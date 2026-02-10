from os import getenv
from dotenv import load_dotenv
import json
import aiohttp
import aiofiles

load_dotenv()
riot_api_key = getenv('RIOT_API_KEY')
routing_region = getenv('ROUTING_REGION')
riot_ids = getenv('RIOT_IDS').split(',')

async def read_json_file(filename):
    """Safely reads a JSON file and returns a dictionary."""
    try:
        async with aiofiles.open(filename, mode="r") as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Returning empty dict.")
        return {}
    except json.JSONDecodeError:
        print(f"Warning: {filename} is corrupted. Returning empty dict.")
        return {}

async def write_json_file(filename, data):
    """Safely writes a dictionary to a JSON file."""
    async with aiofiles.open(filename, mode="w") as f:
        await f.write(json.dumps(data, indent=4))
    # if there is no data, write an empty dictionary
    if not data:
        await f.write("{}")

async def get_http_response(url):
    """Sends a GET request to the specified URL and returns the response. Checks the status code as well."""
    async with aiohttp.ClientSession() as session:
        # the next with block automatically releases the response after it's done with it
        async with session.get(url) as response:
            response_code_errors = {
                400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Rate Limit Exceeded",
                500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"
            }
            # you do not need to await response.status as it is just an integer, not a coroutine (unlike .json() for example)
            if response.status != 200:
                print(f"Request to Riot API failed with status code {response.status} {response_code_errors[response.status]}")
                return None
            else:
                return await response.json()

async def get_puuid_from_riot_id(riot_id):
    """Gets the unique PUUID for an account using their Riot ID which looks like GameName#TagLine"""
    if len(riot_id.split('#')) == 2:
        game_name, tag_line = riot_id.split('#')
    else:
        print("Invalid Riot ID format, should be GameName#TagLine")
        return None
    url = f"https://{routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={riot_api_key}"
    # this code is asyncable (unlike requests -- in theory)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response_handler(response):
                data = await response.json()
                return data['puuid']
            else:
                return None

async def get_latest_match_id(puuid):
    """Gets the match ID of the most recent match that the player with the specified PUUID played"""
    if puuid is None:
        print("No PUUID entered, returning None")
        return None
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={riot_api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response_handler(response):
                data = await response.json()
                return data[0]
            else:
                print("Failed to get response from riot/account/v1/accounts/by-puuid/")
                return None

async def get_match_data(match_id):
    print("Finding match data...")
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response_handler(response):
                data = await response.json()
                return data
            else:
                print("Failed to get response from match id endpoint")
                return None

async def get_kda_from_match(puuid, match_id):
    """Gets the KDA of the player with the specified PUUID in their most recent match, returned as a dictionary with keys 'kills', 'deaths', 'assists'"""
    async with aiofiles.open("matches.json", "r") as f:
        content = await f.read()
        matches = json.loads(content)
    match_data = matches[match_id]
    player_index = match_data['metadata']['participants'].index(puuid)
    participants = match_data['info']['participants']
    player_data = participants[player_index]
    player_position = player_data['teamPosition']
    sidelane = player_position not in ["UTILITY", "JUNGLE", "MIDDLE"]
    sided = await calc_weakside(participants, match_id, player_data["teamId"], player_position) if sidelane else ""
    return {
        'kills': player_data['kills'], 
        'deaths': player_data['deaths'], 
        'assists': player_data['assists'],
        'lost': player_data['nexusLost'],
        'sided': sided
    }

async def find_jungle_positions(participants, match_id, team_id):
    jungle_id = next(
        (p['puuid'] for p in participants if p['teamPosition'] == "JUNGLE" and p["teamId"] == team_id),
        None
    )

    if not jungle_id:
        return None
    
    # print(jungle_id)
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={riot_api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response_handler(response):
                data = await response.json()
    info = data['info']

    players = info['participants']
    jg_participant_id = next(
        (str(p['participantId']) for p in players if p['puuid'] == jungle_id),
        None
    )

    if not jg_participant_id:
        return None

    # limit to 20 (approx when laning phase ends)
    return [
        list(frame['participantFrames'][jg_participant_id]['position'].values()) 
        for frame in info['frames'][:21]
    ]

async def calc_weakside(participants, match_id, team_id, position):
    positions = await find_jungle_positions(participants, match_id, team_id)
    if not positions:
        return None
    
    total = len(positions)
    topside, botside = 0, 0
    for x, y in positions:
        if y >= 5000 and y > x and x <= 10000:
            topside += 1
        elif x >= 5000 and x > y and y <= 10000:
            botside += 1

    top_p, bot_p = round((topside / total) * 100, 2), round((botside / total) * 100, 2)
    print(top_p, bot_p)
    strongsided = (position == "TOP" and topside >= botside) or (position == "BOTTOM" and botside >= topside)
    side_str = f"**strongsided** ({max(top_p, bot_p)}%)" if strongsided else f"**weaksided** ({min(top_p, bot_p)}%)"
    return f"They were {side_str}. "
