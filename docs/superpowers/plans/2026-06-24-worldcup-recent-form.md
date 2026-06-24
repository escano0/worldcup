# 世界杯球队近期战绩抓取与存储 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 抓取球迷屋比赛页,解析出世界杯各球队近期战绩,产出符合 spec 的 `data/recent-form.json`(方案 A,以球队为中心)。

**Architecture:** 页面是服务端渲染,数据内嵌 HTML。流水线为 `fetch(网络) → html_to_text(去标签) → 正则解析球队战绩块 → 构建快照 dict → JSON Schema 校验 → 写文件`。解析是纯函数(可离线测试),网络层(fetcher)单独隔离。

**Tech Stack:** Python 3.10+;requests(抓取)、beautifulsoup4(去标签)、jsonschema(校验)、pytest(测试)。

**Spec:** `docs/superpowers/specs/2026-06-24-worldcup-recent-form-design.md`

---

## File Structure

```
projects/worldcup/
├── data/
│   ├── recent-form.schema.json     # JSON Schema(Task 2)
│   └── recent-form.json            # 产物(运行 CLI 生成,不入库)
├── src/worldcup/
│   ├── __init__.py
│   ├── models.py                   # MatchRecord / TeamForm 数据类(Task 3)
│   ├── parser.py                   # 纯函数:去标签 + 解析战绩(Task 4-5)
│   ├── builder.py                  # 构建快照 dict + 校验 + 写文件(Task 6)
│   ├── fetcher.py                  # 抓取(处理 404-有正文 的怪异)(Task 7)
│   └── cli.py                      # 命令行编排(Task 7)
├── tests/
│   ├── __init__.py
│   ├── fixtures/recent_form_sample.html  # 合成小样本(Task 5)
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_builder.py
│   └── test_fetcher.py
└── requirements.txt
```

---

### Task 1: 项目骨架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `src/worldcup/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: 写 requirements.txt**

```
requests>=2.31
beautifulsoup4>=4.12
jsonschema>=4.21
pytest>=8.0
```

- [ ] **Step 2: 建空包文件**

`src/worldcup/__init__.py`:
```python
```
`tests/__init__.py`:
```python
```

- [ ] **Step 3: 写 .gitignore**

```
__pycache__/
*.pyc
.venv/
data/recent-form.json
.pytest_cache/
```

- [ ] **Step 4: 安装依赖并确认 pytest 可运行**

Run:
```bash
cd /Users/uc/Documents/projects/worldcup
python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt
PYTHONPATH=src python -m pytest -q
```
Expected: `no tests ran`(无测试,但 pytest 正常启动)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/worldcup/__init__.py tests/__init__.py .gitignore
git commit -m "chore: 项目骨架与依赖"
```

---

### Task 2: JSON Schema 文件

**Files:**
- Create: `data/recent-form.schema.json`
- Test: `tests/test_schema.py`

- [ ] **Step 1: 写失败测试**

`tests/test_schema.py`:
```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA = json.loads(Path("data/recent-form.schema.json").read_text(encoding="utf-8"))

def _good_snapshot():
    return {
        "schema_version": "1.0",
        "source": "qiumiwu",
        "tournament": "2026-world-cup",
        "generated_at": "2026-06-24T18:00:00+08:00",
        "teams": {
            "瑞士": {
                "team_id": None, "name": "瑞士", "name_en": None,
                "rank": 17, "group": "B",
                "form": {"played": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "win_rate": 1.0},
                "updated_at": "2026-06-24T18:00:00+08:00",
                "recent": [{
                    "match_id": None, "date": "2026-06-19", "competition": "男足世界杯",
                    "opponent": "波黑", "is_home": True, "gf": 4, "ga": 1, "result": "W",
                    "home": "瑞士", "away": "波黑", "score": "4-1", "note": None
                }],
            }
        },
    }

def test_good_snapshot_validates():
    jsonschema.validate(_good_snapshot(), SCHEMA)

def test_bad_result_rejected():
    snap = _good_snapshot()
    snap["teams"]["瑞士"]["recent"][0]["result"] = "X"  # 非 W/D/L
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(snap, SCHEMA)

