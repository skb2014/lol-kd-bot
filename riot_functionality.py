import os
from dotenv import load_dotenv
import requests

load_dotenv()
riot_api_key = os.getenv('RIOT_API_KEY')
routing_region = os.getenv('ROUTING_REGION')
riot_ids = os.getenv('RIOT_IDS').split(',')

def get_puuid_from_riot_id(riot_id):
    """Gets the unique PUUID for an account using their Riot ID which looks like GameName#TagLine"""
    game_name, tag_line = riot_id.split('#')
    url = f"https://{routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={riot_api_key}"
    response = requests.get(url)
    print(f"request sent to riot/account/v1/accounts/by-riot-id/, response code: {response.status_code}")
    return response.json()['puuid']

def get_most_recent_match(puuid):
    """Gets the match ID of the most recent match that the player with the specified PUUID played"""
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={riot_api_key}"
    response = requests.get(url)
    print(f"request sent to lol/match/v5/matches/by-puuid/, response code: {response.status_code}")
    return response.json()[0]

def get_kda_from_most_recent_match(puuid, match_id):
    """Gets the KDA of the player with the specified PUUID in their most recent match, returned as a dictionary with keys 'kills', 'deaths', 'assists'"""
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}"
    response = requests.get(url)
    print(f"request sent to lol/match/v5/matches/, response code: {response.status_code}")
    player_index = response.json()['metadata']['participants'].index(puuid)
    player_data = response.json()['info']['participants'][player_index]
    kills = player_data['kills']
    deaths = player_data['deaths']
    assists = player_data['assists']
    return {'kills': kills, 'deaths': deaths, 'assists': assists}
