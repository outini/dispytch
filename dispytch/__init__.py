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

"""dispytch - Modular REST API dispatcher in Python

CLI Usage:
    dispytch <request_uri>
"""


import os
import sys
import logging
import logging.config
import json

import config


EXIT_USAGE = 2
EXIT_HANDLE_ERROR = 3

logging.config.dictConfig(config.logging())
_log = logging.getLogger("dispytch")

_INTERNAL_SECTIONS = ('logging',)


def output_json(data):
    """Output passed datas as json

    :param dict data: Data to output as json
    """
    print(json.dumps(data, indent=2))


def parse_documentpath(string):
    """Parse URL document path and return datas dict

    :param str string: Documentpath REST call
    :return: Positionnal arguments from parsed document path
    :rtype: list
    """
    # document path starts with '/', exclude the first empty element
    _log.debug("parsing documentpath: {0}".format(string))
    return string.split("/")[1:]


def parse_urlencoded(string):
    """Parse URL-Encoded format and return datas dict

    :param str string: URL-Encoded string
    :return: Named arguments from parsed URL-Encoded string
    :rtype: dict
    """
    _log.debug("parsing url-encoded: {0}".format(string))
    kwargs = {}
    for field in string.split("&"):
        if "=" in field:
            key, val = field.split("=", 1)
            kwargs.update({key: val})
    return kwargs


def receive_request(method):
    """Receive request for the specified method

    :param str method: Method used for the request, may be GET or POST

    :return: Parsed positionnal and named arguments as :func:`tuple`
    :rtype: tuple
    """
    datas = ([], {})

    _log.debug("request method: {0}".format(method))
    if method == "POST":
        # read url-encoded input from stdin
        _log.debug("request type: url-encoded")
        request = sys.stdin.read()
        datas[1].update(parse_urlencoded(request))

    elif method == "GET":
        req_uri = os.environ.get('REQUEST_URI', '')
        if "?" in req_uri:
            _log.debug("request type: url-encoded")
            datas[1].update(parse_urlencoded(req_uri.split("?", 1)[-1]))
        else:
            _log.debug("request type: documentpath")
            datas[0].extend(parse_documentpath(req_uri))

    _log.debug("request datas: {0}".format(datas))
    return datas


def info():
    """Get information from dispytch and configured modules

    """
    _log.debug('Get information')
    cur_config = {}
    # get insternal configuration
    for section in _INTERNAL_SECTIONS:
        cur_config.update({ section: config.get_section(section)})
        config.print_section(section)

    # get moludes configuration
    for disp in config.dispatch_list():
        (section, mod_config) = config.get_dispatch(disp)
        cur_config.update({ section: config.get_section(section)})
        config.print_section(section)

    return cur_config


_DISPATCH_INTERNAL = {'/info': info}


def select_dispatch(docpath, dispatches):
    """Select matching dispatch from dispatches infos

    :param str docpath: Requested path
    :param dict dispatches: Dictionnary of dispatches and associated modules

    :return: Matched dispatch target or None
    """
    # dispatches are sorted, so the most precise dispatch is selected
    for entry in sorted(dispatches, reverse=True):
        if docpath.startswith(entry):
            _log.debug("selected dispatch: {0}".format(entry))
            return dispatches[entry]


def dispatch(args, kwargs):
    """Dispatch request args and kwargs to the selected module

    :param list args: Positionnal args to pass to the module
    :param dict kwargs: Named args to pass to the module

    :return: Data returned by module
    :rtype: dict
    """
    data = None
    module_name = None
    module_config = {}

    # retrieve the required known module using dispatch info from document path
    docpath = os.environ.get('DOCUMENT_PATH', '')
    _log.info("handling new dispatch: {0}".format(docpath))

    dispatch_target = select_dispatch(docpath, _DISPATCH_INTERNAL)
    if dispatch_target is not None:
        return {'result': dispatch_target()}

    module_name = select_dispatch(docpath, config.dispatch_list())
    #module_config = config.get_section(module_name)
    _log.debug("module name: {0}".format(module_name))
    _log.debug("module config: {0}".format(module_config))

    try:
        module = __import__(module_name)
        module.configure(module_config)
        data = module.handle_request(*args, **kwargs)
    except TypeError, ValueError:
        raise ImportError("No module found to handle the request")

    return {'result': data}


if __name__ == "__main__":
    # Test request method to handle commandline
    method = os.environ.get('REQUEST_METHOD')

    if method is None:
        if len(sys.argv) == 2:
            os.environ['REQUEST_URI'] = sys.argv[1]
        else:
            print(__doc__)
            exit(EXIT_USAGE)

    try:
        print "Content-type: text/plain"
        print ""
        (args, kwargs) = receive_request(method)
        output_json(dispatch(args, kwargs))
    except Exception:
        import traceback
        info = sys.exc_info()
        _log.error(info[1].message)
        output_json({'error': info[1].message, })
        print('# ' + '\n# '.join(__doc__.split("\n")))

        # For debug purposes
        print ''.join(traceback.format_exception(*info))