def test_missing_required_match_field_rejected():
    snap = _good_snapshot()
    del snap["teams"]["瑞士"]["recent"][0]["score"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(snap, SCHEMA)
```

- [ ] **Step 2: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_schema.py -q`
Expected: FAIL(`data/recent-form.schema.json` 不存在 → FileNotFoundError)

- [ ] **Step 3: 写 schema 文件**

`data/recent-form.schema.json`:
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
    "generated_at": { "type": "string" },
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
        "updated_at": { "type": "string" }
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

- [ ] **Step 4: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_schema.py -q`
Expected: PASS(3 passed)

- [ ] **Step 5: Commit**

```bash
git add data/recent-form.schema.json tests/test_schema.py
git commit -m "feat: recent-form JSON Schema 与校验测试"
```

---

### Task 3: 数据模型 models.py

**Files:**
- Create: `src/worldcup/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/test_models.py`:
```python
from worldcup.models import MatchRecord, TeamForm

def test_match_record_defaults():
    m = MatchRecord(
        date="2026-06-19", competition="男足世界杯", opponent="波黑",
        is_home=True, gf=4, ga=1, result="W", home="瑞士", away="波黑", score="4-1",
    )
    assert m.match_id is None and m.note is None
    assert m.result == "W"

def test_team_form_defaults():
    t = TeamForm(
        name="瑞士",
        form={"played": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "win_rate": 1.0},
        recent=[], updated_at="2026-06-24T18:00:00+08:00",
    )
    assert t.team_id is None and t.name_en is None and t.rank is None and t.group is None
    assert t.recent == []
```

- [ ] **Step 2: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_models.py -q`
Expected: FAIL(`ModuleNotFoundError: worldcup.models`)

- [ ] **Step 3: 写实现**

`src/worldcup/models.py`:
```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MatchRecord:
    date: str
    competition: str
    opponent: str
    is_home: bool
    gf: int
    ga: int
    result: str          # "W" | "D" | "L"(本队视角)
    home: str
    away: str
    score: str           # 原始比分 "主-客"
    match_id: Optional[str] = None
    note: Optional[str] = None


@dataclass
class TeamForm:
    name: str
    form: dict           # {"played","w","d","l","gf","ga","win_rate"}
    recent: list         # list[MatchRecord]
    updated_at: str
    team_id: Optional[str] = None
    name_en: Optional[str] = None
    rank: Optional[int] = None
    group: Optional[str] = None
```

- [ ] **Step 4: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_models.py -q`
Expected: PASS(2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/worldcup/models.py tests/test_models.py
git commit -m "feat: MatchRecord / TeamForm 数据模型"
```

---

### Task 4: 解析纯函数 — 比分/结果/单场记录

**Files:**
- Create: `src/worldcup/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: 写失败测试**

`tests/test_parser.py`:
```python
import pytest
from worldcup.parser import parse_score, compute_result, build_match_record

def test_parse_score_with_spaces():
    assert parse_score("4 - 1") == (4, 1)
    assert parse_score("0-0") == (0, 0)

def test_parse_score_invalid():
    with pytest.raises(ValueError):
        parse_score("待定")

def test_compute_result():
    assert compute_result(4, 1) == "W"
    assert compute_result(1, 1) == "D"
    assert compute_result(0, 2) == "L"

def test_build_match_record_team_is_home():
    m = build_match_record("瑞士", "2026-06-19", "男足世界杯", "瑞士", 4, 1, "波黑")
    assert m.is_home is True and m.opponent == "波黑"
    assert m.gf == 4 and m.ga == 1 and m.result == "W" and m.score == "4-1"

def test_build_match_record_team_is_away():
    m = build_match_record("瑞士", "2026-06-14", "男足世界杯", "卡塔尔", 1, 1, "瑞士")
    assert m.is_home is False and m.opponent == "卡塔尔"
    assert m.gf == 1 and m.ga == 1 and m.result == "D" and m.score == "1-1"

def test_build_match_record_unknown_team_raises():
    with pytest.raises(ValueError):
        build_match_record("瑞士", "2026-06-14", "国际赛", "法国", 2, 0, "德国")
```

- [ ] **Step 2: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_parser.py -q`
Expected: FAIL(`ModuleNotFoundError: worldcup.parser`)

- [ ] **Step 3: 写实现**

`src/worldcup/parser.py`:
```python
import re
from .models import MatchRecord

_SCORE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def parse_score(score: str):
    """'4 - 1' 或 '4-1' -> (4, 1);无法解析则抛 ValueError。"""
    m = _SCORE_RE.match(score)
    if not m:
        raise ValueError(f"unparseable score: {score!r}")
    return int(m.group(1)), int(m.group(2))


def compute_result(gf: int, ga: int) -> str:
    """本队视角的胜平负。"""
    if gf > ga:
        return "W"
    if gf < ga:
        return "L"
    return "D"


def build_match_record(team_name, date, competition, home, home_goals, away_goals, away, match_id=None):
    """把一场原始比赛(主队 home_goals-away_goals 客队)转成 team_name 视角的记录。"""
    if team_name == home:
        is_home, gf, ga, opponent = True, home_goals, away_goals, away
    elif team_name == away:
        is_home, gf, ga, opponent = False, away_goals, home_goals, home
    else:
        raise ValueError(f"{team_name!r} not in match {home!r} vs {away!r}")
    return MatchRecord(
        date=date, competition=competition, opponent=opponent,
        is_home=is_home, gf=gf, ga=ga, result=compute_result(gf, ga),
        home=home, away=away, score=f"{home_goals}-{away_goals}",
        match_id=match_id, note=None,
    )
```

- [ ] **Step 4: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_parser.py -q`
Expected: PASS(6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/worldcup/parser.py tests/test_parser.py
git commit -m "feat: 比分解析/结果计算/单场记录构建"
```

---

### Task 5: 解析 HTML 战绩块 — html_to_text + parse_team_blocks

**Files:**
- Modify: `src/worldcup/parser.py`
- Create: `tests/fixtures/recent_form_sample.html`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: 建测试 fixture**

`tests/fixtures/recent_form_sample.html`:
```html
<html><body>
<script>var x = "最近战绩 伪造 1 - 9 数据";</script>
<div class="block">交战历史 暂无数据</div>
<div class="title">最近战绩</div>
<div class="team">瑞士 进球20/失球10/胜率40.0% 4胜 5平 1负</div>
<div class="row">2026-06-19 男足世界杯 瑞士 4 - 1 波黑</div>
<div class="row">2026-06-14 男足世界杯 卡塔尔 1 - 1 瑞士</div>
<div class="team">加拿大 进球15/失球9/胜率30.0% 3胜 5平 2负</div>
<div class="row">2026-06-19 男足世界杯 加拿大 6 - 0 卡塔尔</div>
<div class="row">2026-06-13 男足世界杯 加拿大 1 - 1 波黑</div>
</body></html>
```

- [ ] **Step 2: 写失败测试(追加到 tests/test_parser.py)**

```python
from pathlib import Path
from worldcup.parser import html_to_text, parse_team_blocks

FIXTURE = Path("tests/fixtures/recent_form_sample.html").read_text(encoding="utf-8")

def test_html_to_text_strips_scripts_and_tags():
    text = html_to_text(FIXTURE)
    assert "最近战绩" in text and "男足世界杯" in text
    assert "<div" not in text
    assert "伪造" not in text  # script 内容被剔除

def test_parse_team_blocks_two_teams():
    teams = parse_team_blocks(html_to_text(FIXTURE), updated_at="2026-06-24T18:00:00+08:00")
    names = {t.name for t in teams}
    assert names == {"瑞士", "加拿大"}

def test_parse_team_blocks_switzerland_form_and_rows():
    teams = {t.name: t for t in parse_team_blocks(html_to_text(FIXTURE), updated_at="T")}
    sui = teams["瑞士"]
    assert sui.form == {"played": 10, "w": 4, "d": 5, "l": 1, "gf": 20, "ga": 10, "win_rate": 0.4}
    assert len(sui.recent) == 2
    m0, m1 = sui.recent
    assert (m0.opponent, m0.is_home, m0.gf, m0.ga, m0.result) == ("波黑", True, 4, 1, "W")
    assert (m1.opponent, m1.is_home, m1.gf, m1.ga, m1.result) == ("卡塔尔", False, 1, 1, "D")
    assert sui.updated_at == "T"
```

- [ ] **Step 3: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_parser.py -q`
Expected: FAIL(`ImportError: cannot import name 'html_to_text'`)

- [ ] **Step 4: 实现(追加到 src/worldcup/parser.py)**

在 `parser.py` 顶部 import 处补上 BeautifulSoup,并在文件末尾追加函数:
```python
from bs4 import BeautifulSoup
from .models import TeamForm

_WS_RE = re.compile(r"\s+")
_TEAM_HEADER_RE = re.compile(
    r"(\S+)\s+进球(\d+)/失球(\d+)/胜率([\d.]+)%\s*(\d+)胜\s*(\d+)平\s*(\d+)负"
)
_ROW_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+(\S+)\s+(\S+)\s+(\d+)\s*-\s*(\d+)\s+(\S+)"
)


