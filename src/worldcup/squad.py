import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .fetcher import DEFAULT_UA, fetch_game_page
from .parser import html_to_text
from .schedule import fetch_schedule_html, parse_game_ids
from .tournament import parse_standings

_COACH_RE = re.compile(r"主教练\s+(\S+)")
_SQUAD_UPDATED_RE = re.compile(r"最新阵容\s+([\d/]{6,}\s+[\d:]+)\s*更新")
_POS_RE = re.compile(r"(\S+?)\s+(守门员|后卫|中场|前锋)\s+(\d+)号")
_DETAIL_RE = re.compile(
    r"([\d.]+(?:万|亿)欧元|-)\s+(\d+cm|-)\s+(\d+kg|-)\s+(左脚|右脚|双脚|-)\s+"
    r"(\d{4}-\d{2}-\d{2}|-)\s+(\d+|-)\s+([^\s\d-]\S*|-)"
)

_POSITIONS = ["守门员", "后卫", "中场", "前锋"]


def _none_if_dash(v):
    return None if v == "-" else v


def parse_roster(html):
    """解析球队阵容页:主教练 + 按位置分组的球员(含身价等详情)。"""
    text = html_to_text(html)
    coach_m = _COACH_RE.search(text)
    upd_m = _SQUAD_UPDATED_RE.search(text)

    s = text.find("最新阵容")
    h = text.find("身价 身高", s if s >= 0 else 0)
    poslist = text[s:h] if (s >= 0 and h >= 0) else text
    detail = text[h:] if h >= 0 else ""

    players = _POS_RE.findall(poslist)
    rows = _DETAIL_RE.findall(detail)

    squad = {p: [] for p in _POSITIONS}
    for i, (name, pos, num) in enumerate(players):
        v, ht, wt, ft, db, ag, nat = rows[i] if i < len(rows) else ("-",) * 7
        squad.setdefault(pos, []).append({
            "name": name, "position": pos, "number": int(num),
            "market_value": _none_if_dash(v),
            "height": _none_if_dash(ht), "weight": _none_if_dash(wt),
            "foot": _none_if_dash(ft), "dob": _none_if_dash(db),
            "age": int(ag) if ag != "-" else None,
            "nationality": _none_if_dash(nat),
        })

    return {
        "coach": coach_m.group(1) if coach_m else None,
        "squad_updated": upd_m.group(1) if upd_m else None,
        "player_count": len(players),
        "squad": squad,
    }


_INJ_TEAM_RE = re.compile(r"(\S+?)\s+原因\s+状态\s+时间\s+")
_INJ_PLAYER_RE = re.compile(
    r"(\S+?)\s+(守门员|后卫|中场|前锋)\s+(\d+)号\s+(\S+?)\s+(\S+?)\s+(\d{2}-\d{2})"
)


def parse_injuries(html):
    """解析比赛页伤停球员 -> {队名: [ {name,position,number,reason,status,date} ]}。"""
    text = html_to_text(html)
    i = text.find("伤停球员")
    if i < 0:
        return {}
    seg = text[i + len("伤停球员"):]
    end = seg.find("最佳球员")
    if end >= 0:
        seg = seg[:end]

    result = {}
    headers = list(_INJ_TEAM_RE.finditer(seg))
    for idx, hm in enumerate(headers):
        team = hm.group(1)
        start = hm.end()
        stop = headers[idx + 1].start() if idx + 1 < len(headers) else len(seg)
        block = seg[start:stop]
        players = []
        for m in _INJ_PLAYER_RE.finditer(block):
            name, pos, num, reason, status, date = m.groups()
            players.append({
                "name": name, "position": pos, "number": int(num),
                "reason": reason, "status": status, "date": date,
            })
        result[team] = players
    return result


_ROSTER_URL = "https://www.qiumiwu.com/team/{slug}/roster"
_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def fetch_team_roster(slug, *, session=None, timeout=20):
    """抓取球队阵容页;按正文是否含『主教练/最新阵容』判断成功(站点 404 但有正文)。"""
    sess = session or requests.Session()
    resp = sess.get(_ROSTER_URL.format(slug=slug),
                    headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
    if "主教练" not in resp.text and "最新阵容" not in resp.text:
        raise RuntimeError(
            f"roster page for {slug} missing squad (status={resp.status_code})"
        )
    return resp.text


def build_squad_doc(slug, name, group, roster, injuries, generated_at):
    """组装单队阵容文档。formation 源头无,固定 None(按位置分组的 squad 即部署框架)。"""
    return {
        "team_id": slug, "name": name, "group": group,
        "coach": roster.get("coach"),
        "squad_updated": roster.get("squad_updated"),
        "formation": None,
        "player_count": roster.get("player_count", 0),
        "squad": roster.get("squad", {}),
        "injuries": injuries,
        "generated_at": generated_at,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="抓取各队阵容/身价/伤停 -> docs/squads/{slug}.json")
    p.add_argument("--docs-dir", default="docs/squads")
    p.add_argument("--delay", type=float, default=0.4, help="每次抓取间隔秒")
    p.add_argument("--no-injuries", action="store_true", help="跳过伤停(省去比赛页抓取)")
    args = p.parse_args(argv)

    ts = _now_iso()
    sched_html = fetch_schedule_html()
    game_ids = parse_game_ids(sched_html)
    if not game_ids:
        raise SystemExit("赛程页未找到 game id")

    # 全部 48 队 (slug, 队名, 组)
    groups = parse_standings(fetch_game_page(game_ids[0]))
    teams = [(t["slug"], t["team"], g["group"]) for g in groups for t in g["standings"]]

    # 伤停:逐个比赛页解析,按队名归并(首次出现为准)
    injuries_by_team = {}
    if not args.no_injuries:
        for gid in game_ids:
            try:
                for tname, players in parse_injuries(fetch_game_page(gid)).items():
                    injuries_by_team.setdefault(tname, players)
            except Exception as e:
                print(f"skip injuries {gid}: {e}")
            time.sleep(args.delay)

    out_dir = Path(args.docs_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written, failed = 0, []
    for slug, name, group in teams:
        try:
            roster = parse_roster(fetch_team_roster(slug))
            doc = build_squad_doc(slug, name, group, roster,
                                  injuries_by_team.get(name, []), ts)
            (out_dir / f"{slug}.json").write_text(
                json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1
        except Exception as e:
            failed.append(slug)
            print(f"skip {slug}: {e}")
        time.sleep(args.delay)

    msg = f"wrote {written} squad files to {args.docs_dir} ({len(teams)} teams)"
    if failed:
        msg += f" ({len(failed)} failed)"
    print(msg)
    if teams and len(failed) == len(teams):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
