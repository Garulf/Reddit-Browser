import webbrowser
import json

from flox import Flox, utils, ICON_HISTORY, APP_ICONS, ICON_BROWSER, ICON_CANCEL
from reddit import Reddit
from requests.exceptions import HTTPError

CACHE_NAME = 'reddit.json'

# @utils.cache(CACHE_NAME, max_age=120)
def get_reddit_posts(reddit, attr):
    return getattr(reddit, attr)()

class RedditBrowser(Flox):

    def query(self, query):
        reddit = Reddit()
        if query.startswith('/'):
            if len(query) == 1:
                history = self.settings.get('favorites', [])
                for item in history:
                    self.add_item(
                        title=f'r/{item}',
                        subtitle='Browse subreddit',
                        icon=f'{APP_ICONS}/bookmark.png',
                        context=[item, ''],
                        method=self.change_query,
                        parameters=[f'{self.user_keyword} /{item}'.replace('* ', '')],
                        dont_hide=True
                    )
                return
            try:
                subreddit_name = query.split(' ')[0][1:]
                subreddit = utils.cache(f'{subreddit_name}.json', max_age=120)(reddit.subreddit)(query.split(' ')[0][1:])
            except (HTTPError):
                return
            if ' ' in query:
                query = query.split(' ')[-1].replace(' ', '').strip()
            else:
                query = ''
        else:
            subreddit = utils.cache(CACHE_NAME, max_age=120)(reddit.hot)()
        for post in subreddit['data']['children']:
            if query.lower() in post['data']['title'].lower():
                try:
                    subtitle = '🡅{ups} • 🡇{downs} - {subreddit} {selftext}'.format(
                        ups=post['data'].get('ups', 'N/A'),
                        downs=post['data'].get('downs', 'N/A'),
                        subreddit=post['data']['subreddit_name_prefixed'],
                        selftext=post['data'].get('selftext', '').replace('\n', ' ')
                    )
                    self.add_item(
                        title=post['data']['title'],
                        subtitle=subtitle,
                        method=self.open_url,
                        parameters=[post['data']['permalink']],
                        context=[post['data']['subreddit'], post['data']['permalink']]
                    )
                except KeyError:
                    return

    def context_menu(self, data):
        subreddit, url = data
        self.add_item(
            title='Open in Browser',
            icon=ICON_BROWSER,
            method=self.open_url,
            parameters=[url]
        )
        if subreddit in self.settings['favorites']:
            self.add_item(
                title='Remove from Favorites',
                icon=ICON_CANCEL,
                method=self.remove_favorite,
                parameters=[subreddit]
            )
        else:
            self.add_item(
                title='Add subreddit to favorites',
                icon=f'{APP_ICONS}/bookmark.png',
                method=self.add_favorite,
                parameters=[subreddit]
            )

    def open_url(self, end_point):
        url = f'https://www.reddit.com{end_point}'
        webbrowser.open(url)

    def add_favorite(self, subreddit):
        favorites = self.settings.setdefault("favorites", [])
        favorites.append(subreddit)
        self.settings.update({"favorites": favorites})
        self.show_msg(
            "Favorite Added", f"{subreddit} added to your favorites."
        )

    def remove_favorite(self, subreddit):
        favorites = self.settings.setdefault("favorites", [])
        favorites.remove(subreddit)
        self.settings.update({"favorites": favorites})
        self.show_msg(
            "Favorite Removed", f"{subreddit} removed from your favorites."
        )

if __name__ == "__main__":
    RedditBrowser()
