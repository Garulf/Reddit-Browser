import requests

HOT_REDDIT = 'https://www.reddit.com/hot.json'

class Reddit(object):

    def __init__(self) -> None:
        pass

    def request(self, end_point, params, method='GET'):
        url = f'https://www.reddit.com/{end_point}'
        headers = {'User-Agent': 'Flow Launcher/0.0.1'}
        response = requests.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def hot(self):
        return self.request('hot.json', {'limit': 15})

    def subreddit(self, subreddit):
        return self.request(f'r/{subreddit}.json', {'limit': 15})
        