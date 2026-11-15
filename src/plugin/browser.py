from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from pyflowlauncher import Plugin, Result, api
from pyflowlauncher.models.result import PreviewInfo

from launcher import KEEP_OPEN, RedditLauncher
from reddit import BASE_URL, Reddit, RedditError

PLUGIN_DIR = Path(__file__).resolve().parent
ICON = str(PLUGIN_DIR.parent / "icon.png")
BLOCKED_STATUSES = {403, 429}

plugin = Plugin(launcher=RedditLauncher())
reddit = Reddit()


@dataclass
class RedditResult(Result):
    settings_change: Optional[dict] = None

    def to_json(self):
        result = super().to_json()
        # pyflowlauncher 1.2.2 sends "Preview": null, which crashes Flow
        # Launcher's preview panel (Garulf/pyFlowLauncher#44).
        if result.get("Preview") is None:
            result["Preview"] = PreviewInfo(PreviewImagePath=None, Description=self.subtitle or "", IsMedia=False)
        # Flow Launcher saves these settings when the result is selected.
        if self.settings_change:
            result["SettingsChange"] = self.settings_change
        return result


def icon(name: str) -> str:
    return getattr(plugin.launcher.icons, name) or ICON


def favorites() -> List[str]:
    return list(plugin.settings.get("favorites") or [])


def full_query(text: str) -> str:
    keyword = plugin.launcher.action_keyword
    return f"{keyword} {text}" if keyword else text


def parse_query(query: str):
    """Split a query into (subreddit, search). subreddit is None for the front page."""
    if not query.startswith("/"):
        return None, query
    name, _, search = query[1:].partition(" ")
    return name, search.strip()


async def fetch_posts(subreddit: Optional[str]) -> List[dict]:
    loop = asyncio.get_running_loop()
    if subreddit:
        return await loop.run_in_executor(None, reddit.subreddit, subreddit)
    return await loop.run_in_executor(None, reddit.hot)


def post_subtitle(post: dict) -> str:
    return "🡅{ups} • 🡇{downs} - {subreddit} {selftext}".format(
        ups=post.get("ups", "N/A"),
        downs=post.get("downs", "N/A"),
        subreddit=post.get("subreddit_name_prefixed", ""),
        selftext=(post.get("selftext") or "").replace("\n", " "),
    )


def post_results(posts: Iterable[dict], search: str) -> List[RedditResult]:
    results = []
    for post in posts:
        title = post.get("title") or ""
        permalink = post.get("permalink")
        if not permalink or search.lower() not in title.lower():
            continue
        results.append(RedditResult(
            title=title,
            subtitle=post_subtitle(post),
            icon=ICON,
            context_data=[post.get("subreddit", ""), permalink],
        ).add_action(api.open_url(BASE_URL + permalink)))
    return results


def favorite_results() -> List[RedditResult]:
    results = []
    for name in favorites():
        subreddit_query = full_query(f"/{name}")
        results.append(RedditResult(
            title=f"r/{name}",
            subtitle="Browse subreddit",
            icon=icon("bookmark"),
            context_data=[name, f"/r/{name}/"],
            auto_complete_text=subreddit_query,
        ).add_action(change_query, [subreddit_query]))
    return results


def error_result(error: RedditError, subreddit: Optional[str]) -> RedditResult:
    url = f"{BASE_URL}/r/{subreddit}/" if subreddit else BASE_URL
    if error.status in BLOCKED_STATUSES:
        title = "Reddit blocked the request"
        reason = f"HTTP {error.status}. Reddit is refusing requests from this plugin"
    else:
        title = "Could not load Reddit"
        reason = str(error)
    return RedditResult(
        title=title,
        subtitle=f"{reason}. Press Enter to open Reddit in your browser.",
        icon=icon("app_error"),
    ).add_action(api.open_url(url))


@plugin.on_method
async def query(query: str):
    if query == "/":
        return favorite_results()
    subreddit, search = parse_query(query)
    try:
        posts = await fetch_posts(subreddit)
    except RedditError as error:
        return [error_result(error, subreddit)]
    return post_results(posts, search)


@plugin.on_method
def context_menu(data):
    if not isinstance(data, list) or len(data) != 2:
        return []
    subreddit, permalink = data
    results = [
        RedditResult(title="Open in Browser", icon=icon("browser")).add_action(api.open_url(BASE_URL + permalink)),
    ]
    if not subreddit:
        return results
    current = favorites()
    if subreddit in current:
        results.append(RedditResult(
            title="Remove from Favorites",
            icon=icon("cancel"),
            settings_change={"favorites": [name for name in current if name != subreddit]},
        ).add_action(api.show_msg("Favorite Removed", f"{subreddit} removed from your favorites.", ICON)))
    else:
        results.append(RedditResult(
            title="Add subreddit to favorites",
            icon=icon("bookmark"),
            settings_change={"favorites": current + [subreddit]},
        ).add_action(api.show_msg("Favorite Added", f"{subreddit} added to your favorites.", ICON)))
    return results


@plugin.on_method
async def change_query(text: str):
    await plugin.launcher.api.invoke(api.change_query(text))
    return KEEP_OPEN
