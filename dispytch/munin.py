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

"""Munin RRD requesting module

Use this API to extract and handle informations from Munin datafiles (rrd).
This API support both POST and GET method to handle queries. GET requests can
be formatted using document path or url-encoded format.

Usage:
    Using document path:
      /munin/list[/<ip>]
      /munin/list[/templates]
      /munin/by-ip/<ip>/<datatype>/<cf>/<start>/<stop>[/<template>]
      /munin/by-id/<id>/<datatype>/<cf>/<start>/<stop>[/<template>]
    Using url-encoded request:
      /munin/list[?ip=<ip>]
      /munin/by-ip?ip=<ip>&datatype=<datatype>&...

Known Fields:
    ip              IP address of the target used by Munin
    id              Munin entry name in configuration
    datatype        Munin datatype as shown in RRDs names
    cf              RRD consolidation function to use
    start           Start time as supported by RRD library
    stop            Stop time as supported by RRD library
    template        Template to use for returned datas structuration

Exemple:
    /munin/by-ip/1.1.1.1/cpu/AVERAGE/now-2h/now
    /munin/by-id/munin;config;id/processes/AVERAGE/1383260400/138585240
"""


import os
import logging
import rrdtool
import ConfigParser


_log = logging.getLogger("dispytch")


CONFIG = None
DATADIR = None
RRDEXT = None


def selfcheck(config):
    """Selfcheck module functionnalities

    :param dict config: Configuration informations
    """
    configure(config)
    assert(CONFIG, config.get('config'))
    assert(DATADIR, config.get('datadir'))
    assert(RRDEXT, config.get('rrdext'))
    assert(True, has_attr(rrdtool, fetch))


def configure(config):
    """Configure module

    :param dict config: Configuration informations
    """
    _log.debug("module config: {0}".format(config))
    CONFIG = config.get('config')
    DATADIR = config.get('datadir')
    RRDEXT = config.get('rrdext')


def handle_request(*args, **kwargs):
    """Main module entry point
    """

    _log.debug("handling new request")
    _log.debug("args: {0}".format(args))
    _log.debug("kwargs: {0}".format(kwargs))

    return {}


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
            cf,
            "-s", '%s' % (start),
            "-e", '%s' % (end),
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
    rrd_datas = rrdfetch(path, cf, start, end)
    _log.debug("fetched rrd_datas: {0}".format(rrd_datas))

    starttime = rrd_datas[0][0]
    step = rrd_datas[0][2]
    name = rrd_datas[1][0]

    # Munin daemon caches some data and RRD datas is not so fresh
    # Skip None values (which have not been flushed yet)
    # Timestamps are returned as ms so with are compliant with HighCharts
    serie = dict([(starttime + step * idx * 1000, {name: value[0], })
                  for idx, value in enumerate(rrd_datas[2])
                  if value[0] is not None])
    return serie


def parse_munin_config(config_lines):
    """Parse Munin style configuration lines

    :param list config_lines: Lines read from configuration files

    :return: Configuration object
    :rtype: ConfigParser.RawConfigParser
    """
    config = ConfigParser.RawConfigParser()
    section = None
    for line in config_lines:
        # remove comments from line
        line = line.split('#', 1)[0]
        if not len(line.strip()):
            continue
        if line.startswith('['):
            section = line[1:-2]
            try:
                config.add_section(section)
            except ConfigParser.DuplicateSectionError:
                continue
            continue

        option = line.strip().split(None, 1)
        try:
            config.set(section, option[0], option[1])
        except IndexError:
            continue

    return config
