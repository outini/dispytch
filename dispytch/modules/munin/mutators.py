#! /usr/bin/env python

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

import logging


_log = logging.getLogger("dispytch")


def transform_series(series, graph_infos, mutator):
    """Transforms RRD series according to specified mutator

    :param dict series: RRD Series
    :param dict graph_infos: Munin node graph infos
    :param str mutator: Mutator name to use to transform series
    :return: Mutated RRD series (:class:`dict`)
    """
    try:
        mutator_func = "mutate_for_{0}".format(mutator)
        _log.debug('using mutator function: {0}'.format(mutator_func))
        return globals()[mutator_func](series, graph_infos)
    except KeyError:
        raise ValueError("Unknown mutator for series transformation")


def mutate_for_highcharts(series, graph):
    """Mutates RRD series for HighCharts

    :param dict series: RRD Series
    :param dict graph: Munin node graph infos
    :return: Mutated RRD series (:class:`dict`)
    """
    _log.debug('mutating series')
    mutated_series = {
            'title': {'text': graph.get('graph_title')},
            #'subtitle': {'text': graph.get('graph_info')},
            'xAxis': {'type': 'datetime'},
            'yAxis': {'title': {'text': graph.get('graph_vlabel')}}
        }

    for idx, serie in enumerate(series['series']):
        infos = graph.get(serie['name'])
        series['series'][idx]['name'] = infos.get('label', serie['name'])

    mutated_series.update(series)

    return mutated_series
