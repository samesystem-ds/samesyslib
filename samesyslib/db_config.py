import os
import sys
import json
import logging
from enum import Enum
from pathlib import Path

from samesyslib.utils import load_config

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

DEFAULT_ENV = 'dev'


class Envs(Enum):
    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class DBParams(object):
    host = None
    schema = None
    login = None
    password = None
    port = None
    connector = "pymysql"

    def __init__(self, **params):
        self.__dict__.update(params)


class DBConfig(object):
    CONFIG_PATH = Path.home() / Path("work/configs/config.yml")

    def __init__(self, env=None):
        self.db_connection = None
        self.bi_connection = None

        if env and env not in Envs._value2member_map_:
            raise Exception(f'ERROR: passed env: {env} is not valid')
        self.env = env or DEFAULT_ENV

        self._proceed()

    def _proceed(self):
        try:
            cred = load_config(self.CONFIG_PATH)
            conf = cred[self.env]
            conf["schema"] = "daily"
            self.db_connection = DBParams(**conf)

            conf = cred[self.env]
            conf['schema'] = 'samesystem_sisense'
            self.bi_connection = DBParams(**conf)
        except FileNotFoundError:
            logging.debug("Config file not found. Try to load DB data from ENV")
            self.db_connection = DBParams(
                host = os.getenv("DB_HOST"),
                schema= os.getenv("SCHEMA"),
                login= os.getenv("LOGIN"),
                password= os.getenv("PASSWORD"),
                port= os.getenv("DB_PORT")
            )

            self.bi_connection = DBParams(
                host= os.getenv.get('BI_DB_HOST'),
                schema= os.getenv.get('BI_SCHEMA'),
                login=os.getenv.get('BI_LOGIN'),
                password= os.getenv.get('BI_PASSWORD'),
                port= os.getenv.get('BI_DB_PORT')
            )

    def get_config(self):
        return self.db_connection

    def get_bi_config(self):
        return self.bi_connection
