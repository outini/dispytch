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

import ConfigParser
import os


__CONFIG = {}
CONFIG_FILE = 'dispytch.conf'

# dirty patch for development
CONFIG_FILE = os.path.sep.join([os.path.dirname(__file__), CONFIG_FILE])




class ConfigurationError(Exception):
    """Custom configuration error exception
    """


def __load_config_file():
    """Load config file

    Configuration file dispytch.conf should be in dispytch directory

    :return: ConfigParser
    """
    try:
        assert os.path.isfile(CONFIG_FILE)
        assert os.access(CONFIG_FILE, os.R_OK)
    except AssertionError:
        message = 'File {0} not found or not readable'.format(CONFIG_FILE)
        raise ConfigurationError(message)

    conf_parser = ConfigParser.RawConfigParser()

    try:
        conf_parser.read(CONFIG_FILE)
    except ConfigParser.ParsingError as e:
        raise ConfigurationError(e.message)

    return conf_parser


def __parse_conf():
    """Parse configuratiguration file and translate it as structure

    :return: Configuration
    :rtype: dict
    """
    conf_parser = __load_config_file()

    for section in conf_parser.sections():
        __CONFIG.update({section : {}})
        for option in conf_parser.options(section):
            value = conf_parser.get(section, option)
            # specific handling of some entries to remove ending "/"
            if option in ["dispatch", "location"] and value.endswith('/'):
                value = value[:-1]
            __CONFIG[section].update({option : value})


def __get_dispatches():
    """Get list of sections where dispatch value is set

    :return: list of sections with dispatch
    :rtype: dict
    """
    dispatches = {}
    for section, opts in __CONFIG.items():
        if 'dispatch' in opts:
            dispatches.update({opts['dispatch']: section})
    return dispatches


def __configure():
    """Configure dispytch
    """
    __parse_conf()
    cfg = get_section('dispytch')

    # configure module's global attributes
    globals()['location'] = cfg['location']
    globals()['modules_path'] = cfg['modules']
    globals()['mutators_path'] = cfg['mutators']
    globals()['dispatches'] = __get_dispatches()
    globals()['internal_dispatches'] = {
            '{0}/info'.format(location): "info",
            '{0}/modules'.format(location): "list_modules",
            '{0}/mutators'.format(location): "list_mutators"
            }


def print_section(section):
    """Print section as comment to be human readable

    :param section str: selected section
    """
    print("# Section: {0}".format(section))
    print("#=========={0}".format("="*len(section)))
    for opt, value in __CONFIG.get(section).items():
        print("#  - {0}: {1}".format(opt, value))
    print("#")


def get_sections():
    """Get list of sections

    :return: list of sections
    :rtype: list
    """
    return __CONFIG.keys()


def get_section(section):
    """Get options of specific section

    :param section string: name of the section
    
    :return: options
    :rtype: dict
    """
    return __CONFIG.get(section)


def get_dispatch(dispatch):
    """Get section info of dispatch

    :param dispatch string: dispatch from which info is useful

    :return: related section with options
    :rtype: tuple
    """
    for section in __CONFIG:
        if __CONFIG[section].has_key('dispatch'):
            value = __CONFIG[section].get('dispatch')
            if value == dispatch:
                return (section, __CONFIG[section])

    return (None, {})


def logging():
    """Generate logging configuration

    :return: logging configuration to apply
    :rtype: dict
    """
    log = get_section('logging')
    log_level = log.get('level', 'debug').upper()
    log_format = log.get('format',
                     '%(asctime)s %(name)s [%(levelname)s] %(message)s')

    log_conf = {
        'version': 1,
        'formatters': {
            'brief': {
                'format': '[%(levelname)s] [%(filename)s:%(funcName)s] %(message)s'},
            'general': {'format': log_format},
            },
        'handlers': {'null': {'class': 'logging.NullHandler'}},
        'loggers': {
            'dispytch': {
                'level': log_level,
                'handlers': ['null'],
                'propagate': 'no',
                },
            },
        }

    if log.get('console') == 'yes':
        log_conf['handlers'].update({
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'brief',
                'stream': 'ext://sys.stdout',
                },
            })
        log_conf['loggers']['dispytch']['handlers'].append('console')

    if len(log.get('file', '')):
        log_conf['handlers'].update({
            'file': {
                'class': 'logging.FileHandler',
                'level': log_level,
                'formatter': 'general',
                'filename': log.get('file'),
            },
        })
        log_conf['loggers']['dispytch']['handlers'].append('file')

    return(log_conf)


# Automatic load of configuration
__configure()
