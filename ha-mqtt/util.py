import logging
import os
import sys
import time


def env(key, default=None):
    return os.environ.get(key, default)


def env_float(key, default=None):
    r = env(key, str(default))
    if r is None:
        return default
    return float(r)


def env_int(key, default=None):
    r = env(key, str(default))
    if r is None:
        return default
    return int(r)


def env_bool(key, default=None):
    r = env(key, str(default))
    if r is None:
        default
    return r.lower() in ['1', 'true', 'yes', 'y']


def env_name(name):
    return env('OVERRIDE_NAME_' + name.replace(" ", "_").upper(), name)


def env_value(name, def_val):
    return env('OVERRIDE_VALUE_' + name.replace(" ", "_").upper(), def_val)


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel({
                             'debug': logging.DEBUG,
                             'info': logging.INFO,
                             'warn': logging.WARN,
                             'error': logging.ERROR
                         }.get(env('LOG_LEVEL', 'info').lower()))
    root_formatter = logging.Formatter("%(asctime)s %(levelname)-5.5s  %(message)s")
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(root_formatter)
    root_logger.addHandler(root_handler)


def sleep_for(t):
    try:
        time.sleep(t)
    except:
        pass


def create_id(c_id, c_name):
    if c_id is None:
        return id_from_name(c_name)
    return c_id


def id_from_name(name):
    return name.replace(" ", "_").lower()
