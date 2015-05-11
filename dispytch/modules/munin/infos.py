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

"""Munin configuration infos module
"""


import os
import logging
import ConfigParser

from dispytch import utils


_log = logging.getLogger("dispytch")


CONFIG = None
MUNIN_CONFIG = None


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


def parse_munin_datafile_line(line):
    """Parse munin datafile line

    :param str line: Munin datafile line

    :return: Informations from line
    :rtype: dict
    """
    (entry, infos_str) = line.strip().split(":", 1)
    (tree, value) = infos_str.split(' ', 1)
    infos = tree.split('.', 2)
    option = infos.pop(-1)
    key = infos.pop(0)

    if len(infos):
        subkey = infos.pop(0)
        return {entry: {key: {subkey: {option: value}}}}

    return {entry: {key: {option: value}}}


def load_munin_datafile(datafile_path, filter_str=None):
    """Load munin datafile containing graphs infos

    :param str datafile_path: Munin datafile path
    :param str filter_str: Filter string to use on data load

    :return: Datafile selected content
    :rtype: dict
    """
    # munin datafile describe how graphs should be draw
    # lines may be one of the following:
    #   "munin;entry:datatype.key value with spaces"
    #   "munin;entry:datatype.serie.key value with spaces"
    data = {}
    with open(datafile_path, "r") as dfile:
        for line in dfile.readlines():
            # Check if line match the provided filter string
            # Example of filter string:
            #   my;munin;entry:cpu
            if filter_str is not None and not line.startswith(filter_str):
                continue

            infos = parse_munin_datafile_line(line.strip())
            utils.merge_dict(data, infos)

    return data


def load_munin_configs():
    """Load munin configuration files from path

    :param str path: Configuration path

    :return: Configuration structure
    :rtype: dict
    """
    configs = {}

    if MUNIN_CONFIG is not None:
        _log.debug("munin config already loaded")
        return MUNIN_CONFIG

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
    globals()['MUNIN_CONFIG'] = configs

    return MUNIN_CONFIG

