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

"""dispytch - Modular REST API dispatcher in Python
"""


import os
import sys
import logging
import logging.config
import importlib
import urlparse
import json

from . import config


EXIT_USAGE = 2
EXIT_HANDLE_ERROR = 3

logging.config.dictConfig(config.logging())
_log = logging.getLogger("dispytch")

_INTERNAL_SECTIONS = ('logging',)


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
    url_params = {}
    for key, value in urlparse.parse_qs(string).items():
        # Forcing single item per key.
        # Next releases would support multiple items if needed.
        url_params.update({key: value[0]})
    return url_params


def receive_request(method, request_uri=None):
    """Receive request for the specified method

    :param str method: Method used for the request, may be GET or POST
    :param str request_uri: Request URI while using method GET

    :return: Parsed positionnal and named arguments as :func:`tuple`
    :rtype: tuple
    """
    datas = ([], {})

    _log.debug("request method: {0}".format(method))
    if request_uri is None:
        raise TypeError("Missing request URI")

    docpath = request_uri
    urlencoded = None
    if "?" in request_uri:
        (docpath, urlencoded) = request_uri.split("?", 1)

    _log.debug("request: parsing documentpath from URI")
    datas[0].extend(parse_documentpath(docpath))

    if urlencoded:
        _log.debug("request: parsing url-encoded from URI")
        datas[1].update(parse_urlencoded(urlencoded))

    if method == "POST":
        # Typical content type header:
        #   application/json; charset=utf-8
        # Charset support will be implemented in future releases
        content_type = os.environ.get('CONTENT_TYPE').split(';')[0]
        _log.debug("request content-type: {0}".format(content_type))

        # read posted data from stdin
        request = sys.stdin.read()

        if content_type == 'application/json':
            _log.debug("request: parsing json from POST")
            datas[1].update(json.loads(request))
        else:
            _log.debug("request: parsing url-encoded from POST")
            datas[1].update(parse_urlencoded(request))

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
        if docpath == entry or docpath.startswith("{0}/".format(entry)):
            _log.debug("selected dispatch: {0}".format(entry))
            return dispatches[entry]


def dispatch(docpath, args, kwargs):
    """Dispatch request args and kwargs to the selected module

    :param str docpath: Document path called
    :param list args: Positionnal args to pass to the module
    :param dict kwargs: Named args to pass to the module

    :return: Data returned by module
    :rtype: dict
    """
    data = None
    module_name = None
    module_config = {}

    # retrieve the required known module using dispatch info from document path
    _log.info("handling new dispatch: {0}".format(docpath))

    dispatch_target = select_dispatch(docpath, _DISPATCH_INTERNAL)
    if dispatch_target is not None:
        return {'result': dispatch_target()}

    module_name = select_dispatch(docpath, config.dispatch_list())
    module_config = config.get_section(module_name)
    _log.debug("module name: {0}".format(module_name))
    _log.debug("module config: {0}".format(module_config))

    if not module_name or not module_config:
        raise ImportError("No module found to handle the request")

    # Removing dispatch part of the args if any
    if docpath.startswith(module_config['dispatch']):
        modargs = docpath.split(module_config['dispatch'])[1]
        args = modargs.split('/')[1:] # skipping the 1st always empty element
        _log.debug("cleaned args: {0}".format(args))

    try:
        module_fullname = ".modules.{0}".format(module_name)
        module = importlib.import_module(module_fullname, "dispytch")
        module.configure(module_config)
        data = module.handle_request(*args, **kwargs)
    except ImportError:
        raise ImportError("No module found to handle the request")
    except Exception as exc:
        _log.error("Handled module error: {0}".format(exc.message))
        import traceback, sys
        info = sys.exc_info()
        print ''.join(traceback.format_exception(*info))
        raise RuntimeError(exc.message)

    return {'result': data}
