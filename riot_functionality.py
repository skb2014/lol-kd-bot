from auxiliary_functions import *

riot_api_key = getenv('RIOT_API_KEY')
routing_region = getenv('ROUTING_REGION')
riot_ids = getenv('RIOT_IDS').split(',')


# in general, when a function is unable to return a proper output for whatever reason, it will resort to returning None

async def get_puuid_from_riot_id(riot_id) -> str | None:
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
    raw_data = await get_http_response(url)
    if not raw_data:
        print_to_log("WARNING", f"Could not get match data for match ID: {match_id}")
        return None
    filtered_data = {}
    queue_types = {
        400: "Draft Pick", 420: "Ranked Solo/Duo", 440: "Ranked Flex", 450: "ARAM",
        490: "Quickplay", 700: "SR Clash", 720: "ARAM Clash", 900: "ARURF",
        1710: "Arena", 1900: "Pick URF", 2400: "ARAM: Mayhem"
    }
    filtered_data["queue_type"] = queue_types[raw_data["info"]["queueId"]]
    filtered_data["duration"] = raw_data["info"]["gameDuration"]
    filtered_data["players"] = {}
    for player in raw_data["info"]["participants"]:
        player_name = player["riotIdGameName"] + "#" + player["riotIdTagline"]
        filtered_data["players"][player_name] = {}
        puuid = await get_puuid_from_riot_id(player_name)
        filtered_data["players"][player_name]["puuid"] = puuid
        if player["teamId"] == 100:
            filtered_data["players"][player_name]["team"] = "blue"
        else:
            filtered_data["players"][player_name]["team"] = "red"
        if player["gameEndedInEarlySurrender"]:
            filtered_data["players"][player_name]["result"] = "drew"
        elif player["win"]:
            filtered_data["players"][player_name]["result"] = "won"
        else:
            filtered_data["players"][player_name]["result"] = "lost"
        match player["championName"]:
            case "AurelionSol":
                champion_name = "Aurelion Sol"
            case "Belveth":
                champion_name = "Bel'Veth"
            case "Chogath":
                champion_name = "Cho'Gath"
            case "DrMundo":
                champion_name = "Dr. Mundo"
            case "FiddleSticks":
                champion_name = "Fiddlesticks"
            case "JarvanIV":
                champion_name = "Jarvan IV"
            case "Kaisa":
                champion_name = "Kai'Sa"
            case "Kayn":
                if player["championTransform"] == 0:
                    champion_name = "Kayn"
                elif player["championTransform"] == 1:
                    champion_name = "Kayn (Rhaast)"
                else:
                    champion_name = "Kayn (Shadow Assassin)"
            case "Khazix":
                champion_name = "Kha'Zix"
            case "KogMaw":
                champion_name = "Kog'Maw"
            case "KSante":
                champion_name = "K'Sante"
            case "Leblanc":
                champion_name = "LeBlanc"
            case "LeeSin":
                champion_name = "Lee Sin"
            case "MasterYi":
                champion_name = "Master Yi"
            case "MissFortune":
                champion_name = "Miss Fortune"
            case "MonkeyKing":
                champion_name = "Wukong"
            case "Nunu":
                champion_name = "Nunu & Willump"
            case "RekSai":
                champion_name = "Rek'Sai"
            case "TahmKench":
                champion_name = "Tahm Kench"
            case "TwistedFate":
                champion_name = "Twisted Fate"
            case "Velkoz":
                champion_name = "Vel'Koz"
            case "XinZhao":
                champion_name = "Xin Zhao"
            case _:
                champion_name = player["championName"]
        filtered_data["players"][player_name]["champion"] = champion_name
        match player["teamPosition"]:
            case "TOP":
                role = "TOP"
            case "JUNGLE":
                role = "JG"
            case "MIDDLE":
                role = "MID"
            case "BOTTOM":
                role = "BOT"
            case "UTILITY":
                role = "SUPP"
            case _:
                # will be the value for games without roles such as ARAM, URF, etc.
                role = ""
        filtered_data["players"][player_name]["role"] = role
        filtered_data["players"][player_name]["kills"] = player["kills"]
        filtered_data["players"][player_name]["deaths"] = player["deaths"]
        filtered_data["players"][player_name]["assists"] = player["assists"]
        filtered_data["players"][player_name]["level"] = player["champLevel"]
        filtered_data["players"][player_name]["gold"] = player["goldEarned"]
        filtered_data["players"][player_name]["cs"] = player["totalMinionsKilled"] + player["neutralMinionsKilled"] + player["wardsKilled"]
        filtered_data["players"][player_name]["damage_dealt_to_champions"] = player["totalDamageDealtToChampions"]
        filtered_data["players"][player_name]["damage_dealt_to_epic_monsters"] = player["damageDealtToObjectives"] - player["damageDealtToBuildings"]
        # for the following number, I don't know if "buildings" encompasses turrets or turret damage needs to be added separately
        filtered_data["players"][player_name]["damage_dealt_to_structures"] = player["damageDealtToBuildings"]
        filtered_data["players"][player_name]["damage_healed_and_shielded_to_allies"] = player["totalDamageShieldedOnTeammates"] + player["totalHealsOnTeammates"]
        filtered_data["players"][player_name]["vision_score"] = player["visionScore"]
        # IS THIS ALL THE INFORMATION WE NEED? WHAT DO YOU THINK?
    return filtered_data


