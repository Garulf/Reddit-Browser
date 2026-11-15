import asyncio
from pathlib import Path

import browser
from launcher import KEEP_OPEN


def run_query(text):
    return asyncio.run(browser.query(text))


def titles(results):
    return [result.title for result in results]


def test_empty_query_lists_front_page_posts_in_order(fake_reddit):
    results = run_query("")
    assert fake_reddit.calls == [("hot",)]
    assert titles(results) == [
        "Flow Launcher 2.0 is out",
        "What plugins do you use every day?",
        "Python 3.14 released",
    ]


def test_query_filters_front_page_by_title(fake_reddit):
    assert titles(run_query("PYTHON")) == ["Python 3.14 released"]


def test_post_result_opens_permalink_and_carries_context(fake_reddit):
    result = run_query("released")[0]
    assert result.json_rpc_action["Method"] == "Flow.Launcher.OpenUrl"
    assert result.json_rpc_action["Parameters"][0] == "https://www.reddit.com/r/Python/comments/ghi789/python_314_released/"
    assert result.context_data == ["Python", "/r/Python/comments/ghi789/python_314_released/"]
    assert result.subtitle == "🡅2048 • 🡇0 - r/Python "


def test_post_subtitle_flattens_selftext(fake_reddit):
    assert run_query("2.0")[0].subtitle == "🡅512 • 🡇0 - r/flowlauncher Release notes are on GitHub"


def test_posts_without_permalink_are_skipped(settings, monkeypatch):
    from conftest import FakeReddit

    monkeypatch.setattr(browser, "reddit", FakeReddit(posts=[{"title": "broken"}, {"title": "ok", "permalink": "/r/a/1/"}]))
    assert titles(run_query("")) == ["ok"]


def test_slash_lists_favorites_that_change_the_query(fake_reddit):
    results = run_query("/")
    assert fake_reddit.calls == []
    assert titles(results) == ["r/flowlauncher", "r/Python"]
    assert results[0].json_rpc_action == {
        "Method": "change_query",
        "Parameters": ["r /flowlauncher"],
        "DontHideAfterAction": False,
    }
    assert results[0].auto_complete_text == "r /flowlauncher"
    assert results[0].context_data == ["flowlauncher", "/r/flowlauncher/"]


def test_favorites_query_without_keyword(fake_reddit):
    browser.plugin.launcher.action_keyword = ""
    assert run_query("/")[0].json_rpc_action["Parameters"] == ["/flowlauncher"]


def test_no_favorites_saved(fake_reddit):
    browser.plugin.launcher._settings = {}
    assert run_query("/") == []


def test_subreddit_query_fetches_that_subreddit(fake_reddit):
    results = run_query("/flowlauncher")
    assert fake_reddit.calls == [("subreddit", "flowlauncher")]
    assert len(results) == 3


def test_subreddit_query_filters_by_search(fake_reddit):
    assert titles(run_query("/flowlauncher plugins")) == ["What plugins do you use every day?"]


def test_subreddit_query_filters_by_the_whole_search(fake_reddit):
    assert titles(run_query("/flowlauncher plugins do you")) == ["What plugins do you use every day?"]
    assert titles(run_query("/flowlauncher 2.0 plugins")) == []


def test_blocked_request_shows_error_result_instead_of_crashing(blocked_reddit):
    results = run_query("")
    assert len(results) == 1
    assert results[0].title == "Reddit blocked the request"
    assert "HTTP 403" in results[0].subtitle
    assert results[0].json_rpc_action["Method"] == "Flow.Launcher.OpenUrl"
    assert results[0].json_rpc_action["Parameters"][0] == "https://www.reddit.com"


def test_subreddit_error_opens_that_subreddit(settings, monkeypatch):
    from conftest import FakeReddit
    from reddit import RedditError

    monkeypatch.setattr(browser, "reddit", FakeReddit(error=RedditError("Could not reach Reddit")))
    (result,) = run_query("/Python")
    assert result.title == "Could not load Reddit"
    assert result.subtitle.startswith("Could not reach Reddit.")
    assert result.json_rpc_action["Parameters"][0] == "https://www.reddit.com/r/Python/"


def test_context_menu_adds_favorite(settings):
    results = browser.context_menu(["rust", "/r/rust/comments/1/x/"])
    assert titles(results) == ["Open in Browser", "Add subreddit to favorites"]
    assert results[0].json_rpc_action["Parameters"][0] == "https://www.reddit.com/r/rust/comments/1/x/"
    assert results[1].settings_change == {"favorites": ["flowlauncher", "Python", "rust"]}
    assert results[1].json_rpc_action["Method"] == "Flow.Launcher.ShowMsg"
    assert results[1].to_json()["SettingsChange"] == {"favorites": ["flowlauncher", "Python", "rust"]}


def test_context_menu_removes_favorite(settings):
    results = browser.context_menu(["Python", "/r/Python/"])
    assert titles(results) == ["Open in Browser", "Remove from Favorites"]
    assert results[1].settings_change == {"favorites": ["flowlauncher"]}


def test_context_menu_ignores_unknown_data(settings):
    assert browser.context_menu(None) == []
    assert browser.context_menu(["only-one"]) == []


def test_change_query_keeps_window_open(monkeypatch):
    sent = []

    async def invoke(command):
        sent.append(command)

    monkeypatch.setattr(browser.plugin.launcher.api, "invoke", invoke)
    assert asyncio.run(browser.change_query("r /Python")) == KEEP_OPEN
    assert sent == [{"Method": "Flow.Launcher.ChangeQuery", "Parameters": ["r /Python", False]}]


def test_results_always_send_a_preview(fake_reddit):
    data = run_query("released")[0].to_json()
    assert data["Preview"] == {"PreviewImagePath": None, "Description": "🡅2048 • 🡇0 - r/Python ", "IsMedia": False}
    assert "SettingsChange" not in data


def test_icons_exist_in_flow_launcher(fake_reddit, monkeypatch):
    from pyflowlauncher.icons import Icons

    monkeypatch.setattr(browser.plugin.launcher, "icons", Icons(Path("C:/FlowLauncher")))
    shipped = {"Browser.png", "cancel.png", "app_error.png"}
    favorite_icons = [result.icon for result in run_query("/")]
    menu_icons = [result.icon for result in browser.context_menu(["rust", "/r/rust/"])]
    menu_icons += [result.icon for result in browser.context_menu(["Python", "/r/Python/"])]
    for icon in favorite_icons + menu_icons:
        assert icon == browser.ICON or Path(icon).name in shipped
