# AGENTS.md — 世界杯数据检索指引

> 给在本仓库工作的 AI agent:**回答世界杯相关问题前,先读 `docs/` 下已抓好的数据文件,不要重新爬取或猜测**。数据是快照,过时才需刷新(见末尾)。

## 1. 数据在哪(`docs/`)

| 你要的信息 | 读这个文件 |
|-----------|-----------|
| **某队的全部信息**(战绩+阵容+积分+伤停,首选) | `docs/profiles/{slug}.json` |
| 某队近期战绩(近10场) | `docs/teams/{slug}.json` |
| 某队阵容/身价/伤停/主教练 | `docs/squads/{slug}.json` |
| 小组积分榜 / 赛程(往期+未来) / 淘汰赛树 | `docs/tournament.json` |
| 最新盘口/赔率(1x2/让球/大小球) | `docs/odds.json` |

`{slug}` = 球队拼音(`ruishi`=瑞士、`baxi1`=巴西、`agenting`=阿根廷、`faguo1`=法国…)。

## 2. 检索决策树

1. **问某一支球队** → 读 `docs/profiles/{slug}.json`(一站式:`standing` 积分、`form`+`recent` 战绩、`coach`+`squad` 阵容、`injuries` 伤停)。
2. **不知道 slug** → 在 `docs/tournament.json` 的 `groups[].standings[]` 里按中文名 `team` 找对应 `slug`;或直接 `ls docs/teams/`。
3. **问积分榜 / 赛程 / 谁打谁 / 淘汰赛对阵** → `docs/tournament.json`(`groups`=积分,`matches`=赛程,`bracket`=淘汰赛树骨架)。
4. **问赔率/盘口** → `docs/odds.json`(按 `matches[].home/away` 找场次,`bookmakers[].markets` 取 `h2h`/`spreads`/`totals`)。
5. **要做跨队统计**(如身价排行、积分排序) → 遍历 `docs/profiles/*.json` 或 `docs/squads/*.json`。

## 3. 关键字段速查

- `profiles/{slug}.json`:`name, group, standing{rank,w,d,l,points,zone}, form{played,w,d,l,gf,ga,win_rate}, recent[], coach, squad{守门员/后卫/中场/前锋:[{name,number,market_value,age,height,...}]}, injuries[], formation(=null)`
- `tournament.json`:`groups[].standings[]{rank,team,slug,w,d,l,points,zone}`、`matches[]{stage,group,round,date,status,home,away,score,ht}`、`bracket[]{stage,slots,matches}`
- `odds.json`:`matches[]{home,away,commence,bookmakers[]{key,title,markets{h2h[],spreads[],totals[]}}}`

## 4. 数据来源与限制(回答时注意)

- 战绩/阵容/积分/赛程来自**球迷屋**(qiumiwu.com);盘口来自 **The Odds API**。
- `formation`(阵型)源头未提供,恒为 `null`;"战略部署框架"= `squad` 按位置分组 + `coach`。
- 淘汰赛对阵小组赛未结束前为空(`bracket[].matches` 多为 `[]`)。
- `tournament.matches` 是赛程页**当前窗口**(临近几日),非全部历史;完整往期由积分体现。
- `injuries` 仅覆盖出现在当前赛程窗口比赛页里的球队;部分球员 `market_value` 等为 `null`。
- 详见 `README.md` 的"已知限制"。

## 5. 数据过时了,如何刷新

需要 Python venv + 依赖(`pip install -r requirements.txt`)。从仓库根运行:

```bash
# 一键全刷(teams→tournament→squad→odds→profiles);无盘口 key 时加 --skip-odds
PYTHONPATH=src python -m worldcup.refresh

# 或单独刷新
PYTHONPATH=src python -m worldcup.cli --all --docs-dir docs/teams        # 战绩
PYTHONPATH=src python -m worldcup.tournament --out docs/tournament.json   # 积分+赛程+树
PYTHONPATH=src python -m worldcup.squad --docs-dir docs/squads            # 阵容/身价/伤停
PYTHONPATH=src python -m worldcup.odds --out docs/odds.json               # 盘口(需 .odds_api_key)
PYTHONPATH=src python -m worldcup.profile --docs-dir docs/profiles        # 合并 profile(纯本地,无网络)
```

- 盘口 API key 放仓库根 `.odds_api_key`(**已 gitignore,勿提交**),或用环境变量 `ODDS_API_KEY`。
- 测试:`PYTHONPATH=src python -m pytest -q`。
