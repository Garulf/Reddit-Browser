import pytest
import requests

from reddit import Reddit, RedditError

LISTING = {"data": {"children": [{"data": {"title": "one"}}, {"data": {"title": "two"}}]}}


class FakeResponse:
    def __init__(self, payload=None, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse(LISTING)
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_hot_requests_front_page_listing():
    session = FakeSession()
    assert Reddit(session).hot() == [{"title": "one"}, {"title": "two"}]
    url, kwargs = session.calls[0]
    assert url == "https://www.reddit.com/hot.json"
    assert kwargs["params"] == {"limit": 15}
    assert kwargs["headers"]["User-Agent"]
    assert kwargs["timeout"] == 10


def test_subreddit_requests_subreddit_listing():
    session = FakeSession()
    Reddit(session).subreddit("Python")
    assert session.calls[0][0] == "https://www.reddit.com/r/Python.json"


def test_listings_are_cached_for_two_minutes():
    session = FakeSession()
    clock = Clock()
    reddit = Reddit(session, clock=clock)
    reddit.hot()
    clock.now += 119
    reddit.hot()
    assert len(session.calls) == 1
    clock.now += 2
    reddit.hot()
    assert len(session.calls) == 2


def test_http_error_carries_status():
    reddit = Reddit(FakeSession(FakeResponse(status=403)))
    with pytest.raises(RedditError) as raised:
        reddit.hot()
    assert raised.value.status == 403
    assert str(raised.value) == "Reddit answered HTTP 403"


def test_errors_are_not_cached():
    session = FakeSession(FakeResponse(status=403))
    reddit = Reddit(session)
    for _ in range(2):
        with pytest.raises(RedditError):
            reddit.hot()
    assert len(session.calls) == 2


def test_connection_error():
    with pytest.raises(RedditError, match="Could not reach Reddit"):
        Reddit(FakeSession(error=requests.ConnectionError("offline"))).hot()


@pytest.mark.parametrize("payload", [None, {}, {"data": {"children": [{}]}}, {"data": None}])
def test_unexpected_response(payload):
    with pytest.raises(RedditError, match="unexpected response"):
        Reddit(FakeSession(FakeResponse(payload))).hot()
