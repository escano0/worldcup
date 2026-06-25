from worldcup.squad import parse_roster, parse_injuries

ROSTER_HTML = (
    "<div>资料 数据 阵容 主教练 安切洛蒂 主场 - 成立 1914 "
    "最新阵容 2026/6/10 11:05更新 球员 "
    "维尼修斯 前锋 7号 阿利森 守门员 1号 卡塞米罗 中场 5号 "
    "马尔基尼奥斯 后卫 4号 内马尔 前锋 10号 "
    "身价 身高 体重 惯用脚 出生日期 年龄 国籍 "
    "1.4亿欧元 176cm 73kg 右脚 2000-07-12 25 巴西 "
    "1500万欧元 191cm 91kg 右脚 1992-10-02 33 巴西 "
    "600万欧元 185cm 84kg 右脚 1992-02-23 34 巴西 "
    "2800万欧元 183cm 76kg 右脚 1994-05-14 32 巴西 "
    "- - - - - - - 赛季数据</div>"
)

INJ_HTML = (
    "<div>... 交战历史 伤停球员 瑞士 原因 状态 时间 "
    "穆海姆 后卫 28号 小腿肌肉拉伤 受伤 06-19 "
    "加拿大 原因 状态 时间 琼斯 后卫 5号 肌肉挫伤 受伤 06-18 "
    "科内 中场 90号 小腿骨折 受伤 06-19 最佳球员 曼赞比 中场 9号 2</div>"
)


def test_parse_roster_coach_and_updated():
    r = parse_roster(ROSTER_HTML)
    assert r["coach"] == "安切洛蒂"
    assert r["squad_updated"] == "2026/6/10 11:05"
    assert r["player_count"] == 5


def test_parse_roster_squad_grouped_by_position_with_details():
    r = parse_roster(ROSTER_HTML)
    sq = r["squad"]
    assert [p["name"] for p in sq["前锋"]] == ["维尼修斯", "内马尔"]
    assert [p["name"] for p in sq["守门员"]] == ["阿利森"]
    vini = sq["前锋"][0]
    assert vini == {
        "name": "维尼修斯", "position": "前锋", "number": 7,
        "market_value": "1.4亿欧元", "height": "176cm", "weight": "73kg",
        "foot": "右脚", "dob": "2000-07-12", "age": 25, "nationality": "巴西",
    }
    # last squad player has the all-dash detail row -> nulls
    neymar = sq["前锋"][1]
    assert neymar["number"] == 10 and neymar["market_value"] is None
    assert neymar["age"] is None and neymar["height"] is None


def test_parse_injuries_by_team():
    inj = parse_injuries(INJ_HTML)
    assert set(inj) == {"瑞士", "加拿大"}
    assert inj["瑞士"] == [{"name": "穆海姆", "position": "后卫", "number": 28,
                            "reason": "小腿肌肉拉伤", "status": "受伤", "date": "06-19"}]
    assert [p["name"] for p in inj["加拿大"]] == ["琼斯", "科内"]
    assert inj["加拿大"][1]["number"] == 90


def test_parse_injuries_handles_none():
    html = "<div>伤停球员 法国 原因 状态 时间 暂无数据 最佳球员 x</div>"
    assert parse_injuries(html) == {"法国": []}


def test_build_squad_doc_assembles():
    from worldcup.squad import build_squad_doc, parse_roster
    roster = parse_roster(ROSTER_HTML)
    injuries = [{"name": "穆海姆", "position": "后卫", "number": 28,
                 "reason": "拉伤", "status": "受伤", "date": "06-19"}]
    doc = build_squad_doc("baxi1", "巴西", "C", roster, injuries, "2026-06-25T12:00:00+08:00")
    assert doc["team_id"] == "baxi1" and doc["name"] == "巴西" and doc["group"] == "C"
    assert doc["coach"] == "安切洛蒂"
    assert doc["formation"] is None              # 源头无阵型
    assert doc["player_count"] == 5
    assert doc["squad"]["前锋"][0]["name"] == "维尼修斯"
    assert doc["injuries"] == injuries
    assert doc["generated_at"] == "2026-06-25T12:00:00+08:00"
    assert doc["squad_updated"] == "2026/6/10 11:05"


def test_fetch_team_roster_judges_by_content():
    import worldcup.squad as S

    class _Resp:
        def __init__(self, text, status): self.text = text; self.status_code = status
    class _Sess:
        def __init__(self, resp): self._r = resp; self.last_url = None; self.last_headers = None
        def get(self, url, headers=None, timeout=None):
            self.last_url = url; self.last_headers = headers; return self._r

    ok = _Sess(_Resp("...主教练 X 最新阵容...", 404))
    html = S.fetch_team_roster("baxi1", session=ok)
    assert "主教练" in html
    assert ok.last_url == "https://www.qiumiwu.com/team/baxi1/roster"
    assert "User-Agent" in ok.last_headers

    bad = _Sess(_Resp("<html>nope</html>", 200))
    import pytest
    with pytest.raises(RuntimeError):
        S.fetch_team_roster("x", session=bad)
