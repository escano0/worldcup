import json
import sqlite3
from typing import Callable, Optional

from ..builder import team_from_dict, team_to_dict
from ..models import TeamForm
from .unicache import UniCache


class TeamFormCache(UniCache[TeamForm]):
    """球队近期战绩的三级缓存。L1 内存 / L2 Redis(可选) / L3 SQLite。

    键为球队 id(pinyin slug)。L3 持久化在 SQLite 表 team_form。
    api_fetcher 为冷未命中时的回源函数 team_id -> Optional[TeamForm](通常由
    上层用 team->game 索引抓取 game 页解析得到);不提供则冷未命中返回 None。
    """

    REDIS_KEY_PREFIX = "worldcup:cache:team_form"

    def __init__(self, db_path, *, redis_client=None,
                 api_fetcher: Optional[Callable[[str], Optional[TeamForm]]] = None):
        super().__init__(redis_client=redis_client, db_session_factory=None, trading_checker=None)
        self._db_path = str(db_path)
        self._api_fetcher = api_fetcher
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS team_form (
                    team_id TEXT PRIMARY KEY,
                    name TEXT,
                    data TEXT NOT NULL,
                    updated_at TEXT
                )"""
            )

    async def _l3_get(self, key: str) -> Optional[TeamForm]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data FROM team_form WHERE team_id = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        return team_from_dict(json.loads(row[0]))

    async def _l3_set(self, key: str, value: TeamForm) -> None:
        payload = json.dumps(team_to_dict(value), ensure_ascii=False)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO team_form (team_id, name, data, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (key, value.name, payload, value.updated_at),
            )

    async def _fetch_from_api(self, key: str) -> Optional[TeamForm]:
        if self._api_fetcher is None:
            return None
        return self._api_fetcher(key)

    def _serialize(self, value: TeamForm) -> str:
        return json.dumps(team_to_dict(value), ensure_ascii=False)

    def _deserialize(self, data: str) -> TeamForm:
        return team_from_dict(json.loads(data))
