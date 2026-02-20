import discord
from discord import app_commands
from discord.ext import commands, tasks
from riot_functionality import *

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
# I want to be able to run the bot in a "testing" mode where it doesn't execute the update matches loop
bot.is_testing = False


@bot.event
async def setup_hook():
    try:
        # right now, all the commands are global
        # and they are syncing to the global cache,
        # not any specific server
        # it will take longer to update this way
        synced = await bot.tree.sync()  # Sync all slash commands
        print_to_log("INFO", f"Synced {len(synced)} command(s)")
    except Exception as e:
        print_to_log("ERROR", f"Failed to sync commands: {e}")


@bot.event
async def on_ready():
    print_to_log("INFO", f"Logged in as {bot.user}")
    print_to_log("INFO", f"Connected to {len(bot.guilds)} server(s)")
    if not bot.is_testing:
        update_matches_loop.start()
    print("Bot is running...")


async def send_a_long_message_in_multiple_parts(channel: discord.TextChannel, content: str, message_to_reply_to: discord.Message | None = None):
    # because discord has a 2000 character limit for non nitro members
    # note: if the text seems to randomly truncate, it's because it's
    # exceeding the token limit in the LLM query
    while len(content) > 1985:
        remainder_text = content[1985:]
        # updates message_to_reply_to to the message it just sent, so it can chain replies
        message_to_reply_to = await channel.send(content[:1985] + " ...(cont.)", reference=message_to_reply_to)
        content = remainder_text
    await channel.send(content, reference=message_to_reply_to)


@bot.event
async def on_message(message: discord.Message):
    # ignore messages sent by the bot itself to avoid infinite loops
    if message.author == bot.user:
        return
    channel = message.channel
    # the bot responds when you ping it
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        # shows the typing indicator
        async with message.channel.typing():
            # if the message was a reply to a previous message:
            # non-bot message -> AI response as normal
            # bot KDA message -> check if winning/losing league and find player
            # - if not able to -> AI response as normal
            # bot AI response -> read up the chain and continue the conversation
            normal_ai_response = True
            conversation = [{"role": "user", "content": message.content}]
            if message.reference:
                try:
                    prev_message = await channel.fetch_message(message.reference.message_id)
                # perhaps the previous message is actually deleted, so it can't be fetched
                except discord.NotFound:
                    print_to_log("WARNING", "Could not find message that was replied to")
                    prev_message = None
                if prev_message:
                    # check if it's just a KDA message
                    key_substrings = ["#", "just", "game", "KDA:"]
                    if prev_message.author == bot.user and all(term in prev_message.content for term in key_substrings):
                        normal_ai_response = False
                        conversation = [{"role": "assistant", "content": prev_message.content}] + conversation
                        conversation_modified = [{"role": "system", "content": prompt_1}] + conversation
                        response_text = await get_groq_response(conversation_modified)
                        if "Yes" in response_text:
                            # perform the winning/losing league analysis here
                            riot_id = prev_message.content.split()[0]
                            await channel.send(f"investigating {riot_id}...")
                        else:
                            await channel.send("Sorry, I'm confused")
                    # begin searching up to assemble the whole conversation
                    else:
                        while prev_message:
                            curr_message = prev_message
                            if prev_message.reference:
                                try:
                                    prev_message = await channel.fetch_message(prev_message.reference.message_id)
                                except discord.NotFound:
                                    print_to_log("WARNING", "Could not find message that was replied to")
                                    prev_message = None
                            else:
                                prev_message = None
                            if curr_message.author == bot.user:
                                role = "assistant"
                            else:
                                role = "user"
                            conversation = [{"role": role, "content": curr_message.content}] + conversation

            if normal_ai_response:
                conversation = [{"role": "system", "content": prompt_2}] + conversation
                response_text = await get_groq_response(conversation)
                await send_a_long_message_in_multiple_parts(channel, response_text, message)

        # lets the bot process other commands? idk if it's necessary since there are no text (non-slash) commands yet
        await bot.process_commands(message)


@bot.tree.command(name="add_channel", description="Registers this channel to the bot, allowing you to add players to be tracked")
async def add_channel(interaction: discord.Interaction):
    # JSON keys must be strings, not ints
    channel_id = str(interaction.channel.id)
    channels = await read_json_file("jsons/channels.json")
    if channel_id in channels:
        await interaction.response.send_message("This channel is already registered!")
        return
    channels[channel_id] = {"name": interaction.channel.name, "players": []}
    await write_json_file("jsons/channels.json", channels)
    await interaction.response.send_message("Channel registered successfully!")
    return


