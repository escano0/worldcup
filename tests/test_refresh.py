import worldcup.refresh as refresh


def test_refresh_runs_all_steps_in_order(monkeypatch):
    calls = []
    monkeypatch.setattr(refresh.cli, "main", lambda argv: calls.append(("teams", argv)))
    monkeypatch.setattr(refresh.tournament, "main", lambda argv: calls.append(("tournament", argv)))
    monkeypatch.setattr(refresh.squad, "main", lambda argv: calls.append(("squad", argv)))
    monkeypatch.setattr(refresh.odds, "main", lambda argv: calls.append(("odds", argv)))
    monkeypatch.setattr(refresh.profile, "main", lambda argv: calls.append(("profile", argv)))
    refresh.main([])
    names = [c[0] for c in calls]
    assert names == ["teams", "tournament", "squad", "odds", "profile"]


def test_refresh_skip_flags(monkeypatch):
    calls = []
    for mod in ("cli", "tournament", "squad", "odds", "profile"):
        monkeypatch.setattr(getattr(refresh, mod), "main",
                            lambda argv, _m=mod: calls.append(_m))
    refresh.main(["--skip-odds", "--skip-profiles"])
    assert "odds" not in calls and "profile" not in calls
    assert "cli" in calls and "tournament" in calls and "squad" in calls


def test_refresh_continues_after_step_error(monkeypatch):
    calls = []
    def boom(argv): raise RuntimeError("net down")
    monkeypatch.setattr(refresh.cli, "main", boom)
    monkeypatch.setattr(refresh.tournament, "main", lambda argv: calls.append("tournament"))
    monkeypatch.setattr(refresh.squad, "main", lambda argv: calls.append("squad"))
    monkeypatch.setattr(refresh.odds, "main", lambda argv: calls.append("odds"))
    monkeypatch.setattr(refresh.profile, "main", lambda argv: calls.append("profile"))
    refresh.main([])  # must NOT raise even though teams step failed
    assert calls == ["tournament", "squad", "odds", "profile"]
