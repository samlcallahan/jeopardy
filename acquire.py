import pandas as pd
from bs4 import BeautifulSoup
from requests import get, Session
import wikipedia as wiki
import pyarrow.feather as feather
import os
import sys
from env import user
from time import time
import concurrent.futures
import threading

HEADERS = {'User-Agent': user}

URL = "https://j-archive.com/"

thread_local = threading.local()

def get_session():
    '''
    if the current thread doesn't have a requests Session object, creates one and updates the headers
    '''

    if not hasattr(thread_local, "session"):
        thread_local.session = Session()
        thread_local.session.headers.update(HEADERS)
    return thread_local.session

def season_urls():
    '''
    gets the urls for all seasons of jeopardy from the above website
    '''

    url_suffix = "listseasons.php"

    # gets html from website index
    response = get(URL + url_suffix, headers=HEADERS)

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # picks out all season elements
    seasons_html = soup.find_all('tr')
    seasons = []

    # takes season URLs out of html chunks
    for season in seasons_html:
        seasons.append(season.find('a').get('href'))
    return seasons

def episode_urls(season_url):
    '''
    gets URLs for all episodes in a given season
    '''

    session = get_session()

    # gets html of season index
    response = session.get(URL + season_url)

    # picks out episode elements
    soup = BeautifulSoup(response.content, 'html.parser')
    episodes_html = soup.find_all('tr')

    # takes episode URLs out of html chunks
    episodes = []
    for episode in episodes_html:
        episodes.append(episode.find('a').get('href'))
    return episodes

def decode_category(code, categories):
    '''
    given a clue code and an episode's full list of categories, returns the clue's category name
    clue codes are of the format [J/DJ]_[category_number]_[question_number] or FJ
    most episodes have 13 categories (6 jeopardy, 6 double jeopardy, 1 final jeopardy), but some have only 7 (6 double jeopardy, 1 final jeopardy)
    '''

    if code[0] == 'J':
        index = int(code[-3]) - 1
        return categories[index]
    elif code[0] == 'D':
        index = int(code[-3]) - 8
        return categories[index]
    else:
        return categories[-1]

def episode_category_list(episode_soup):
    '''
    gets a list of all clue categories out of a given episode's html soup
    '''

    # finds all html chunks with the category_name class
    soups = episode_soup.find_all('td', class_="category_name")

    # goes through each td chunk and finds the category name in it. Sometimes it's split into multiple html elements.
    category_list = []
    for i in soups:
        if i.get_text() is not None:
            category_list.append(i.get_text())
        else:
            category = ''
            for element in i.contents:
                if element.get_text() is not None:
                    category += element.get_text()
            category_list.append(category)

    return category_list

def episode_clue_data(episode_soup, category_list, debug):
    '''
    returns a list of all clues and their categories in an episode, given the episode page's soup
    '''

    clues = []
    categories = []
    values = []

    for spoonful in episode_soup.find_all(class_='clue_text'):
        if spoonful.get_text() == '\n':
            continue
        clues.append(spoonful.get_text())

        clue_code = spoonful['id'][5:]

        category = decode_category(clue_code, category_list)
        categories.append(category)

    for spoonful in episode_soup.find_all(class_='clue'):
        if spoonful.find(class_='clue_value'):
            values.append(spoonful.find(class_='clue_value').get_text())
        elif spoonful.find(class_='clue_value_daily_double'):
            values.append(spoonful.find(class_='clue_value_daily_double').get_text())

    values.append(None)
    return clues, categories, values
    
def episode_answers(episode_soup):
    '''
    returns a list of correct answers in an episode given the episode page's soup
    '''
    answers = []
    spoonfuls = []

    for tag in episode_soup.find_all('div', onmouseover=True): 
        spoonfuls.append(tag['onmouseover']) 

    for soup_string in spoonfuls:
        answer_soup = BeautifulSoup(soup_string, 'html.parser')
        answers.append(answer_soup.find('em').get_text())
    return answers

def episode_data(episode_url, debug=True):
    '''
    given an episode's url returns a tuple of lists of the categories, clues, and correct answers in an episode
    '''

    session = get_session()
    response = session.get(episode_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    category_list = episode_category_list(soup)

    clues, categories, values = episode_clue_data(soup, category_list, debug)
    correct_responses = episode_answers(soup)
    
    game = soup.find(id='game_title').get_text()
    return game, categories, clues, correct_responses, values

def make_rows(categories, clues, answers, season, episode, values):

    rows = []
    for i in range(len(clues)):
        rows.append({   'season': season,
                        'episode': episode,
                        'category': categories[i],
                        'value': values[i],
                        'clue': clues[i],
                        'answer': answers[i]})
    return rows

def save_df(df):
    feather.write_feather(df, f'data/{df.name}.feather')

def season_data(url):
    season_name = url.split('=')[1]
    
    df = pd.DataFrame()

    episodes = episode_urls(url)

    for i, episode in enumerate(episodes):
        game_name, categories, clues, answers, values = episode_data(episode)

        percent_acquired = f'{100 * (i+1) / len(episodes):4.2f}% complete:'

        print(f'{percent_acquired:16} Season {season_name:14} ({i + 1} / {len(episodes)})')
        df = df.append(make_rows(categories, clues, answers, season_name, game_name, values), ignore_index=True)
    
    print(f'Finished acquiring Season: {season_name}')

    df.name = season_name
    save_df(df)

    return df

def combine_data(dfs):
    df = pd.DataFrame()
    for season in dfs:
        df = df.append(season, ignore_index=True)
    return df

def all_seasons(seasons):

    season_dfs = []
    season_futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for season_url in seasons:
            season_futures.append(executor.submit(season_data, season_url))
    
    for future in concurrent.futures.as_completed(season_futures):
        season_dfs.append(future.result())

    return combine_data(season_dfs)

def clues(debug=False, fresh=False):
    if os.path.exists('jeopardy.feather') and not fresh:
        return pd.read_feather('jeopardy.feather')

    seasons = season_urls()

    all_seasons(seasons)

    jeopardy = combine_data()
    jeopardy.name = 'jeopardy'

    save_df(jeopardy)
    return jeopardy

if __name__ == '__main__':
    time = time()
    clues(debug=('debug' in sys.argv), fresh=('fresh' in sys.argv))
    print(f'{time() - time} elapsed.')