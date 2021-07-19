import pandas as pd
from bs4 import BeautifulSoup
from requests import get
import wikipedia as wiki


URL = "https://j-archive.com/"

# gets the urls for all seasons of jeopardy from the above website
def get_season_urls():
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

# gets URLs for all episodes in a given season
def get_episode_urls(season_url):

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

# gets all clue categories out of a given episode's html soup
def get_episode_categories(episode_soup):

    # finds all td html chunks
    soups = episode_soup.find_all('td', class_="category_name")

    # goes through each td chunk to make sure it's a category title -- if it is, adds it to list of categories
    categories = []
    for i in soups:
        if i.string is not None:
            categories.append(i.string)
        else:
            category = ''
            for element in i.contents:
                if element.string is not None:
                    category += element.string
            categories.append(category)
    return categories

def decode_category(code, categories):
    if code[0] == 'J':
        return categories[code[-3]]
    elif code[0] == 'D':
        return categories[code[-3] + 6]
    else:
        return categories[-1]

def get_episode_clues(episode_url):
    response = get(episode_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    category_list = get_episode_categories(soup)

    clues = []
    categories = []
    correct_responses = []
    correct_response_soups = [] 

    for tag in soup.find_all('div', onmouseover=True): 
        correct_response_soups.append(tag['onmouseover']) 
    # classes: correct_response, clue_text

    for soup_string in correct_response_soups:
        correct_response_soup = BeautifulSoup(soup_string)
        correct_responses.append(correct_response_soup.find('em').string)
    # id: clue_[category_number]_[clue_number]

    for tag in soup.find_all(class_='clue_text'):
        clues.append(tag.text)
        clue_code = decode_category(tag.get('id')[5:], category_list)
        categories.append(clue_code)
    
    game = soup.find(class_)
    return categories, clues, correct_responses

def make_rows(categories, clues, answers, season, episode):
    rows = []
    for i in range(len(clues)):
        rows.append({   'season': season,
                        'episode': episode,
                        'category': categories[i],
                        'clue': clues[i],
                        'answer': answers[i]})
    return rows

def get_clues(debug=False):
    seasons = pd.DataFrame()
    seasons['urls'] = get_season_urls()
    seasons['names'] = seasons['urls'].str.split('=').apply(lambda x: x[1])

    jeopardy = []

    for url in seasons['urls']:
        season = seasons[seasons['urls'] == url]['names']['names']
        if debug:
            print(season)
        episodes = get_episode_urls(url)
        for episode in episodes:
            ep_id = episode[-4:]
            if debug:
                print(ep_id)
            categories, clues, answers = get_episode_clues(episode)
            jeopardy.append(make_rows(categories, clues, answers, season, ep_id))
    
    return pd.DataFrame(jeopardy)


'''
clues 

id
clue text
answer text (not in question form)
categorys
date

wikis

id
answer/wiki title (should be the same?)
wiki contents
'''