async def get_relevant_information_from_match_so_ai_can_determine_winning_or_losing_league(player_name: str) -> dict | None:
    """Gets the KDA of the player with the specified PUUID in their most recent match, returned as a dictionary with keys 'kills', 'deaths', 'assists'"""
    try:
        players = await read_json_file("jsons/players.json")
        matches = await read_json_file("jsons/matches.json")
        puuid = players[player_name]["puuid"]
        match_id = players[player_name]["most_recent_match_id"]
        match_data = matches[match_id]
        player_data = match_data["players"][player_name]
        sided = ""
        if match_data["queue_type"] in ["Draft Pick", "Ranked Solo/Duo", "Ranked Flex", "Quickplay", "SR Clash"]:
            if player_data["role"] in ["TOP", "BOT"]:
                jungle_player_puuid = None
                for player_name in match_data["players"]:
                    if match_data["players"][player_name]["team"] == player_data["team"] and match_data["players"][player_name]["role"] == "JG":
                        jungle_player_puuid = match_data["players"][player_name]["puuid"]
                top_or_bot = "TOP" if player_data["role"] == "TOP" else "BOT"
                sided = await calc_weakside(match_id, jungle_player_puuid, top_or_bot)
        team = player_data['team']
        role = player_data['role']
        opponent = ""
        for player_name in match_data["players"]:
            if match_data["players"][player_name]["team"] != team and role and match_data["players"][player_name]["role"] == role:
                opponent = f"vs. {match_data["players"][player_name]["champion"]}"
        return {
            'queue_type': match_data['queue_type'],
            'result': player_data['result'],
            'champion': player_data['champion'],
            'role': player_data['role'],
            'opponent': opponent,
            'kills': player_data['kills'],
            'deaths': player_data['deaths'],
            'assists': player_data['assists'],
            'sided': sided
        }
    except (TypeError, KeyError) as e:
        print_to_log("ERROR", f"error in getting important match data: {e}")
        return None


async def find_jungle_positions(match_id, jungle_player_puuid):
    if not jungle_player_puuid:
        print_to_log("WARNING", f"No jungle_player_puuid was provided for match ID: {match_id}")
        return None
    try:
        url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={riot_api_key}"
        data = await get_http_response(url)
        if data:
            info = data['info']
        else:
            print_to_log("WARNING", f"Could not get timeline data for match ID: {match_id}")
            return None

        players = info['participants']
        jg_participant_id = next((str(p['participantId']) for p in players if p['puuid'] == jungle_player_puuid))

        # limit to 20 (approx when laning phase ends)
        return [
            list(frame['participantFrames'][jg_participant_id]['position'].values())
            for frame in info['frames'][:21]
        ]
    except (StopIteration, KeyError, TypeError) as e:
        print_to_log("ERROR", f"error in finding jungle positions: {e}")
        return None


async def calc_weakside(match_id: int, jungle_player_puuid: str, top_or_bot: str) -> str | None:
    positions = await find_jungle_positions(match_id, jungle_player_puuid)
    if not positions:
        print_to_log("WARNING", f"Could not find calculate weakside for match ID: {match_id}")
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
    strongsided = (top_or_bot == "TOP" and topside >= botside) or (top_or_bot == "BOT" and botside >= topside)
    side_str = f"**strongsided** ({max(top_p, bot_p)}% jungle proximity)" if strongsided else f"**weaksided** ({min(top_p, bot_p)}% jungle proximity)"
    return f"They were {side_str}. "
