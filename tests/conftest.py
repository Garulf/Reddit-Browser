import pytest

import browser
from reddit import RedditError

POSTS = [
    {
        "title": "Flow Launcher 2.0 is out",
        "permalink": "/r/flowlauncher/comments/abc123/flow_launcher_20_is_out/",
        "subreddit": "flowlauncher",
        "subreddit_name_prefixed": "r/flowlauncher",
        "ups": 512,
        "downs": 0,
        "selftext": "Release notes\nare on GitHub",
    },
    {
        "title": "What plugins do you use every day?",
        "permalink": "/r/flowlauncher/comments/def456/what_plugins_do_you_use_every_day/",
        "subreddit": "flowlauncher",
        "subreddit_name_prefixed": "r/flowlauncher",
        "ups": 88,
        "downs": 0,
        "selftext": "",
    },
    {
        "title": "Python 3.14 released",
        "permalink": "/r/Python/comments/ghi789/python_314_released/",
        "subreddit": "Python",
        "subreddit_name_prefixed": "r/Python",
        "ups": 2048,
        "downs": 0,
        "selftext": "",
    },
]


class FakeReddit:
    def __init__(self, posts=None, error=None):
        self.posts = POSTS if posts is None else posts
        self.error = error
        self.calls = []

    def _listing(self, call):
        self.calls.append(call)
        if self.error:
            raise self.error
        return self.posts

    def hot(self):
        return self._listing(("hot",))

    def subreddit(self, name):
        return self._listing(("subreddit", name))


@pytest.fixture
def settings():
    launcher = browser.plugin.launcher
    launcher._settings = {"favorites": ["flowlauncher", "Python"]}
    launcher.action_keyword = "r"
    yield launcher._settings
    launcher._settings = {}
    launcher.action_keyword = ""


@pytest.fixture
def fake_reddit(settings, monkeypatch):
    fake = FakeReddit()
    monkeypatch.setattr(browser, "reddit", fake)
    return fake


@pytest.fixture
def blocked_reddit(settings, monkeypatch):
    fake = FakeReddit(error=RedditError("Reddit answered HTTP 403", 403))
    monkeypatch.setattr(browser, "reddit", fake)
    return fake