@bot.tree.command(name="remove_channel", description="Removes this channel from tracking, clearing all players")
async def remove_channel(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    channels = await read_json_file("jsons/channels.json")
    if channel_id not in channels:
        await interaction.response.send_message("This channel is already not registered!")
        return

    for player_name in channels[channel_id]["players"]:
        await remove_player_from_file(player_name, channel_id)
    # del might be more dangerous, so pop is used instead
    channels.pop(channel_id)
    await write_json_file("jsons/channels.json", channels)
    await interaction.response.send_message("Channel removed successfully!")
    return


@bot.tree.command(name="list_players", description="Lists all players currently being tracked in this channel")
async def list_players(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    channels = await read_json_file("jsons/channels.json")
    if channel_id not in channels:
        await interaction.response.send_message("This channel is not registered!")
        return

    index = 1
    message_string = ""
    for player_name in channels[channel_id]["players"]:
        message_string += f"{index}. {player_name}\n"
        index += 1
    if index == 1:
        await interaction.response.send_message("No players are being tracked in this channel!")
    else:
        # delete the last newline character
        message_string = message_string[:-1]
        await interaction.response.send_message(message_string)


async def add_player_to_file(player_name, channel_id) -> str:
    channels = await read_json_file("jsons/channels.json")
    players = await read_json_file("jsons/players.json")
    if channel_id not in channels:
        return "Channel not registered!"

    if player_name in channels[channel_id]["players"]:
        return "Player already registered in this channel!"
    # need to check that the player is real by verifying that it has a PUUID
    puuid = await get_puuid_from_riot_id(player_name)
    if puuid is None:
        return f"Player {player_name} not found!"

    channels[channel_id]["players"].append(player_name)
    # if the player isn't already in the players.json file, add them
    if player_name not in players:
        players[player_name] = {"puuid": puuid, "channels": [channel_id], "most_recent_match_id": None}
    else:
        players[player_name]["channels"].append(channel_id)

    await write_json_file("jsons/channels.json", channels)
    await write_json_file("jsons/players.json", players)
    return f"{player_name} added successfully!"


async def remove_player_from_file(player_name, channel_id):
    channels = await read_json_file("jsons/channels.json")
    players = await read_json_file("jsons/players.json")
    if channel_id not in channels:
        return "Channel not registered!"
    if player_name not in channels[channel_id]["players"]:
        return "Player already not registered in this channel!"

    channels[channel_id]["players"].remove(player_name)
    players[player_name]["channels"].remove(channel_id)
    # if the player doesn't exist in any channels, delete them
    if not players[player_name]["channels"]:
        players.pop(player_name)

    await write_json_file("jsons/channels.json", channels)
    await write_json_file("jsons/players.json", players)
    return f"{player_name} removed successfully!"


@bot.tree.command(name="add_player", description="Adds a player to be tracked in this channel (channel must be registered")
async def add_player(interaction: discord.Interaction, player_name: str):
    channel_id = str(interaction.channel.id)
    result = await add_player_to_file(player_name, channel_id)
    await interaction.response.send_message(result)


async def player_autocomplete(interaction: discord.Interaction, current: str):
    players = await read_json_file("jsons/players.json")
    player_names = list(players.keys())
    return [app_commands.Choice(name=name, value=name) for name in player_names if current.lower() in name.lower()][:25]


@bot.tree.command(name="remove_player", description="Removes a player from being tracked in this channel (channel must be registered)")
@app_commands.autocomplete(player_name=player_autocomplete)
async def remove_player(interaction: discord.Interaction, player_name: str):
    channel_id = str(interaction.channel.id)
    result = await remove_player_from_file(player_name, channel_id)
    await interaction.response.send_message(result)


@bot.tree.command(name="investigate_player", description="Checks player's most recent game to determine winning/losing league")
@app_commands.autocomplete(player_name=player_autocomplete)
async def investigate_player(interaction: discord.Interaction, player_name: str):
    await interaction.response.send_message(f"investigating {player_name}")


@bot.tree.command(name="clear_all_data", description="Clears all data stored by the bot, including players and matches")
async def clear_all_data(interaction: discord.Interaction):
    """Use for debugging purposes, will probably be removed later"""
    await write_json_file("jsons/channels.json", {})
    await write_json_file("jsons/players.json", {})
    await write_json_file("jsons/matches_data_raw.json", {})
    await interaction.response.send_message("All data cleared successfully!")


async def print_match_kda(channel_id, player_name, match_id):
    players = await read_json_file("jsons/players.json")
    puuid = players[player_name]["puuid"]
    kda = await get_kda_from_match(puuid, match_id)
    result = "lost" if kda["lost"] else "won"
    channel = bot.get_channel(int(channel_id))
    await channel.send(
        f"**{player_name}** just **{result}** a game. {kda["sided"]} KDA: {kda["kills"]}/{kda["deaths"]}/{kda["assists"]}")


@tasks.loop(seconds=60)
async def update_matches_loop():
    """Repeatedly checks all players for new matches, and if one is found, the bot types their KDA in the given discord channels"""
    print_to_log("INFO", "Checking for new matches...")

    players = await read_json_file("jsons/players.json")
    matches = await read_json_file("jsons/matches_data_raw.json")
    old_match_ids = set()
    for match_id in matches:
        old_match_ids.add(match_id)
    new_match_ids = set()
    players_with_new_matches = dict()
    for player_name in players.keys():
        new_match_id = await get_latest_match_id(players[player_name]["puuid"])
        if new_match_id is None:
            print_to_log("WARNING", f"Failed to get match ID for player {player_name}, skipping...")
            break
        print_to_log("INFO", f"Player {player_name}'s most recent match has ID: {new_match_id}")
        print_to_log("INFO", f"Their previous most recent match had ID {players[player_name]['most_recent_match_id']}")
        new_match_ids.add(new_match_id)
        if new_match_id != players[player_name]["most_recent_match_id"]:
            players[player_name]["most_recent_match_id"] = new_match_id
            players_with_new_matches[player_name] = new_match_id
    await write_json_file("jsons/players.json", players)
    print_to_log("INFO", f"Players with new matches -- {players_with_new_matches}")

    match_ids_to_be_deleted = old_match_ids - new_match_ids
    match_ids_to_be_added = new_match_ids - old_match_ids
    for match_id in match_ids_to_be_deleted:
        matches.pop(match_id)
    for match_id in match_ids_to_be_added:
        match_data = await get_match_data(match_id)
        matches[match_id] = match_data
    await write_json_file("jsons/matches_data_raw.json", matches)

    channels = await read_json_file("jsons/channels.json")
    for channel_id in channels:
        for player_name in channels[channel_id]["players"]:
            if player_name in players_with_new_matches:
                print_to_log("INFO", f"Sending KDA message for {player_name} in channel {channels[channel_id]["name"]}")
                await print_match_kda(channel_id, player_name, players_with_new_matches[player_name])
