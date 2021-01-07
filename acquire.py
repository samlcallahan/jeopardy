import pandas as pd
from bs4 import BeautifulSoup
from requests import get
import wikipedia as wiki


URL = "https://j-archive.com/"

def get_season_urls():
    url_suffix = "listseasons.php"
    response = get(URL + url_suffix)
    soup = BeautifulSoup(response.content, 'html.parser')
    seasons_html = soup.find_all('tr')
    seasons = []
    for season in seasons_html:
        seasons.append(season.find('a').get('href'))
    return seasons

def get_episode_urls(season_url):
    response = get(URL + season_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    episodes_html = soup.find_all('tr')
    episodes = []
    for episode in episodes_html:
        episodes.append(episode.find('a').get('href'))
    return episodes

def get_episode_clues(episode_url):
    response = get(episode_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    clues = []
    # classes: correct_response, clue_text
    # id: clue_[category_number]_[clue_number]
    for 
    
def get_clues():
    seasons = get_season_urls()

clues
'''
id
clue text
answer text (not in question form)
category
date
'''
wikis
'''
id
answer/wiki title (should be the same?)
wiki contents
'''