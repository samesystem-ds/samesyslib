import os

# from enum import Enum
from pathlib import Path

from samesyslib.utils import load_config


DEFAULT_ENV = os.getenv("DB_ENVIRONMENT", "dev")
CONFIG_PATH = os.getenv("CONFIG_PATH", None)


# class Envs(Enum):
#     DEV = "dev"
#     STG = "stg"
#     PROD = "prod"


class DBParams(object):
    host = None
    schema = None
    login = None
    password = None
    port = None
    connector = "pymysql"
    _shard = None
    parameters = {}
    connect_args = {}

    def __init__(self, **params):
        self.__dict__.update(params)


class DBConfig(object):
    def __init__(self, env=None, schema=None, bi=False, parameters={}, connect_args={}):
        self._schema = schema
        self._env = env
        self._connect_args = connect_args
        self._parameters = parameters

        self.db_connection = None

        self._change_env(env)
        self._proceed()

    def _change_env(self, env):
        # if env and env not in Envs._value2member_map_:
        #     raise Exception(f"ERROR: passed env: {env} is not valid")
        self._env = env or DEFAULT_ENV

    def _load_from_config(self):
        if CONFIG_PATH is None:
            raise Exception("CONFIG_PATH is not defined")

        path = Path.home() / Path(CONFIG_PATH)
        cred = load_config(path)
        conf = cred[self._env]
        conf["parameters"] = self._parameters
        conf["connect_args"] = self._connect_args
        self.db_connection = DBParams(**conf)

        conf = cred[self._env]
        conf["schema"] = "samesystem_sisense"
        conf["parameters"] = self._parameters
        conf["connect_args"] = self._connect_args
        self.bi_connection = DBParams(**conf)

    def _proceed(self):
        self._load_from_config()

    def get_config(self):
        return self.db_connection
