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

"""Munin RRD utilities module
"""


import os
import re
import logging
import rrdtool


_log = logging.getLogger("dispytch")


def fetch_rrd(path, cf, start, end, opts=[]):
    """Fetch informations from rrd file

    :param str path: RRD file path
    :param str cf: RRD consolidation function to use
    :param str start: Start time
    :param str end: End time
    :param list opts: Additional arguments to pass to rrdtool

    :return: RRD fetched data
    :rtype: list
    """
    args = [path,
            str(cf),
            "-s", str(start),
            "-e", str(end),
            ]
    args.extend(opts)
    return rrdtool.fetch(args)


def get_rrd_metrics(path, cf, start, end, opts=[]):
    """Get transformed metrics from rrd file

    :param str path: RRD file path
    :param str cf: RRD consolidation function to use
    :param str start: Start time
    :param str end: End time
    :param list opts: Additional arguments to pass to rrdtool

    :return: Structured RRD fetched data
    :rtype: dict
    """
    rrd_datas = fetch_rrd(path, cf, start, end)
    _log.debug("fetched RRD data infos: {0}".format(rrd_datas[0]))
    _log.debug("fetched RRD data series: {0}".format(len(rrd_datas[1])))

    (starttime, stoptime, step) = rrd_datas[0]
    names = rrd_datas[1]
    values = rrd_datas[2]

    # Munin daemon caches some data and RRD datas is not so fresh
    # Skip None values (which have not been flushed yet)
    # Timestamps are returned as ms so with are compliant with most of graphing
    # systems (like Highcharts for example)
    # returned series must be of the form:
    #   [[time, val], [time, val], [time, val], ...]
    series = []
    for name in names:
        series.append({'name': name, 'data': []})

    for vidx, vals in enumerate(values):
        for idx, val in enumerate(vals):
            if val is not None:
                series[idx]['data'].append(
                        ((starttime + step * vidx) * 1000, val))

    for idx, serie in enumerate(series):
        _log.debug("serie {0} RRD data points: {1}".format(idx,
                                                           len(serie['data'])))
    return series


def get_munin_entry_metrics(datadir, node, datatype, cf, start, end, opts=[]):
    """Get transformed RRD metrics from munin node

    :param str datadir: Directory containing Munin node's RRDs
    :param str node: Munin node name
    :param str cf: RRD consolidation function to use
    :param str start: Start time
    :param str end: End time
    :param list opts: Additional arguments to pass to rrdtool

    :return: Structured RRD fetched data (:class:`dict`)
    """
    # munin RRD files comonly are: <host>-<datatype>-<datasubtype>-<X>.rrd
    # where <host> can contain dashes (-)
    # and <datasubtype> cannot contain dashes (-)
    # selection is made against: <host>-<datatype>-[^-]+-x.rrd
    rrdpath = "/".join(node.split(';')[:-1])
    host = node.split(';')[-1]
    rrdstore = os.path.join(datadir, rrdpath)

    subtype_pattern = r"{0}-{1}-([^-]+)-.\.rrd".format(host, datatype)
    subtype_re = re.compile(subtype_pattern)

    _log.debug("rrdstore: ".format(rrdstore))

    rrd_candidates = {}
    for rrdfile in os.listdir(rrdstore):
        subtype = subtype_re.match(rrdfile)
        if subtype:
            subtype_name = subtype.groups()[0]
            rrd_candidates.update({
                subtype_name: os.path.join(rrdstore, rrdfile)
                })

    _log.debug("selected rrds: {0}".format(rrd_candidates))

    # returned series must be under the form:
    #   series = [{'name': "serieA",
    #              'data': [[time, val], [time, val], [time, val], ...]},
    #             {'name': "serieB",
    #              'data': [[time, val], [time, val], [time, val], ...]},
    # get_rrd_metrics already returns this format
    # however, munin does not use rrd field name and set it to '42'
    # we replace this fake field name with extracted subtype from file name
    # munin's rrd contains only one field, so we aggregate multiple RRD data
    series = []
    for subtype, rrdfile in rrd_candidates.items():
        rrd_metrics = get_rrd_metrics(rrdfile, cf, start, end)

        # munin rrd only contains one field named "42", check it, or skip
        if len(rrd_metrics) > 1 or rrd_metrics[0]['name'] != "42":
            continue

        serie = {'name': subtype, 'data': rrd_metrics[0]['data']}
        series.append(serie)

    return {node: {datatype: series}}

