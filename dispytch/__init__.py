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

# import config
# mutators are imported on-demand later
from dispytch import config


EXIT_USAGE = 2
EXIT_HANDLE_ERROR = 3

logging.config.dictConfig(config.logging())
_log = logging.getLogger("dispytch")

_INTERNAL_SECTIONS = ('logging',)


class MutatorError(Exception):
    """Custom exception to handle mutator errors
    """


def get_module(module_name, path):
    try:
        _log.debug("importing {0} from {1}".format(module_name, path))
        # If a previous module with the same name exists, clean it
        # I don't know if there is a better way, this may not be pythonic
        if module_name in sys.modules:
            sys.modules.pop(module_name)
        sys.path.insert(0, path)
        module = importlib.import_module(module_name)
        _log.debug("imported: {0}".format(module.__file__))
    finally:
        sys.path.pop(sys.path.index(path))
    return module


def get_mutator(mutator_fullname):
    """Get mutator function

    Mutator full name has to include module name:
        <mutator_module>.<transform>
    Returned mutator function will be:
        <mutator_module>.mutate_to_<transform>

    :param str mutator_fullname: Mutator's function name
    :return: Mutator function handler
    """
    if '.' not in mutator_fullname:
        raise MutatorError("Invalid mutator name: {0}".format(mutator_fullname))

    (module_name, transform) = mutator_fullname.split('.')
    module = get_module(module_name, config.mutators_path)
    _log.debug("getting mutator function: mutate_to_{0}".format(transform))
    return getattr(module, "mutate_to_{0}".format(transform))


# modules path in config
# mutators path in config
# mutators are called using <mutator_module>.|mutate_to_|<transform>
# json:   mutator: munin.highcharts => munin.mutate_to_highcharts
#
# Method to list available mutator modules.mutate_to_* methods
# Direct call on series transformation
# Modify function above
# import_file('/home/somebody/somemodule.py')


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


def receive_request(method, request_uri):
    """Receive request for the specified method

    :param str method: Method used for the request, may be GET or POST
    :param str request_uri: Request URI

    :return: Module name, parsed "args" and "kwargs" as :func:`tuple`
    :rtype: tuple
    """
    _log.debug("request method: {0}".format(method))

    if request_uri.startswith(config.location):
        # Stripping dispytch location from URI
        request_uri = request_uri[len(config.location):]

    _log.debug('request URI: {0}'.format(request_uri))
    (dispatch, module_name) = select_dispatch(request_uri, config.dispatches)

    # Cleaning module's dispatch from positionnal arguments
    if request_uri.startswith(dispatch):
        request_uri = request_uri[len(dispatch):]

    _log.debug('request target module: {0}'.format(module_name))
    datas = (module_name, [], {})

    docpath = request_uri
    urlencoded = None
    if "?" in request_uri:
        (docpath, urlencoded) = request_uri.split("?", 1)

    _log.debug("request: parsing documentpath from URI")
    datas[1].extend(parse_documentpath(docpath))

    if urlencoded:
        _log.debug("request: parsing url-encoded from URI")
        datas[2].update(parse_urlencoded(urlencoded))

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
            datas[2].update(json.loads(request))
        else:
            _log.debug("request: parsing url-encoded from POST")
            datas[2].update(parse_urlencoded(request))

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


def select_dispatch(docpath, dispatches):
    """Select matching dispatch from dispatches infos

    :param str docpath: Requested path
    :param dict dispatches: Dictionnary of dispatches and associated modules

    :return: Selected dispatch and dispatch target or None
    """
    # dispatches are sorted, so the most precise dispatch is selected
    for entry in sorted(dispatches, reverse=True):
        if docpath == entry or docpath.startswith("{0}/".format(entry)):
            _log.debug("selected dispatch: {0}".format(entry))
            return (entry, dispatches[entry])


def dispatch(module_name, args, kwargs):
    """Dispatch request args and kwargs to the selected module

    :param str docpath: Document path called
    :param list args: Positionnal args to pass to the module
    :param dict kwargs: Named args to pass to the module

    :return: Data returned by module
    :rtype: dict
    """
    data = None
    module_config = {}

    # retrieve the required known module using dispatch info from document path
    _log.info("handling new dispatch: {0}".format(module_name))

    # How to handle internal dispatches ?
    #if dispatch_target is not None:
    #    return {'result': dispatch_target()}

    module_config = config.get_section(module_name)
    _log.debug("module config: {0}".format(module_config))

    if not module_config:
        raise ImportError("No module found to handle the request")

    try:
        module = get_module(module_name, config.modules_path)
        module.configure(module_config)
        data = module.handle_request(*args, **kwargs)

    except ImportError:
        raise ImportError("No module found to handle the request")

    except Exception as exc:
        _log.error("handled module error: {0}".format(exc.message))
        raise RuntimeError(exc.message)

    if kwargs.get('mutator'):
        try:
            mutator_name = kwargs['mutator']
            mutator_opts = kwargs.get('mutator_opts')

            _log.debug('selected mutator: {0}'.format(mutator_name))
            mutator = get_mutator(mutator_name)

            _log.debug('sending series to mutator')
            return {'result': mutator(module_name, data[0], data[1],
                                      options=mutator_opts)}

        except ImportError, AttributeError:
            raise ImportError("No mutator found to transform the response")

        except Exception as exc:
            _log.error("handled mutator error: {0}".format(exc.message))
            raise RuntimeError(exc.message)

    return {'result': data[1]}
