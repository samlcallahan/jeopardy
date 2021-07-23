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

# given a clue code and an episode's full list of categories, returns the clue's category name
# clue codes are of the format [J/DJ]_[category_number]_[question_number] or FJ
def decode_category(code, categories):
    if code[0] == 'J':
        index = int(code[-3]) - 1
        return categories[index]
    elif code[0] == 'D':
        index = int(code[-3]) - 8
        # if len(categories) < 13:
        #     index -= 6
        return categories[index]
    else:
        return categories[-1]

# gets a list of all clue categories out of a given episode's html soup
def get_episode_category_list(episode_soup):

    # finds all td html chunks
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

# returns a list of all clues and their categories in an episode, given the episode page's soup
def get_episode_clue_data(episode_soup, category_list):
    clues = []
    categories = []

    for spoonful in episode_soup.find_all(class_='clue_text'):
        clues.append(spoonful.text)
        clue_code = spoonful.get('id')[5:]
        category = decode_category(clue_code, category_list)
        categories.append(category)
    return clues, categories
    
# returns a list of correct answers in an episode given the episode page's soup
def get_episode_answers(episode_soup):
    answers = []
    spoonfuls = []

    for tag in episode_soup.find_all('div', onmouseover=True): 
        spoonfuls.append(tag['onmouseover']) 

    for soup_string in spoonfuls:
        answer_soup = BeautifulSoup(soup_string)
        answers.append(answer_soup.find('em').string)
    return answers

# given an episode's url returns a tuple of lists of the categories, clues, and correct answers in an episode
def get_episode_data(episode_url):
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

def get_clues(debug=False, first_only=False):
    seasons = pd.DataFrame()
    seasons['urls'] = get_season_urls()
    seasons['names'] = seasons['urls'].str.split('=').apply(lambda x: x[1])

    jeopardy = []

    for url in seasons['urls']:
        if debug:
            print(f'Going to {url}')
        season = seasons[seasons['urls'] == url]['names'].item()
        if debug:
            print(f'Acquiring Season: {season}')
        episodes = get_episode_urls(url)
        for episode in episodes:
            game_name, categories, clues, answers = get_episode_data(episode)
            if debug:
                print(f'Just acquired: {game_name}')
            jeopardy += make_rows(categories, clues, answers, season, game_name)
        if first_only:
            break
    
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