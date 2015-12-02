#! /usr/bin/env python
# coding: utf8

#
#    Modular REST API dispatcher in Python (dispytch)
#
#    Copyright (C) 2015 Denis Pompilio (jawa) <denis.pompilio@gmail.com>
#    Copyright (C) 2015 Cyrielle Camanes (cycy) <cyrielle.camanes@gmail.com>
#
#    This file is part of dispytch
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Munin series mutators module
"""

import os
import sys
import logging


_log = logging.getLogger("dispytch")


# Meaningful series
# cpu: 'idle', 'user', 'system', 'iowait'
# memory: 'free', 'cached', 'apps', 'buffers', 'slab'
#    suppress: 'active', 'inactive', 'committed'

# Converts RRD tool draws to Highcharts types
def __convert_draw(serie_cfg):
    """Convert draw information to highcharts type

    :param dict serie_cfg: Serie configuration entry
    :return: Highcharts type (:class:`str`)
    """
    if not serie_cfg.get('draw'):
        return 'spline'

    if serie_cfg['draw'].startswith('LINE'):
        return 'spline'

    if serie_cfg['draw'] == 'AREA':
        return 'areaspline'

    return 'spline'


def __order_series(series, order):
    """Order aggregated RRD series
    """
    s_info = {serie['name']: idx for idx, serie in enumerate(series)}

    ordered_series = []
    for serie_name in order:
        if serie_name in s_info:
            ordered_series.append(series[s_info[serie_name]])

    # Append unordered series
    for serie in series:
        if serie['name'] not in order:
            ordered_series.append(serie)

    return ordered_series


def __hide_series(series, hidelist):
    """Set Highcharts hide flag
    """
    for idx, serie in enumerate(series):
        if serie['name'] in hidelist:
            series[idx]['visible'] = False
    return series


def __show_series(series, showlist, exact=True):
    """Set Highcharts hide flag on non listed series
    """
    for idx, serie in enumerate(series):
        if serie['name'] in showlist:
            series[idx]['visible'] = True
        elif exact:
            series[idx]['visible'] = False
    return series


def __sum_series(series):
    """Sum all series values to get a "total" serie

    :param list series: Aggregated series to sum
    :return: Special "total" serie (:class:`dict`)
    """
    # total serie does not have any __datatype or __node keys
    # total serie is dark
    total_serie = {'name': 'total', 'color': '#666666', 'data': []}

    # We expect all series have the same number of points
    for idx, values in enumerate(series[0]['data']):
        total_serie['data'].append(
                [values[0], sum([serie['data'][idx][1] for serie in series])])
    return total_serie


def __suppress_series(series, suppresslist):
    """Suppress series
    """
    s_info = {serie['name']: idx for serie in enumerate(series)}
    for serie_name in suppresslist:
        if serie_name in s_info:
            series.pop(s_info[serie_name])
    return series


def __negate_serie(serie_data):
    """Negate serie's data values

    :param list serie_data: List of serie's point ([time, value])
    :return: Negated serie's data (:class:`list`)
    """
    return [[point[0], point[1]*-1] for point in serie_data]


def __aggregate_series(data):
    """Aggregate multiple nodes to allow metrics comparison

    :param dict data: Nodes RRD series
    :return: Aggregated nodes RRD series (:class:`dict`)
    """
    aggregated_series = []
    for node, datatypes in data.items():
        for datatype, series in datatypes.items():
            for idx, serie in enumerate(series):
                serie['__node'] = node
                serie['__datatype'] = datatype
                aggregated_series.append(serie)
    return aggregated_series


def mutate_to_highcharts_pie(module_name, info, series):
    """Mutate raw RRD series to pie structured series

    Series value are summed to obtain a cumulated value.

    :param dict series: RRD Series
    :param dict graph: Munin node graph infos
    :return: Mutated RRD series (:class:`dict`)
    """
    _log.debug('mutating series')
    mutated_series = {
            'title': {'text': info.get('graph_title')},
            'series': []
        }

    for idx, serie in enumerate(series['series']):
        serie_info = info.get(serie['name'], {})
        mutated_series['series'].append({
            'name': serie_info.get('label', serie['name']),
            'y': sum([point[1] for point in serie['data']])
            })

    return mutated_series


def mutate_to_highcharts(module_name, info, data, options=None):
    """Mutates RRD series for HighCharts timeseries

    :param dict data: RRD Series
    :param dict graph: Munin node graph infos
    :return: Mutated RRD series (:class:`dict`)
    """
    _log.debug('mutating series')

    if module_name != "munin":
        _log.debug('series from unhandled module {0}'.format(module_name))
        _log.debug('skipping series mutation')
        return series

    # return series are structured like:
    # "node-A": {
    #     "datatype1": [{'name': "A", 'data': [...]}, ...],
    #     "datatype2": [{'name': "A", 'data': [...]}, ...],
    #     ...
    #     },
    # "node-B": {
    #     "datatype1": [{'name': "A", 'data': [...]}, ...]
    #     "datatype2": [{'name': "A", 'data': [...]}, ...],
    #     ...
    #     },
    y_text = info.get('graph_vlabel', '')
    y_text = y_text.replace('${graph_period}', 'second')
    mutated_series = {
            'title': {'text': info.get('graph_title')},
            #'subtitle': {'text': graph.get('graph_info')},
            'xAxis': {'type': 'datetime'},
            'yAxis': {'title': {'text': y_text}},
            'series': []
        }

    # aggregate multiple nodes and datatypes
    series = __aggregate_series(data)

    # calculate the "total" serie if needed
    if info.get('graph_total'):
        _log.debug("summing series to get total")
        series.append(__sum_series(series))

    # order series according to munin graph_order informations
    series_order = info.get('graph_order', '').split()
    if len(series_order):
        series = __order_series(series, series_order)

    # loop on series to define extensions to apply on next loop
    series_to_negate = []
    stacks = {}
    for serie in series:
        _log.debug("extending serie: {0} (pass#1)".format(serie['name']))
        s_info = info.get(serie['name'], {})

        # specific for "df*" plugins with wrong labels
        if serie.get('__datatype', '').startswith('df'):
            serie['name'] = s_info.get('label', serie['name'])

        # handle series to negate (ie. network)
        if s_info.get('negative'):
            series_to_negate.append(s_info['negative'])

        # handle stackable series
        if s_info.get('draw') == 'STACK':
            if prev_name not in stacks:
                stacks[prev_name] = {'stack': prev_name,
                                     'stacking': 'normal'}
            s_info['draw'] = prev_draw
            stacks[serie['name']] = stacks[prev_name]
        else:
            (prev_name, prev_draw) = (serie['name'], s_info.get('draw'))

        # convert RRDTool draw to Highcharts type
        serie['type'] = __convert_draw(s_info)

    # Loop on series to apply "stack" and "negate" extensions
    for serie in series:
        _log.debug("extending serie: {0} (pass#2)".format(serie['name']))

        if serie['name'] in stacks:
            serie.update(stacks[serie['name']])

        if serie['name'] in series_to_negate:
            serie['data'] = __negate_serie(serie['data'])

        mutated_series['series'].append(serie)

    return mutated_series
