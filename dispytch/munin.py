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
    try:
        assert config.has_key('config')
        assert config.has_key('datadir')
        assert config.has_key('rrdext')
    except AssertionError:
        raise RuntimeError("invalid module configuration")

    try:
        configure(config)
        assert CONFIG == config['config']
        assert DATADIR == config['datadir']
        assert RRDEXT == config['rrdext']
    except AssertionError:
        raise RuntimeError("unable to configure module")

    try:
        assert has_attr(rrdtool, fetch)
    except AssertionError:
        raise RuntimeError("missing dependency")


def configure(config):
    """Configure module

    :param dict config: Configuration informations
    """
    _log.debug("module config: {0}".format(config))
    globals().update({
        'CONFIG': config.get('config'),
        'DATADIR': config.get('datadir'),
        'RRDEXT': config.get('rrdext'),
        })
    try:
        assert CONFIG is not None
        assert DATADIR is not None
        assert RRDEXT is not None
    except AssertionError:
        raise RuntimeError("unconfigured module")


def handle_request(*args, **kwargs):
    """Main module entry point
    """

    _log.debug("handling new request")
    _log.debug("args: {0}".format(args))
    _log.debug("kwargs: {0}".format(kwargs))

    # Converting positionnal args to kwargs
    # First positionnal arg is always dispatch, skipping it
    args = list(args)
    args.pop(0)
    fields = ["method", "target", "datatype", "cf", "start", "stop", "tmpl"]
    positionnal_args = dict(zip(fields[:len(args)], args))

    # arguments agreggation
    arguments = kwargs
    arguments.update(positionnal_args)

    _log.debug("arguments: {0}".format(arguments))

    # Unknown method will raise exception handled by dispatcher
    try:
        return KNOWN_METHODS[arguments['method']](arguments)
    except Exception as e:
        print(e.__repr__())


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
    rrd_datas = fetch_rrd(path, cf, start, end)
    _log.debug("fetched rrd_datas: {0}".format(rrd_datas))

    starttime = rrd_datas[0][0]
    step = rrd_datas[0][2]
    name = rrd_datas[1][0]

    # Munin daemon caches some data and RRD datas is not so fresh
    # Skip None values (which have not been flushed yet)
    # Timestamps are returned as ms so with are compliant with HighCharts
    # returned series must be of the form:
    #   [[time, val], [time, val], [time, val], ...]

    serie = dict([(starttime + step * idx * 1000, {name: value[0], })
                  for idx, value in enumerate(rrd_datas[2])
                  if value[0] is not None])
    return serie


def get_rrd_metrics_by_entry(poller, entry, datatype, cf, start, end, opts=[]):
    """Get transformed RRD metrics from munin entry

    :param str poller: Munin poller
    :param str entry: Munin configuration entry
    :param str cf: RRD consolidation function to use
    :param str start: Start time
    :param str end: End time
    :param list opts: Additional arguments to pass to rrdtool

    :return: Structured RRD fetched data
    :rtype: dict
    """
    # munin RRD files comonly are: <host>-<datatype>-<datasubtype>-<X>.rrd
    # where <host> can contain dashes (-)
    rrdhostpath = "/".join(entry.split(';')[:-1])
    rrdhost = entry.split(';')[-1]
    rrdstore = os.path.join(DATADIR, poller, rrdhostpath)

    _log.debug("rrdstore:".format(rrdstore))

    rrd_candidates = []
    match = "%s-%s" % (rrdhost, datatype)
    for rrdfile in os.listdir(rrdstore):
        if rrdfile[:len(match) + 1] == "%s-" % (match) \
            and '-' not in rrdfile[len(match) + 1: -6]:
            rrd_candidates.append(os.path.join(rrdstore, rrdfile))

    _log.debug("selected rrds: {0}".format(rrd_candidates))

    # returned series must be under the form:
    #   series = [{'name': "serieA",
    #              'data': [[time, val], [time, val], [time, val], ...]},
    #             {'name': "serieB",
    #              'data': [[time, val], [time, val], [time, val], ...]},
    rrddata = []
    for rrdfile in rrd_candidates:
        # Munin only store one field named "42"
        field = rrdfile.split('-')[-2]
        serie = {'name': field, 'data': []}

        for entry, data in get_rrd_metrics(rrdfile, cf, start, end).items():
            serie['data'].append([entry, data.values()[0]])

        rrddata.append(serie)

    return rrddata


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


def load_munin_configs():
    """Load munin configuration files from path

    :param str path: Configuration path

    :return: Configuration structure
    :rtype: dict
    """
    configs = {}

    _log.debug("loading munin config")
    _log.debug("configpath: {0}".format(CONFIG))

    if os.path.isdir(CONFIG):
        pollers = os.listdir(CONFIG)
        _log.debug("listed pollers: {0}".format(pollers))
        for poller in pollers:
            raw_config = []
            for cfg in os.listdir(os.path.join(CONFIG, poller)):
                cfg = os.path.join(CONFIG, poller, cfg)
                if cfg.endswith('.conf'):
                    raw_config.extend(open(cfg, 'r').readlines())
            configs[poller] = parse_munin_config(raw_config)

    _log.debug("munin config loaded")

    return configs


def handle_request_list(arguments):
    """Handle "list" request

    :param dict arguments: Dictionnary of arguments

    :return: Dictionnary of available data
    :rtype: dict
    """
    munin_config = load_munin_configs()
    info = {}
    for poller, config in munin_config.items():
        pinfo = {}
        for section in config.sections():
            pinfo[section] = dict(config.items(section))
        info[poller] = pinfo
    return info

def handle_request_byid(kwargs):
    """Handle "by-id" request

    :param dict args: Dictionnary of arguments

    :return: Dictionnary of fetched data
    :rtype: dict
    """
    # Find specified id from configuration
    munin_entry = kwargs.get('target')
    if munin_entry is None:
        raise ValueError('invalid request')

    munin_poller = None
    munin_config = load_munin_configs()
    for poller, config in munin_config.items():
        if munin_entry in config.sections():
            munin_poller = poller
            break

    _log.debug("selected munin poller: {0}".format(munin_poller))
    _log.debug("selected munin entry: {0}".format(munin_entry))

    if munin_poller is None:
        raise ValueError('target not found')

    return get_rrd_metrics_by_entry(munin_poller, munin_entry,
                                    kwargs.get('datatype'), kwargs.get('cf'),
                                    kwargs.get('start'), kwargs.get('stop'))


def handle_request_byip(arguments):
    """Handle "by-ip" request

    :param dict arguments: Dictionnary of arguments

    :return: Dictionnary of fetched data
    :rtype: dict
    """
    # Find id with specified ip from configuration
    ipaddr = arguments.get('target')
    if ipaddr is None:
        raise ValueError('invalid request')

    munin_entry = None
    munin_poller = None
    munin_config = load_munin_configs()
    for poller, config in munin_config.items():
        for section in config.sections():
            if ('address', ip) in config.items(section):
                munin_poller = poller
                munin_entry = section
                break

    _log.debug("selected munin poller: {0}".format(munin_poller))
    _log.debug("selected munin entry: {0}".format(munin_entry))

    if munin_entry is None or munin_poller is None:
        raise ValueError('target not found')

    return {}


# Reference known methods to handle
KNOWN_METHODS = {
    'list': handle_request_list,
    'by-id': handle_request_byid,
    'by-ip': handle_request_byip,
    }

