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

"""Munin requests module
"""


from . import infos


def handle_request_list(arguments):
    """Handle "list" request

    :param dict arguments: Dictionnary of arguments

    :return: Dictionnary of available data
    :rtype: dict
    """
    info = {}
    for poller, config in infos.MUNIN_CONFIG.items():
        pinfo = {}
        for section in config.sections():
            pinfo[section] = dict(config.items(section))
        info[poller] = pinfo
    #return infos.load_munin_datafile(os.path.join(DATADIR, "a/datafile"))
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
    for poller, config in infos.MUNIN_CONFIG.items():
        if munin_entry in config.sections():
            munin_poller = poller
            break

    _log.debug("selected munin poller: {0}".format(munin_poller))
    _log.debug("selected munin entry: {0}".format(munin_entry))

    if munin_poller is None:
        raise ValueError('target not found')

    return rrd_utils.get_munin_entry_metrics(
            munin_poller, munin_entry,
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
    for poller, config in infos.MUNIN_CONFIG.items():
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