def html_to_text(html: str) -> str:
    """去掉 script/style 与所有标签,折叠空白,返回纯文本。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return _WS_RE.sub(" ", soup.get_text(" ")).strip()


def parse_team_blocks(text: str, updated_at: str):
    """从纯文本的『最近战绩』区块解析出每支球队的 TeamForm 列表。"""
    idx = text.find("最近战绩")
    section = text[idx:] if idx >= 0 else text
    headers = list(_TEAM_HEADER_RE.finditer(section))
    teams = []
    for i, h in enumerate(headers):
        name = h.group(1)
        gf_total, ga_total = int(h.group(2)), int(h.group(3))
        w, d, l = int(h.group(5)), int(h.group(6)), int(h.group(7))
        played = w + d + l
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
        recent = []
        for r in _ROW_RE.finditer(section[start:end]):
            date, comp, home = r.group(1), r.group(2), r.group(3)
            hg, ag, away = int(r.group(4)), int(r.group(5)), r.group(6)
            recent.append(build_match_record(name, date, comp, home, hg, ag, away))
        win_rate = round(w / played, 4) if played else 0.0
        form = {"played": played, "w": w, "d": d, "l": l,
                "gf": gf_total, "ga": ga_total, "win_rate": win_rate}
        teams.append(TeamForm(name=name, form=form, recent=recent, updated_at=updated_at))
    return teams
```

- [ ] **Step 5: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_parser.py -q`
Expected: PASS(9 passed)

- [ ] **Step 6: Commit**

```bash
git add src/worldcup/parser.py tests/fixtures/recent_form_sample.html tests/test_parser.py
git commit -m "feat: HTML 去标签与球队战绩块解析"
```

---

### Task 6: 构建快照 builder.py(dict 化 + 校验 + 写文件)

**Files:**
- Create: `src/worldcup/builder.py`
- Test: `tests/test_builder.py`

- [ ] **Step 1: 写失败测试**

`tests/test_builder.py`:
```python
import json
from pathlib import Path
import jsonschema
from worldcup.parser import html_to_text, parse_team_blocks
from worldcup.builder import build_snapshot, validate_snapshot, write_snapshot

FIXTURE = Path("tests/fixtures/recent_form_sample.html").read_text(encoding="utf-8")
SCHEMA_PATH = "data/recent-form.schema.json"

def _teams():
    return parse_team_blocks(html_to_text(FIXTURE), updated_at="2026-06-24T18:00:00+08:00")

def test_build_snapshot_shape():
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    assert snap["schema_version"] == "1.0"
    assert set(snap["teams"]) == {"瑞士", "加拿大"}
    m0 = snap["teams"]["瑞士"]["recent"][0]
    assert m0["opponent"] == "波黑" and m0["result"] == "W" and m0["score"] == "4-1"
    assert snap["teams"]["瑞士"]["team_id"] is None

def test_build_snapshot_validates_against_schema():
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    validate_snapshot(snap, SCHEMA_PATH)  # 不抛即通过

def test_write_snapshot_roundtrip(tmp_path):
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    out = tmp_path / "recent-form.json"
    write_snapshot(snap, str(out))
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["teams"]["加拿大"]["form"]["w"] == 3
    # 中文不转义
    assert "瑞士" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_builder.py -q`
Expected: FAIL(`ModuleNotFoundError: worldcup.builder`)

- [ ] **Step 3: 写实现**

`src/worldcup/builder.py`:
```python
import json
from pathlib import Path

import jsonschema


def match_to_dict(m):
    return {
        "match_id": m.match_id, "date": m.date, "competition": m.competition,
        "opponent": m.opponent, "is_home": m.is_home, "gf": m.gf, "ga": m.ga,
        "result": m.result, "home": m.home, "away": m.away, "score": m.score,
        "note": m.note,
    }


def team_to_dict(t):
    return {
        "team_id": t.team_id, "name": t.name, "name_en": t.name_en,
        "rank": t.rank, "group": t.group, "form": t.form,
        "updated_at": t.updated_at,
        "recent": [match_to_dict(m) for m in t.recent],
    }


def build_snapshot(teams, generated_at, *, source="qiumiwu", tournament="2026-world-cup"):
    """teams: list[TeamForm] -> spec 顶层快照 dict。键优先用 team_id,缺失则用 name。"""
    return {
        "schema_version": "1.0",
        "source": source,
        "tournament": tournament,
        "generated_at": generated_at,
        "teams": {(t.team_id or t.name): team_to_dict(t) for t in teams},
    }


def validate_snapshot(snapshot, schema_path):
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema.validate(snapshot, schema)


def write_snapshot(snapshot, out_path):
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_builder.py -q`
Expected: PASS(3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/worldcup/builder.py tests/test_builder.py
git commit -m "feat: 快照构建/Schema校验/写文件"
```

---

### Task 7: 抓取层 fetcher.py 与 CLI 编排

**Files:**
- Create: `src/worldcup/fetcher.py`
- Create: `src/worldcup/cli.py`
- Test: `tests/test_fetcher.py`

- [ ] **Step 1: 写失败测试**

`tests/test_fetcher.py`:
```python
import pytest
from worldcup.fetcher import fetch_game_page


class _FakeResp:
    def __init__(self, text, status):
        self.text = text
        self.status_code = status


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.last_url = None
        self.last_headers = None

    def get(self, url, headers=None, timeout=None):
        self.last_url = url
        self.last_headers = headers
        return self._resp


def test_fetch_accepts_404_with_body():
    # 该站会返回 HTTP 404 但正文正常,必须按内容判断成功
    sess = _FakeSession(_FakeResp("...最近战绩 瑞士 进球1/失球0...", 404))
    html = fetch_game_page("107506805271", session=sess)
    assert "最近战绩" in html
    assert sess.last_url.endswith("/game/107506805271")
    assert "User-Agent" in sess.last_headers

def test_fetch_rejects_page_without_records():
    sess = _FakeSession(_FakeResp("<html>error</html>", 200))
    with pytest.raises(RuntimeError):
        fetch_game_page("999", session=sess)
```

- [ ] **Step 2: 运行,确认失败**

Run: `PYTHONPATH=src python -m pytest tests/test_fetcher.py -q`
Expected: FAIL(`ModuleNotFoundError: worldcup.fetcher`)

- [ ] **Step 3: 写 fetcher 实现**

`src/worldcup/fetcher.py`:
```python
import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE = "https://www.qiumiwu.com/game/"


def fetch_game_page(game_id, *, session=None, timeout=20):
    """抓取比赛页 HTML。

    注意:球迷屋会返回 HTTP 404 但正文是正常页面,因此用『正文是否含
    最近战绩』判断成功,而不是 status_code。
    """
    url = f"{BASE}{game_id}"
    sess = session or requests.Session()
    resp = sess.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
    if "最近战绩" not in resp.text:
        raise RuntimeError(
            f"page for {game_id} missing '最近战绩' "
            f"(status={resp.status_code}, len={len(resp.text)})"
        )
    return resp.text
```

- [ ] **Step 4: 运行,确认通过**

Run: `PYTHONPATH=src python -m pytest tests/test_fetcher.py -q`
Expected: PASS(2 passed)

- [ ] **Step 5: 写 CLI(无独立测试,靠端到端手动验证)**

`src/worldcup/cli.py`:
```python
import argparse
from datetime import datetime, timezone, timedelta

from .fetcher import fetch_game_page
from .parser import html_to_text, parse_team_blocks
from .builder import build_snapshot, validate_snapshot, write_snapshot

_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def main(argv=None):
    p = argparse.ArgumentParser(description="抓取世界杯球队近期战绩")
    p.add_argument("game_ids", nargs="+", help="球迷屋比赛 id,可多个")
    p.add_argument("--out", default="data/recent-form.json")
    p.add_argument("--schema", default="data/recent-form.schema.json")
    args = p.parse_args(argv)

    ts = _now_iso()
    by_key = {}
    for gid in args.game_ids:
        text = html_to_text(fetch_game_page(gid))
        for team in parse_team_blocks(text, updated_at=ts):
            by_key[team.team_id or team.name] = team

    snapshot = build_snapshot(list(by_key.values()), generated_at=ts)
    validate_snapshot(snapshot, args.schema)
    write_snapshot(snapshot, args.out)
    print(f"wrote {args.out} with {len(snapshot['teams'])} teams")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 跑全量测试 + 端到端真实抓取**

Run:
```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m worldcup.cli 107506805271 --out data/recent-form.json
```
Expected:
- pytest 全绿(19 passed)
- 打印 `wrote data/recent-form.json with 2 teams`(瑞士、加拿大)
- `data/recent-form.json` 内容符合 schema,瑞士近 10 场 4胜5平1负

- [ ] **Step 7: Commit**

```bash
git add src/worldcup/fetcher.py src/worldcup/cli.py tests/test_fetcher.py
git commit -m "feat: 抓取层与 CLI 编排,端到端打通"
```

---

## 已知限制 / 后续

- 当前 `team_id` 始终为 None(键用中文名);如需稳定 id,后续从来源 schedule 接口采集 teamId。
- 「全部球队」需传入所有比赛的 game id;后续可加一个从赛程页/日历接口枚举 game id 的步骤。
- 点球大战仅 `note` 文本保留,`result` 规则待真实样本出现再细化。
- 反爬/频控:批量抓取时应加 sleep 与缓存(对接项目三级缓存的 L3=本文件)。
