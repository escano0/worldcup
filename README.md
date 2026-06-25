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

### 阵容/身价/伤停(squads/{slug}.json)

```bash
# 抓各队阵容页 + 伤停 -> docs/squads/{slug}.json(48 队)
PYTHONPATH=src python -m worldcup.squad --docs-dir docs/squads
```

每个 `docs/squads/{slug}.json`:`team_id/name/group/coach/squad_updated/formation/player_count/squad/injuries`。
- `squad`:按位置分组 `守门员/后卫/中场/前锋`(即"战略部署框架"),每名球员含 `name/position/number` 及 `market_value`(身价)/`height`/`weight`/`foot`/`dob`/`age`/`nationality`。
- `coach`:主教练;`formation`:阵型源头未公布(临场首发才有)→ 固定 `null`。
- `injuries`:伤停球员(姓名/位置/号码/伤情/状态/日期)。
参数:`--delay`、`--no-injuries`(跳过伤停以加速)。

### 盘口/赔率(odds.json)

球迷屋无结构化赔率,故盘口数据来自 **[The Odds API](https://the-odds-api.com)**(`soccer_fifa_world_cup`)。

```bash
# 拉取世界杯最新盘口 -> docs/odds.json(需 API key)
PYTHONPATH=src python -m worldcup.odds --out docs/odds.json
```

API key 三选一提供(**勿提交进仓库**):`--api-key`、环境变量 `ODDS_API_KEY`,或仓库根的 `.odds_api_key` 文件(已 gitignore)。参数:`--regions`(默认 `eu,uk`)、`--markets`(默认 `h2h,spreads,totals`)。
> 计费:The Odds API 免费档 500 次/月,每次成本 = markets 数 × regions 数(默认 3×2=6)。

`docs/odds.json` 顶层:`source/sport/regions/markets/generated_at/match_count/matches`。每场 `matches[]` 含 `home/away/commence` 与 `bookmakers[]`,每家博彩 `markets` 按类型成 dict:`h2h`(胜平负)、`spreads`(让球/亚盘,含 `point`)、`totals`(大小球,含 `point`)。实测一次取到 19 场、~41 家博彩(h2h 761 / totals 323 / spreads 131 条)。

### 价值投注推荐(recommendations.json)

基于 **Dixon-Coles 概率模型**(`docs/teams` 战绩拟合)对比 **`docs/odds.json` 盘口**,找正期望(value)的 胜平负/大小球/让球,并用**分数凯利**给注码。

```bash
PYTHONPATH=src python -m worldcup.recommend --out docs/recommendations.json
# 调参:--edge 价值阈值(默认0.03) --kelly 凯利分数(默认0.25)
#       --max-odds 滤冷门(默认7.0) --max-stake 单注上限%(默认5.0)
```

`docs/recommendations.json`:`matches[].value_bets[]{market, selection, model_prob, implied_prob, edge, odds, bookmaker, kelly_stake_pct}`。流程:盘口去水(devig)→ `edge = 模型概率 − 隐含概率` → 正EV 才推 → 分数凯利注码 → 冷门/注码护栏。

> ⚠️ **免责 / 重要**:这是**统计建模实验,不是稳赚系统**。当前用的是稀疏数据上的简化 Dixon-Coles(每队约 10 场),且**未做历史回测**,所以会产出**偏多、偏噪声**的"价值"信号(一次 ~100 注/19 场,真实可信优势远少于此)。护栏只挡掉了极端冷门和大注码,**不代表这些注有真实正收益**。仅供个人研究/娱乐参考,博彩有风险。要变可靠需:历史数据回测 + 更严格拟合(MLE)/ML——这部分已暂缓。

## 架构

```
schedule.py  从赛程页枚举 game id
fetcher.py   抓取 game 页(按正文判断成功,绕过站点 404 怪异)
parser.py    html_to_text + parse_team_blocks(战绩) + parse_team_slugs(team_id)
builder.py   构建快照 dict / Schema 校验 / 写每队文件 write_team_files / 写聚合
cli.py       编排:enumerate → fetch → parse → build → validate → 写 docs/teams [→ 聚合]
tournament.py 积分/赛程/bracket → docs/tournament.json
squad.py     阵容/身价/伤停 → docs/squads/{slug}.json
odds.py      The Odds API 盘口 → docs/odds.json
dixon_coles.py 进球泊松概率引擎(攻防强度+τ修正)
teamnames.py  队名映射 en<->zh<->slug(48队)
recommend.py  DC概率 vs 去水盘口 → 价值投注 → docs/recommendations.json
models.py    MatchRecord / TeamForm
```

`docs/` 产物:`teams/{slug}.json`(48 队战绩)、`squads/{slug}.json`(48 队阵容/身价/伤停)、`profiles/{slug}.json`(每队聚合)、`tournament.json`(积分+赛程+树)、`odds.json`(盘口)、`recommendations.json`(价值投注,实验性)。

## 测试

```bash
PYTHONPATH=src python -m pytest -q     # 30 passed
```

## 已知限制
- 每队战绩文件的 `rank`/`group`/`match_id` 暂为 null(可后续从来源补采)。
- 点球大战仅以 `note` 文本保留。
- `tournament.json` 的 `matches` 是赛程页的**当前窗口**(临近几日),非全部 72 场小组赛历史;完整往期结果由 `groups` 积分汇总体现。`matches[].game_id` 暂为 null(源页链接数与比赛数非 1:1,best-effort 跳过)。淘汰赛对阵待小组赛结束后由源公布再生成。
- `squads/*.json` 的 `formation` 恒为 null(源头无阵型,临场首发才有);`injuries` 仅覆盖出现在当前赛程窗口比赛页里的球队(约 10+ 队有数据,其余为空);部分球员 `market_value` 等为 null(源页用 `-` 占位)。
- 反爬:批量抓取已内置 `--delay`;高频使用请自行控频。
