# worldcup — 世界杯球队近期战绩抓取

从球迷屋(qiumiwu.com)抓取 2026 世界杯各球队的**近期战绩**,产出以球队为中心、符合 JSON Schema 的 `data/recent-form.json`,并可写入三级缓存(L1 内存 / L2 Redis / L3 SQLite)。

## 安装

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## 用法

```bash
# 单场(传 game id):抓该场两队战绩
PYTHONPATH=src python -m worldcup.cli 107506805271 --out data/recent-form.json

# 全部球队:从世界杯赛程页枚举所有 game id 后逐场抓取(48 队)
PYTHONPATH=src python -m worldcup.cli --all --out data/recent-form.json

# 同时写入三级缓存的 L3 SQLite(对接 UniCache)
PYTHONPATH=src python -m worldcup.cli --all --out data/recent-form.json --cache-db data/wc-cache.db
```

参数:`--delay`(批量每场间隔秒,默认 0.5)、`--schema`(校验用 schema 路径)。
`--all` 模式下个别未开赛/无战绩的场次会被跳过并打印 `skip ...`;**全部场次都失败时进程以非 0 退出**(便于自动化区分"个别跳过"与"整体崩了")。

## 数据结构

以球队为中心(方案 A),键为球队 pinyin slug(如 `ruishi`、`baxi1`):

```jsonc
{
  "schema_version": "1.0", "source": "qiumiwu", "tournament": "2026-world-cup",
  "generated_at": "...",
  "teams": {
    "ruishi": {
      "team_id": "ruishi", "name": "瑞士", "rank": null, "group": null,
      "form": {"played":10,"w":4,"d":5,"l":1,"gf":20,"ga":10,"win_rate":0.4},
      "recent": [
        {"date":"2026-06-19","competition":"男足世界杯","opponent":"波黑",
         "is_home":true,"gf":4,"ga":1,"result":"W",
         "home":"瑞士","away":"波黑","score":"4-1","match_id":null,"note":null}
      ],
      "updated_at": "..."
    }
  }
}
```

设计与计划详见 `docs/superpowers/specs/` 与 `docs/superpowers/plans/`;字段约束见 `data/recent-form.schema.json`。

## 架构

```
schedule.py  从赛程页枚举 game id
fetcher.py   抓取 game 页(按正文判断成功,绕过站点 404 怪异)
parser.py    html_to_text + parse_team_blocks(战绩) + parse_team_slugs(team_id)
builder.py   构建快照 dict / Schema 校验 / 读写 / 序列化反序列化
cli.py       编排:enumerate → fetch → parse → build → validate → write [→ cache]
cache/       UniCache 三级缓存抽象 + TeamFormCache(L3 SQLite)
models.py    MatchRecord / TeamForm
```

三级缓存对齐 AlphaMate 的 `UniCache` 契约(`get` 按 L1→L2→L3→API 查找,`set` write-through):

```python
import asyncio
from worldcup.cache.team_form_cache import TeamFormCache

cache = TeamFormCache("data/wc-cache.db")     # 可传 redis_client / api_fetcher
entry = asyncio.run(cache.get("ruishi"))       # entry.source ∈ {l1,l2,l3,api}
print(entry.value.name, entry.value.form)
```

## 测试

```bash
PYTHONPATH=src python -m pytest -q     # 35 passed
```

## 已知限制
- `rank`/`group` 暂为 null;`match_id` 暂为 null(可后续从来源补采)。
- 点球大战仅以 `note` 文本保留。
- 缓存 `_fetch_from_api`(冷未命中回源)需上层注入 `api_fetcher`;CLI 仅做 L3 写入(population),读取由消费方走 `TeamFormCache`。
- 反爬:批量抓取已内置 `--delay`;高频使用请配合缓存。
