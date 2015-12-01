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

"""Munin requests module
"""

import logging

from . import infos
from . import rrd_utils


_log = logging.getLogger("dispytch")


def handle_request_list(arguments):
    """Handle "list" request

    :param dict arguments: Dictionnary of arguments

    :return: Dictionnary of available data
    :rtype: dict
    """
    target = arguments.get('target')

    if target:
        available = {target: infos.config.get_node(target)}
    else:
        available = {'nodes_list': infos.config.nodes}

    return (None, available)


def handle_request_byid(munin_args):
    """Handle "by-id" request

    :param dict munin_args: Dictionnary of arguments built by Munin module

    :return: Dictionnary of fetched data
    :rtype: dict
    """
    # Find specified id from configuration
    if not munin_args.get('target'):
        raise ValueError('missing node from request')

    node = infos.config.get_node(munin_args['target'])
    if not node:
        raise ValueError('unknown requested node')

    _log.debug("selected munin node: {0}".format(node['__id']))
    series = rrd_utils.get_munin_entry_metrics(
                node['__datadir'], node['__id'],
                munin_args.get('datatype'), munin_args.get('cf'),
                munin_args.get('start'), munin_args.get('stop'))

    graph_info = node.get('graphs', {}).get(munin_args.get('datatype'))
    return (graph_info, series)


def handle_request_byip(munin_args):
    """Handle "by-ip" request

    :param dict arguments: Dictionnary of arguments

    :return: Dictionnary of fetched data
    :rtype: dict
    """
    # Find id with specified ip from configuration
    ipaddr = munin_args.get('target')
    if ipaddr is None:
        raise ValueError('missing IP from request')

    node = infos.config.get_node_by_ip(munin_args['target'])
    if not node:
        raise ValueError('unknown requested IP')

    _log.debug("selected munin node: {0}".format(node['__id']))
    series = rrd_utils.get_munin_entry_metrics(
                node['__datadir'], node['__id'],
                munin_args.get('datatype'), munin_args.get('cf'),
                munin_args.get('start'), munin_args.get('stop'))

    graph_info = node.get('graphs', {}).get(munin_args.get('datatype'))
    return (graph_info, series)


# Reference known methods to handle
KNOWN_METHODS = {
    'list': handle_request_list,
    'by-id': handle_request_byid,
    'by-ip': handle_request_byip,
    }

