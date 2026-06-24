# 世界杯球队近期战绩数据文档 — 设计 (Spec)

- **日期**: 2026-06-24
- **状态**: 已批准设计,待实现
- **作者**: 与 Claude 协作 brainstorm
- **数据来源**: 球迷屋 (qiumiwu.com) — 页面服务端渲染,可直接抓取 HTML 解析

## 1. 背景与目标

worldcup 项目当前为空,需要一个**供程序读取的 JSON 数据文件**,用于存放**世界杯所有球队的近期战绩(比分)**,并能配合项目的三级缓存(unicache)按球队粒度读取。

数据真相在来源网站(球迷屋),本文件是抓取后的**结构化快照**,不手工编辑,每次刷新整队覆盖。

### 目标
- 一份聚合 JSON,按球队组织,每队含近 N 场战绩(默认 10 场)与汇总。
- 每条记录同时提供"本队视角"(前端零计算直接用)与"原始比分"(保真可核对)。
- 结构契合三级缓存:每支球队是一个可独立缓存/失效的自包含单元。

### 非目标 (YAGNI)
- 不做全量比赛级的查询/统计引擎(那是方案 C/B,将来需要再升级)。
- 不存未开赛的赛程(本文件只存**已结束**的战绩)。
- 不在本文件做点球大战的复杂建模(仅以 `note` 文本保留)。

## 2. 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储结构 | **方案 A:以球队为中心(去规范化)** | 主访问模式是"按队取近期战绩";每队自包含 → 直接对应缓存键 `wc:form:{team_id}`。同一场比赛在两队各存一份,但因是只读快照、整队覆盖刷新,不存在改一处漏一处的漂移风险。 |
| `teams` 容器 | **map(键=team_id)** 而非数组 | O(1) 按队取数,键即缓存键。 |
| 记录视角 | **双写**:本队视角 + 原始比分 | 本队视角省前端计算;原始比分用于核对/重算/关联两队。 |
| 稳定键 | **team_id** 优先,名称 slug 兜底 | 避免简繁体/译名差异("斯洛文尼/斯洛文尼亚")导致键漂移。 |

将来若需要"全量比赛统计"等场景,可平滑升级到混合方案 C(`matches` 唯一真相 + 每队 `form` 摘要)。

## 3. 文件布局

| 文件 | 作用 |
|------|------|
| `projects/worldcup/data/recent-form.json` | 全部球队战绩的聚合快照(三级缓存的 L3 冷数据层) |
| `projects/worldcup/data/recent-form.schema.json` | JSON Schema,供程序校验 |

## 4. 数据结构

### 4.1 顶层

```jsonc
{
  "schema_version": "1.0",
  "source": "qiumiwu",
  "tournament": "2026-world-cup",
  "generated_at": "2026-06-24T18:00:00+08:00",  // 整份快照生成时间(ISO8601)
  "teams": {
    "<team_id>": { /* TeamObject */ }
  }
}
```

### 4.2 TeamObject

```jsonc
{
  "team_id": "string",            // 来源站点队伍ID(稳定键);抓不到时退化为名称slug
  "name": "瑞士",
  "name_en": "Switzerland",       // 可空
  "rank": 17,                     // 世界排名, int | null
  "group": "B",                   // 小组, string | null
  "form": {                       // 近N场汇总(本队视角)
    "played": 10, "w": 4, "d": 5, "l": 1,
    "gf": 20, "ga": 10, "win_rate": 0.40
  },
  "recent": [ /* MatchRecord[],按 date 倒序,默认最多10场 */ ],
  "updated_at": "2026-06-24T18:00:00+08:00"  // 本队记录刷新时间(缓存按队失效用)
}
```

### 4.3 MatchRecord(本队视角 + 原始保真)

```jsonc
{
  "match_id": "107506805271",   // 来源 game id,可空;用于去重/关联两队
  "date": "2026-06-19",          // YYYY-MM-DD
  "competition": "男足世界杯",
  "opponent": "波黑",
  "is_home": true,               // 本队是否主场(由 home 与 name 比对得出)
  "gf": 4,                       // 本队进球
  "ga": 1,                       // 本队失球
  "result": "W",                 // W | D | L,本队视角
  "home": "瑞士",                // 原始主队
  "away": "波黑",                // 原始客队
  "score": "4-1",                // 原始比分(主-客)
  "note": null                   // 可空,如点球 "点球5-4"
}
```

