from os import getenv
from dotenv import load_dotenv
import requests

load_dotenv()
riot_api_key = getenv('RIOT_API_KEY')
routing_region = getenv('ROUTING_REGION')
riot_ids = getenv('RIOT_IDS').split(',')

def response_checker(response):
    """Checks the status code of a response and raises an exception if it's not 200"""
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}, response text: {response.text}")
        return False
    else:
        return True

def get_puuid_from_riot_id(riot_id):
    """Gets the unique PUUID for an account using their Riot ID which looks like GameName#TagLine"""
    game_name, tag_line = riot_id.split('#')
    url = f"https://{routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={riot_api_key}"
    response = requests.get(url)
    if response_checker(response):
        return response.json()['puuid']
    else:
        print("Failed to get response from riot/account/v1/accounts/by-riot-id/")
        return None

def get_most_recent_match(puuid):
    """Gets the match ID of the most recent match that the player with the specified PUUID played"""
    if puuid is None:
        print("No PUUID entered, returning None")
        return None
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={riot_api_key}"
    response = requests.get(url)
    if response_checker(response):
        return response.json()[0]
    else:
        print("Failed to get response from riot/account/v1/accounts/by-puuid/")
        return None

def get_kda_from_most_recent_match(puuid, match_id):
    """Gets the KDA of the player with the specified PUUID in their most recent match, returned as a dictionary with keys 'kills', 'deaths', 'assists'"""
    if puuid is None:
        print("No PUUID entered, returning None")
        return None
    if match_id is None:
        print("No match ID entered, returning None")
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}"
    response = requests.get(url)
    if response_checker(response):
        player_index = response.json()['metadata']['participants'].index(puuid)
        player_data = response.json()['info']['participants'][player_index]
        kills = player_data['kills']
        deaths = player_data['deaths']
        assists = player_data['assists']
        return {'kills': kills, 'deaths': deaths, 'assists': assists}
    else:
        print("Failed to get response from riot/match/v5/matches/")
        return None
