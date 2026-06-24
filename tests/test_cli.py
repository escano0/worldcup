import pytest
import worldcup.cli as cli


def test_all_games_failing_exits_nonzero(monkeypatch, tmp_path):
    def boom(gid, **kwargs):
        raise RuntimeError("no 最近战绩")
    monkeypatch.setattr(cli, "fetch_game_page", boom)
    with pytest.raises(SystemExit) as ei:
        cli.main([
            "111", "222",
            "--out", str(tmp_path / "o.json"),
            "--schema", "data/recent-form.schema.json",
            "--delay", "0",
        ])
    assert ei.value.code == 1


def test_partial_failure_does_not_exit_nonzero(monkeypatch, tmp_path):
    # one game yields a team, the other fails -> should NOT raise SystemExit
    from worldcup.models import TeamForm

    def half(gid, **kwargs):
        if gid == "ok":
            return "<html>ok</html>"
        raise RuntimeError("no form")

    def fake_slugs(html):
        return {"瑞士": "ruishi"}

    def fake_blocks(text, updated_at):
        return [TeamForm(name="瑞士", team_id=None,
                         form={"played":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"win_rate":0.0},
                         recent=[], updated_at=updated_at)]

    monkeypatch.setattr(cli, "fetch_game_page", half)
    monkeypatch.setattr(cli, "parse_team_slugs", fake_slugs)
    monkeypatch.setattr(cli, "parse_team_blocks", fake_blocks)
    monkeypatch.setattr(cli, "html_to_text", lambda h: h)
    cli.main([
        "ok", "bad",
        "--out", str(tmp_path / "o.json"),
        "--schema", "data/recent-form.schema.json",
        "--delay", "0",
    ])  # returns normally, no SystemExit
