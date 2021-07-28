import pandas as pd
from bs4 import BeautifulSoup
from requests import get
import wikipedia as wiki
import pyarrow.feather as feather
import os


URL = "https://j-archive.com/"

def get_season_urls():
    '''
    gets the urls for all seasons of jeopardy from the above website
    '''
    url_suffix = "listseasons.php"

    # gets html from website index
    response = get(URL + url_suffix)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # picks out all season elements
    seasons_html = soup.find_all('tr')
    seasons = []

    # takes season URLs out of html chunks
    for season in seasons_html:
        seasons.append(season.find('a').get('href'))
    return seasons

def get_episode_urls(season_url):
    '''
    gets URLs for all episodes in a given season
    '''

    # gets html of season index
    response = get(URL + season_url)

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

def get_episode_category_list(episode_soup):
    '''
    gets a list of all clue categories out of a given episode's html soup
    '''

    # finds all html chunks with the category_name class
    soups = episode_soup.find_all('td', class_="category_name")

    # goes through each td chunk and finds the category name in it. Sometimes it's split into multiple html elements.
    category_list = []
    for i in soups:
        if i.string is not None:
            category_list.append(i.string)
        else:
            category = ''
            for element in i.contents:
                if element.string is not None:
                    category += element.string
            category_list.append(category)

    return category_list

def get_episode_clue_data(episode_soup, category_list):
    '''
    returns a list of all clues and their categories in an episode, given the episode page's soup
    '''
    clues = []
    categories = []

    for spoonful in episode_soup.find_all(class_='clue_text'):
        clues.append(spoonful.text)
        clue_code = spoonful.get('id')[5:]
        category = decode_category(clue_code, category_list)
        categories.append(category)
    return clues, categories
    
def get_episode_answers(episode_soup):
    '''
    returns a list of correct answers in an episode given the episode page's soup
    '''
    answers = []
    spoonfuls = []

    for tag in episode_soup.find_all('div', onmouseover=True): 
        spoonfuls.append(tag['onmouseover']) 

    for soup_string in spoonfuls:
        answer_soup = BeautifulSoup(soup_string)
        answers.append(answer_soup.find('em').string)
    return answers

def get_episode_data(episode_url):
    '''
    given an episode's url returns a tuple of lists of the categories, clues, and correct answers in an episode
    '''

    response = get(episode_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    category_list = get_episode_category_list(soup)

    clues, categories = get_episode_clue_data(soup, category_list)
    correct_responses = get_episode_answers(soup)
    
    game = soup.find(id='game_title').string
    return game, categories, clues, correct_responses

def make_rows(categories, clues, answers, season, episode):
    rows = []
    for i in range(len(clues)):
        rows.append({   'season': season,
                        'episode': episode,
                        'category': categories[i],
                        'clue': clues[i],
                        'answer': answers[i]})
    return rows

def get_wiki_title(answer, debug=True):
    results = wiki.search(answer)
    if results == []:
        print(f'{answer} not found.')
        return None
    title = results[0]
    print(f'{answer} matched {title}')
    return title

def get_wiki_data(wiki_title, full_content = False):
    if wiki_title is None:
        return None
    if full_content:
        return wiki.page(wiki_title).content
    wiki_info = wiki.summary(wiki_title)
    return wiki_info

def save_df(df):
    feather.write_feather(df, f'{df.name}.feather')

def get_clues(debug=False, update=False):
    jeopardy = pd.DataFrame()
    jeopardy.name = 'jeopardy'
    if os.path.exists('jeopardy.feather'):
        jeopardy = feather.read_feather('jeopardy.feather')
        if not update:
            return jeopardy
    
    seasons = pd.DataFrame()
    seasons['urls'] = get_season_urls()

    seasons['names'] = seasons['urls'].str.split('=').apply(lambda x: x[1])

    for url in seasons['urls']:
        season = seasons[seasons['urls'] == url].loc[0, 'names']

        if update:
            acquired_games = set(jeopardy[jeopardy.season == season]['episode'])

        if debug:
            print(f'Acquiring Season: {season}')

        episodes = get_episode_urls(url)

        for episode in episodes:
            game_name, categories, clues, answers = get_episode_data(episode)
            if update and game_name in acquired_games:
                break
            if debug:
                print(f'Just acquired: {game_name}')
            jeopardy.append(make_rows(categories, clues, answers, season, game_name), ignore_index=True)
    
    save_df(jeopardy)
    return jeopardy

def get_wiki_df(debug=False):
    if os.path.exists('wiki.feather'):
        wiki = feather.read_feather('wiki.feather')
        return wiki

    wiki = get_clues()
    wiki.name = 'wiki'
    
    if debug:
        wiki['title'] = wiki['answer'].apply(lambda x: get_wiki_title(x, True))
    else:
        wiki['title'] = wiki['answer'].apply(get_wiki_title)
    wiki['summary'] = wiki['title'].apply(get_wiki_data)

    save_df(wiki)
    return wiki