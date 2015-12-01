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

"""Munin configuration infos module
"""


import os
import logging

from dispytch import utils


_log = logging.getLogger("dispytch")


def _parse_datafile_line(line):
    """Parse munin datafile line

    :param str line: Munin datafile line
    :return: Informations from line (:class:`dict`)
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


class MuninConfig(object):
    """Simple class to handle Munin configuration and infos

    This object provides several method for ease of configuration use.
    """

    def __init__(self, configpath, datadir, multipollers):
        """Initialization method
        """
        self.configpath = configpath
        self.datadir = datadir
        self.multiple_pollers = multipollers == "yes"
        self._nodes = None

    def clear(self):
        """Clear loaded configuration
        """
        self._nodes = None

    def _parse_config(self, config_lines):
        """Parse Munin style configuration lines

        :param list config_lines: Lines read from configuration files

        :return: Parsed configuration as structure
        :rtype: dict
        """
        config = {}
        section = None
        for line in config_lines:
            # remove comments from line
            line = line.split('#', 1)[0].strip()
            if not len(line):
                continue

            if line.startswith('['):
                section = line[1:-1]
                if section in config:
                    raise SyntaxError('duplicate section: %s' % (section,))

                config[section] = {}
                continue

            option = line.strip().split(None, 1)
            try:
                config[section].update({option[0]: option[1]})
            except IndexError:
                raise SyntaxError('option without value: %s' % (option[0],))
            except KeyError:
                raise SyntaxError('orphan option: %s' % (option[0],))

        return config

    def _process_confs(self, path):
        """Process every ".conf" files found in provided path

        :param str path: Configuration path holding ".conf" files
        """
        configlines = []
        for cfg in os.listdir(path):
            cfg = os.path.join(path, cfg)
            if os.path.isfile(cfg) and cfg.endswith('.conf'):
                configlines.extend(open(cfg, 'r').readlines())
            else:
                _log.warning(
                    'skipping non-configuration element: {0}'.format(cfg))

        return self._parse_config(configlines)

    def load(self):
        """Load munin configuration files
        """
        if self._nodes:
            _log.debug("munin config already loaded")
            return None

        _log.debug("loading munin config")
        _log.debug("configpath: {0}".format(self.configpath))

        if not os.path.isdir(self.configpath):
            _log.error('provided configuration path is not a directory')

        self._nodes = {}
        if self.multiple_pollers is True:
            pollers = os.listdir(self.configpath)
            _log.debug("listed pollers: {0}".format(pollers))
            for poller in pollers:
                configpath = os.path.join(self.configpath, poller)
                datadir = os.path.join(self.datadir, poller)
                for node, data in self._process_confs(configpath).items():
                    data.update({
                        '__poller': poller,
                        '__datadir': datadir,
                        '__datafile': os.path.join(datadir, 'datafile'),
                        '__id': node
                        })
                    self._nodes[node] = data
        else:
            for node, data in self._process_confs(configpath).items():
                data.update({
                    '__poller': "general",
                    '__datadir': self.datadir,
                    '__datafile': os.path.join(self.datadir, 'datafile'),
                    '__id': node
                    })
                self._nodes[node] = data

        _log.debug("{0} nodes loaded".format(len(self._nodes)))
        _log.debug("munin config loaded")

    def _load_node_graphs(self, node):
        """Load node's graphs infos from Munin datafile

        :param str node: Munin node name
        :return: :obj:`None`

        :raise: KeyError if node is missing from configuration
        :raise: KeyError if '__id' infos is missing from node
        :raise: KeyError if '__datafile' infos is missing from node
        """
        datafile = self._nodes[node]['__datafile']
        node_id = self._nodes[node]['__id']
        self._nodes[node]['graphs'] = {}

        # munin datafile describe how graphs should be draw
        # lines may be one of the following:
        #   "munin;entry:datatype.key value with spaces"
        #   "munin;entry:datatype.serie.key value with spaces"
        with open(datafile, "r") as dfile:
            for line in dfile.readlines():
                # Ignore heading line with munin version informations
                if line.startswith("version "):
                    continue

                # Check if line match the provided filter string
                # Example of filter string:
                #   my;munin;entry:cpu
                if not line.startswith("{0}:".format(node_id)):
                    continue

                infos = _parse_datafile_line(line.strip())
                utils.merge_dict(self._nodes[node]['graphs'],
                                 infos[node])

    @property
    def nodes(self):
        """Get loaded nodes names

        :return: Loaded nodes names (:class:`list`)
        """
        if not self._nodes:
            self.load()
        return self._nodes.keys()

    def get_node(self, node_name):
        """Get specific Munin node

        Node configuration and graphs are loaded on call

        :param str node_name: Munin node name
        :return: Munin node data (:class:`dict`) or :obj:`None`
        """
        if node_name in self.nodes:
            self._load_node_graphs(node_name)
            return self._nodes[node_name]

    def get_node_by_ip(self, node_ip):
        """Get specific Munin node by IP

        Node configuration and graphs are loaded on call

        :param str node_ip: Munin node IP address
        :return: Munin node data (:class:`dict`) or :obj:`None`
        """
        for node in self.nodes:
            if node_ip == self._nodes[node]['address']:
                self._load_node_graphs(node)
                return self._nodes[node]


def init_config(configpath, datadir, multipollers):
    """Initialize MuninConfig object and load configuration
    """
    globals()['config'] = MuninConfig(configpath, datadir, multipollers)


config = None
