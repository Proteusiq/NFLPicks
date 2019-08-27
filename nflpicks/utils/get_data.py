from collections import defaultdict

from bs4 import BeautifulSoup
from requests import Session
import pandas as pd

USER_AGENT = {'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/39.0.2171.95 Safari/537.36'),
              'Content-Type': 'application/json'}


class GetData:
    '''Get Data from two end_points
        fixture or results
    '''

    BASE_URL = 'https://www.bbc.com/sport/american-football/'

    def __init__(self, end_point='fixtures'):

        self.session = Session()
        self.session.headers.update(USER_AGENT)
        self.end_point = end_point

    def __repr__(self):

        return f'<Get({self.end_point})>'

    @property
    def fetch(self):

        call_url = f'{self.BASE_URL}{self.end_point}'
        self.r = self.session.get(call_url)

        return self

    def scrap_fixture(self):

        assert self.r.ok, 'Broken'

        calls_soup = BeautifulSoup(self.r.content, 'lxml')
        games_soup = calls_soup.find('div', {'id': 'sp-c-filter-contents'})
        games = games_soup.find_all('span', {'class': 'qa-fixture-block'})

        data = defaultdict(list)

        for game in games:
            data['game_date'].append(game.h3.get_text())
            data['game_round'].append(game.h5.get_text())
            data['games'].append([{'home': home['title'], 'away':away['title']}
                                 for home, away in [g.find_all('abbr')
                                 for g in game.find_all('li')]])
            data['time'].append([{'time': time.get_text()}
                                for time in game.find_all(
                'span', class_='sp-c-fixture__number--time')])
            data['venue'].append([{'venue': venue.get_text()}
                                 for venue in game.find_all(
                                'span', class_='sp-c-fixture__venue')
                                ])

        df = pd.DataFrame(data)

        # split data game per rows
        games = df.explode('games')
        time = df.explode('time')
        venue = df.explode('venue')

        games.drop(columns=['time', 'venue'], inplace=True)
        time.drop(columns=['games', 'venue'], inplace=True)
        venue.drop(columns=['time', 'games'], inplace=True)

        games['time'] = time['time'].apply(lambda x: x['time'])
        games['venue'] = venue['venue']

        df = games
        df['game_dt'] = df.apply(
            lambda x: f'{x["game_date"]} {x["time"]}', axis=1
            ).apply(pd.to_datetime)

        df['check_round'] = df['game_round'].str.extract(
                                                '(\d+)').astype(int)

        self.df = df

        return self
