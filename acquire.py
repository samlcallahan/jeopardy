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

def get_episode_categories(episode_soup):
    soups = episode_soup.find_all('td', class_="category_name")
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

def get_episode_clues(episode_url):
    response = get(episode_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    categories = get_episode_categories(soup)

    clues = []
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
        clues.append(tag.string)

    return categories, clues, correct_responses

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