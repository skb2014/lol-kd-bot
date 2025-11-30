import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
riot_api_key = os.getenv('RIOT_API_KEY')
routing_region = os.getenv('ROUTING_REGION')

riot_IDs = ['LittleYay#NA1', 'voidfłight#NA1', 'Mewzer2#NA1', 'UnsaltedSalt#NA1', 'skb#4559', 'ASneakySquirrel#NA1']

def get_puuid_from_riot_id(riot_id):
    game_name, tag_line = riot_id.split('#')
    url = f"https://{routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={riot_api_key}"
    response = requests.get(url)
    return response.json()['puuid']

def get_most_recent_match(puuid):
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={riot_api_key}"
    response = requests.get(url)
    return response.json()[0]
# "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20&api_key={riot_api_key}"

def get_kda_from_most_recent_match(puuid):
    match_id = get_most_recent_match(puuid)
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}"
    response = requests.get(url)
    player_index = response.json()['metadata']['participants'].index(puuid)
    player_data = response.json()['info']['participants'][player_index]
    kills = player_data['kills']
    deaths = player_data['deaths']
    assists = player_data['assists']
    return {'kills': kills, 'deaths': deaths, 'assists': assists}