### 4.4 字段必填/可空一览

- **必填**:`date`, `competition`, `opponent`, `is_home`, `gf`, `ga`, `result`, `home`, `away`, `score`
- **可空**:`team_id`, `name_en`, `rank`, `group`, `match_id`, `note`
- **取值约束**:`result ∈ {W, D, L}`;`gf/ga` 为非负整数;`win_rate ∈ [0,1]`;日期为 `YYYY-MM-DD`;时间戳为 ISO8601。
- **`win_rate` 口径**:`w / played`(胜场÷场次,不含平局加权),与来源页"胜率"一致(例:瑞士 4/10 = 0.40)。

## 5. JSON Schema(draft-07,初版)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "World Cup Recent Form",
  "type": "object",
  "required": ["schema_version", "source", "generated_at", "teams"],
  "properties": {
    "schema_version": { "type": "string" },
    "source": { "type": "string" },
    "tournament": { "type": "string" },
    "generated_at": { "type": "string", "format": "date-time" },
    "teams": {
      "type": "object",
      "additionalProperties": { "$ref": "#/definitions/team" }
    }
  },
  "definitions": {
    "team": {
      "type": "object",
      "required": ["name", "form", "recent", "updated_at"],
      "properties": {
        "team_id": { "type": ["string", "null"] },
        "name": { "type": "string" },
        "name_en": { "type": ["string", "null"] },
        "rank": { "type": ["integer", "null"] },
        "group": { "type": ["string", "null"] },
        "form": {
          "type": "object",
          "required": ["played", "w", "d", "l", "gf", "ga", "win_rate"],
          "properties": {
            "played": { "type": "integer", "minimum": 0 },
            "w": { "type": "integer", "minimum": 0 },
            "d": { "type": "integer", "minimum": 0 },
            "l": { "type": "integer", "minimum": 0 },
            "gf": { "type": "integer", "minimum": 0 },
            "ga": { "type": "integer", "minimum": 0 },
            "win_rate": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        },
        "recent": { "type": "array", "items": { "$ref": "#/definitions/match" } },
        "updated_at": { "type": "string", "format": "date-time" }
      }
    },
    "match": {
      "type": "object",
      "required": ["date", "competition", "opponent", "is_home", "gf", "ga", "result", "home", "away", "score"],
      "properties": {
        "match_id": { "type": ["string", "null"] },
        "date": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
        "competition": { "type": "string" },
        "opponent": { "type": "string" },
        "is_home": { "type": "boolean" },
        "gf": { "type": "integer", "minimum": 0 },
        "ga": { "type": "integer", "minimum": 0 },
        "result": { "type": "string", "enum": ["W", "D", "L"] },
        "home": { "type": "string" },
        "away": { "type": "string" },
        "score": { "type": "string" },
        "note": { "type": ["string", "null"] }
      }
    }
  }
}
```

## 6. Golden 示例(瑞士,真实抓取数据)

下例为从来源页面 `game/107506805271` 实际解析出的瑞士近 10 场,可作为实现的回归 fixture(已自洽:4 胜 5 平 1 负、进 20 失 10、胜率 0.40)。

```json
{
  "schema_version": "1.0",
  "source": "qiumiwu",
  "tournament": "2026-world-cup",
  "generated_at": "2026-06-24T18:00:00+08:00",
  "teams": {
    "switzerland": {
      "team_id": "switzerland",
      "name": "瑞士",
      "name_en": "Switzerland",
      "rank": 17,
      "group": "B",
      "form": { "played": 10, "w": 4, "d": 5, "l": 1, "gf": 20, "ga": 10, "win_rate": 0.40 },
      "updated_at": "2026-06-24T18:00:00+08:00",
      "recent": [
        { "date": "2026-06-19", "competition": "男足世界杯", "opponent": "波黑",   "is_home": true,  "gf": 4, "ga": 1, "result": "W", "home": "瑞士",   "away": "波黑",   "score": "4-1", "note": null },
        { "date": "2026-06-14", "competition": "男足世界杯", "opponent": "卡塔尔", "is_home": false, "gf": 1, "ga": 1, "result": "D", "home": "卡塔尔", "away": "瑞士",   "score": "1-1", "note": null },
        { "date": "2026-06-07", "competition": "国际赛",    "opponent": "澳大利亚","is_home": false, "gf": 1, "ga": 1, "result": "D", "home": "澳大利亚","away": "瑞士",   "score": "1-1", "note": null },
        { "date": "2026-05-31", "competition": "国际赛",    "opponent": "约旦",   "is_home": true,  "gf": 4, "ga": 1, "result": "W", "home": "瑞士",   "away": "约旦",   "score": "4-1", "note": null },
        { "date": "2026-04-01", "competition": "国际赛",    "opponent": "挪威",   "is_home": false, "gf": 0, "ga": 0, "result": "D", "home": "挪威",   "away": "瑞士",   "score": "0-0", "note": null },
        { "date": "2026-03-28", "competition": "国际赛",    "opponent": "德国",   "is_home": true,  "gf": 3, "ga": 4, "result": "L", "home": "瑞士",   "away": "德国",   "score": "3-4", "note": null },
        { "date": "2025-11-19", "competition": "世欧预",    "opponent": "科索沃", "is_home": false, "gf": 1, "ga": 1, "result": "D", "home": "科索沃", "away": "瑞士",   "score": "1-1", "note": null },
        { "date": "2025-11-16", "competition": "世欧预",    "opponent": "瑞典",   "is_home": true,  "gf": 4, "ga": 1, "result": "W", "home": "瑞士",   "away": "瑞典",   "score": "4-1", "note": null },
        { "date": "2025-10-14", "competition": "世欧预",    "opponent": "斯洛文尼亚","is_home": false,"gf": 0, "ga": 0, "result": "D", "home": "斯洛文尼亚","away": "瑞士", "score": "0-0", "note": null },
        { "date": "2025-10-11", "competition": "世欧预",    "opponent": "瑞典",   "is_home": false, "gf": 2, "ga": 0, "result": "W", "home": "瑞典",   "away": "瑞士",   "score": "0-2", "note": null }
      ]
    }
  }
}
```

## 7. 三级缓存对接

- **角色**:本 JSON 文件是 L3 冷数据/快照层(将来可换 DB)。
- **缓存键**:每队 `wc:form:{team_id}` → 值为整个 TeamObject。
- **读路径**:L1 内存 → L2(Redis/本地) → L3(本文件) → 回源抓取。
- **失效粒度**:整份用顶层 `generated_at`;单队用 `updated_at`。TTL 建议:比赛日短、平时长。
- 详细以项目 unicache 设计为准(见 CLAUDE.md 引用的 `/docs/unicache-design.md`)。

## 8. 约束与边界情况

- 只存**已结束**的比赛;未开赛赛程不进本文件。
- 比分解析需兼容**带空格**写法("4 - 1")。
- **点球大战**:常规时间比分进 `gf/ga` 与 `score`,点球结果写入 `note`(如 `"点球5-4"`);`result` 以晋级/官方判定为准,实现时需明确规则。
- `is_home` 由原始 `home` 与本队 `name` 比对得出。
- 键稳定性:优先 `team_id`;若来源仅有名称,用确定性 slug 兜底,并在同一来源内保持一致。

## 9. 测试计划

- **Schema 校验**:用第 5 节 JSON Schema 校验整份文件。
- **单元测试**:
  - 比分解析器(含空格、点球)。
  - `result` 计算(W/D/L,本队视角)。
  - `is_home` 判定。
  - `form` 汇总(由 `recent` 聚合,与来源摘要对账)。
- **Golden fixture**:用第 6 节瑞士真实数据做回归。

## 10. 待办/未来

- 实现抓取器:输入 game id / 球队,输出本结构(Python 或 Node,待定)。
- 采集真实 `team_id`(来源站点 schedule 接口含 teamId 参数)。
- 如需全量比赛统计,升级到方案 C。
