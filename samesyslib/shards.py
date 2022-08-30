import logging

from sqlalchemy.sql import text
from pydantic import BaseSettings, BaseModel

from samesyslib.db import DB
from samesyslib.db_config import DBParams
from samesyslib.utils import get_config_value

logger = logging.getLogger(__name__)


class Shard(BaseModel):
    name: str
    host: str
    port: int
    login: str
    password: str
    schema_: str  # reserved by pydantic

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
                if name == 'schema_':
                    name = 'schema'
                setattr(it, name, value)
            self._conns[shard.dict()['name']] = DB(it)

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


def get_shards_db_client():
    shards = []
    for name, value in get_config_value("db")["shards"].items():
        shards.append(value | {'name': name})

    shards_db_client = ShardsDBClient(ShardsSettings(SHARDS=shards))

    return shards_db_client
