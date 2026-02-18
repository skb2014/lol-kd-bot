from auxiliary_functions import *

riot_api_key = getenv('RIOT_API_KEY')
routing_region = getenv('ROUTING_REGION')
riot_ids = getenv('RIOT_IDS').split(',')


# in general, when a function is unable to return a proper output for whatever reason, it will resort to returning None

async def get_puuid_from_riot_id(riot_id):
    """Gets the unique PUUID for an account using their Riot ID which looks like GameName#TagLine"""
    if len(riot_id.split('#')) == 2:
        game_name, tag_line = riot_id.split('#')
    else:
        print_to_log("WARNING", f"Invalid Riot ID format: {riot_id}. Should be GameName#TagLine")
        print("Invalid Riot ID format, should be GameName#TagLine")
        return None
    url = f"https://{routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}?api_key={riot_api_key}"
    data = await get_http_response(url)
    if data:
        return data["puuid"]
    else:
        print_to_log("WARNING", f"Could not find PUUID for Riot ID: {riot_id}")
        return None


async def get_latest_match_id(puuid):
    """Gets the match ID of the most recent match that the player with the specified PUUID played"""
    if puuid is None:
        print_to_log("WARNING", "PUUID is None")
        return None
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={riot_api_key}"
    data = await get_http_response(url)
    if data:
        return data[0]
    else:
        print_to_log("WARNING", f"Could not get matches for for PUUID: {puuid}")
        return None


async def get_match_data(match_id):
    print_to_log("INFO", f"Getting match data for match ID: {match_id}")
    url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}"
    data = await get_http_response(url)
    if data:
        return data
    else:
        print_to_log("WARNING", f"Could not get match data for match ID: {match_id}")
        return None


async def glean_useful_match_data(match_id):
    matches_data_raw = await read_json_file("jsons/matches_data_raw.json")
    raw_match_data = matches_data_raw[match_id]


async def get_kda_from_match(puuid, match_id) -> dict | None:
    """Gets the KDA of the player with the specified PUUID in their most recent match, returned as a dictionary with keys 'kills', 'deaths', 'assists'"""
    try:
        matches = await read_json_file("jsons/matches_data_raw.json")
        # TODO -- THE FOLLOWING LINE KEEPS CAUSING ERRORS AND I DONT KNOW WHY
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
    except (TypeError, KeyError) as e:
        print_to_log("ERROR", f"error in finding kda: {e}")
        return None


async def find_jungle_positions(participants, match_id, team_id):
    try:
        jungle_id = next((p['puuid'] for p in participants if p['teamPosition'] == "JUNGLE" and p["teamId"] == team_id))
        url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={riot_api_key}"
        data = await get_http_response(url)
        info = data['info']

        players = info['participants']
        jg_participant_id = next((str(p['participantId']) for p in players if p['puuid'] == jungle_id))

        # limit to 20 (approx when laning phase ends)
        return [
            list(frame['participantFrames'][jg_participant_id]['position'].values())
            for frame in info['frames'][:21]
        ]
    except (StopIteration, KeyError, TypeError) as e:
        print_to_log("ERROR", f"error in finding jungle positions: {e}")
        return None


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
    print_to_log("INFO", f"top_p: {top_p}, bot_p: {bot_p}")
    strongsided = (position == "TOP" and topside >= botside) or (position == "BOTTOM" and botside >= topside)
    side_str = f"**strongsided** ({max(top_p, bot_p)}%)" if strongsided else f"**weaksided** ({min(top_p, bot_p)}%)"
    return f"They were {side_str}. "

async def get_relevant_information_from_match_so_ai_can_determine_winning_or_losing_league(player_name):
    pass
