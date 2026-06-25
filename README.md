# worldcup — 世界杯球队近期战绩抓取

从球迷屋(qiumiwu.com)抓取 2026 世界杯各球队的**近期战绩**,**每支球队写一个 JSON 文件到 `docs/teams/`**(文件名为球队 pinyin slug,如 `docs/teams/ruishi.json`),可选再产出一个聚合快照。

## 安装

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## 用法

```bash
# 全部球队:从世界杯赛程页枚举所有 game id 后逐场抓取,每队写 docs/teams/{slug}.json(48 队)
PYTHONPATH=src python -m worldcup.cli --all --docs-dir docs/teams

# 单场(传 game id):抓该场两队战绩,写到 docs/teams/
PYTHONPATH=src python -m worldcup.cli 107506805271 --docs-dir docs/teams

# 额外再写一个聚合 JSON(可选)
PYTHONPATH=src python -m worldcup.cli --all --docs-dir docs/teams --out data/recent-form.json
```

参数:`--docs-dir`(每队文件输出目录,默认 `docs/teams`)、`--out`(可选聚合快照)、`--delay`(批量每场间隔秒,默认 0.5)、`--schema`(校验用 schema 路径)。
`--all` 模式下个别未开赛/无战绩的场次会被跳过并打印 `skip ...`;**全部场次都失败时进程以非 0 退出**(便于自动化区分"个别跳过"与"整体崩了")。

### 赛事树/积分(tournament.json)

```bash
# 生成 docs/tournament.json:各组积分 + 赛程(往期+未来)+ 淘汰赛树骨架
PYTHONPATH=src python -m worldcup.tournament --out docs/tournament.json
```

`docs/tournament.json` 顶层:
- `groups`:12 组(A–L)积分榜,每队 `rank/team/slug/w/d/l/points/zone`(zone=晋级32强|晋级待定)。
- `matches`:赛程页当前窗口的小组赛(往期 `status:finished` 带 `score`/`ht`,未来 `status:scheduled`)。
- `bracket`:淘汰赛树骨架 `round_of_32→round_of_16→quarter_final→semi_final→third_place→final`,每轮带 `slots`;对阵随源公布填入 `matches`(当前小组赛未完,均为空)。

## 数据结构

每个 `docs/teams/{slug}.json` 是一支球队对象(以球队为中心,方案 A):

```jsonc
// docs/teams/ruishi.json
{
  "team_id": "ruishi", "name": "瑞士", "name_en": null, "rank": null, "group": null,
  "form": {"played":10,"w":4,"d":5,"l":1,"gf":20,"ga":10,"win_rate":0.4},
  "recent": [
    {"date":"2026-06-19","competition":"男足世界杯","opponent":"波黑",
     "is_home":true,"gf":4,"ga":1,"result":"W",
     "home":"瑞士","away":"波黑","score":"4-1","match_id":null,"note":null}
  ],
  "updated_at": "..."
}
```

`--out` 写出的聚合快照则把所有球队收进顶层 `teams` map(键为 slug),并带 `schema_version`/`generated_at` 等元数据,字段约束见 `data/recent-form.schema.json`。设计与计划详见 `docs/superpowers/specs/` 与 `docs/superpowers/plans/`。

## 架构

```
schedule.py  从赛程页枚举 game id
fetcher.py   抓取 game 页(按正文判断成功,绕过站点 404 怪异)
parser.py    html_to_text + parse_team_blocks(战绩) + parse_team_slugs(team_id)
builder.py   构建快照 dict / Schema 校验 / 写每队文件 write_team_files / 写聚合
cli.py       编排:enumerate → fetch → parse → build → validate → 写 docs/teams [→ 聚合]
models.py    MatchRecord / TeamForm
```

## 测试

```bash
PYTHONPATH=src python -m pytest -q     # 30 passed
```

## 已知限制
- 每队战绩文件的 `rank`/`group`/`match_id` 暂为 null(可后续从来源补采)。
- 点球大战仅以 `note` 文本保留。
- `tournament.json` 的 `matches` 是赛程页的**当前窗口**(临近几日),非全部 72 场小组赛历史;完整往期结果由 `groups` 积分汇总体现。`matches[].game_id` 暂为 null(源页链接数与比赛数非 1:1,best-effort 跳过)。淘汰赛对阵待小组赛结束后由源公布再生成。
- 反爬:批量抓取已内置 `--delay`;高频使用请自行控频。
