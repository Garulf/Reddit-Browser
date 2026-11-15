from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple

import requests

BASE_URL = "https://www.reddit.com"
USER_AGENT = "Flow Launcher/0.0.1"
LIMIT = 15
CACHE_SECONDS = 120


class RedditError(Exception):
    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


class Reddit:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 10,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._clock = clock
        self._cache: Dict[str, Tuple[float, List[dict]]] = {}

    def hot(self) -> List[dict]:
        return self.listing("hot.json")

    def subreddit(self, name: str) -> List[dict]:
        return self.listing(f"r/{name}.json")

    def listing(self, path: str) -> List[dict]:
        cached = self._cache.get(path)
        if cached and self._clock() - cached[0] < CACHE_SECONDS:
            return cached[1]
        posts = self._fetch(path)
        self._cache[path] = (self._clock(), posts)
        return posts

    def _fetch(self, path: str) -> List[dict]:
        try:
            response = self._session.get(
                f"{BASE_URL}/{path}",
                headers={"User-Agent": USER_AGENT},
                params={"limit": LIMIT},
                timeout=self._timeout,
            )
            response.raise_for_status()
            children = response.json()["data"]["children"]
            return [child["data"] for child in children]
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            raise RedditError(f"Reddit answered HTTP {status}", status) from error
        except requests.RequestException as error:
            raise RedditError("Could not reach Reddit") from error
        except (ValueError, KeyError, TypeError) as error:
            raise RedditError("Reddit sent an unexpected response") from error
