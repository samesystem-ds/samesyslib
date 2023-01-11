import logging
import time

from sqlalchemy.sql import text
from pydantic import BaseSettings, BaseModel
from typing import Optional

from samesyslib.db import DB
from samesyslib.db_config import DBParams
from samesyslib.utils import get_config_value

logger = logging.getLogger(__name__)

"""
USAGE

# hard requirement
# ENV VARIABLE => config_path=PATH_TO_YOUR_YML_CONFIG_FILE.yml
as underneath we use samesyslib/utils.py.get_config_value
to get value

yml should be structured like:
...
db:
  shards:
    shardK:
      host: 0.0.0.0
      port: 3333
      login: login
      password: pass
      schema: schema
    shardM:
      host: 0.0.0.0
      port: 3333
      login: login
      password: pass
      schema: schema
    shardN:
      host: 0.0.0.0
      port: 3333
      login: login
      password: pass
      schema: schema
  ...


from samesyslib.shards import get_shards_db_client
shards_db_client = get_shards_db_client()
data = shards_db_client.combined_query("SELECT NOW()")
"""


class Shard(BaseModel):
    name: str
    host: str
    port: int
    login: str
    password: str
    schema_: str  # reserved by pydantic
    connect_args: Optional[dict] = {}

    class Config:
        fields = {"schema_": "schema"}


class ShardsSettings(BaseSettings):
    SHARDS: list[Shard]


class ShardsDBClient:
    def __init__(self, shards_settings):
        self._conns = {}
        for shard in shards_settings.SHARDS:
            it = DBParams()
            for name, value in shard.dict().items():
                if name == "schema_":
                    name = "schema"
                setattr(it, name, value)
            it._shard = shard.name
            self._conns[shard.dict()["name"]] = DB(it)

    def query(self, sql):
        result = {}
        for name, conn in self._conns.items():
            result[name] = conn.execute(text(sql)).fetchall()
        return result

    def combined_query(self, sql):
        logger.debug(f"SQL query: {sql}")
        combined = []
        for shard_name, results in self.query(sql).items():
            for it in results:
                row = dict(it) | {"_shard": shard_name}
                combined.append(row)
        return combined

    def combined_get_and_replace(self, sql, conn, table):
        for name, db in self._conns.items():
            result_df = db.get(sql)
            result_df["_shard"] = name
            conn.send_replace(result_df, table=table)

    def get_shards_conns(self):
        return [db for name, db in self._conns.items()]


def get_shards_db_client():
    shards = []
    for name, value in get_config_value("db")["shards"].items():
        shards.append(value | {"name": name})

    shards_db_client = ShardsDBClient(ShardsSettings(SHARDS=shards))

    return shards_db_client


def execute_sql(engine, sql):
    start_time = time.time()
    engine.execute(sql)

    return {"shard": engine.get_shard(), "duration": time.time() - start_time}
