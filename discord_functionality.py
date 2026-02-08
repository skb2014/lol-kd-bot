import discord
from discord.ext import commands, tasks
from riot_functionality import *
import json
import logging
import aiofiles
from groq import AsyncGroq

# guild_ids = list(map(int, getenv('DISCORD_GUILD_IDS').split(',')))
# channel_ids = list(map(int, getenv('DISCORD_CHANNEL_IDS').split(',')))
# guilds = []
# channels = []
async_groq_client = AsyncGroq(api_key=getenv('GROQ_API_KEY'))

with open("puuids.json") as f:
    puuids = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
# I want to be able to run the bot in a "testing" mode where it doesn't execute the update matches loop
bot.is_testing = False

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logger = logging.getLogger('Match Checker')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

async def print_match_kda(riot_id, kda):
    """Prints the Riot ID and KDA in each of the given discord channels."""
    result = "lost" if kda["lost"] else "won"
    # for channel in channels:
        # await channel.send(f'{riot_id} has just **{result}** a game. {kda['sided']} KDA: {kda["kills"]}/{kda["deaths"]}/{kda["assists"]}')

@tasks.loop(seconds=30)
async def update_matches_loop():
    """Repeatedly checks all players for new matches, and if one is found, the bot types their KDA in the given discord channels.
    The most recent match IDs are saved in a .json file."""
    print("Checking for new matches...")
    logger.info("Checking for new matches...")

    with open('most_recent_matches.json', 'r') as f:
        most_recent_matches = json.load(f)
    most_recent_matches_updated = {}

    seen_matches = {}
    for riot_id in riot_ids:
        logger.info(f"Checking {riot_id}")
        puuid = get_puuid_from_riot_id(riot_id) if riot_id not in puuids else puuids[riot_id]
        if puuid is None:
            logger.warning(f"Failed to get PUUID for {riot_id}")
            most_recent_matches_updated[riot_id] = most_recent_matches[riot_id]
            continue

        match_id = get_most_recent_match(puuid)
        if match_id is None:
            logger.warning(f"Failed to get match ID for {riot_id}")
            most_recent_matches_updated[riot_id] = most_recent_matches[riot_id]
            continue

        kda = None
        if riot_id not in most_recent_matches or most_recent_matches[riot_id] != match_id:
            match_data = seen_matches[match_id] if match_id in seen_matches else get_match(match_id)
            kda = get_kda_from_most_recent_match(puuid, match_data, match_id)
            if kda is None:
                logger.warning(f"Failed to get KDA for {riot_id}")
            
            seen_matches[match_id] = match_data

        if kda:
            print(f"Found a new KDA for {riot_id}")
            await print_match_kda(riot_id, kda)

        # ensures that the kda message is sent for a new match
        most_recent_matches_updated[riot_id] = match_id

    with open("most_recent_matches.json", "w") as f:
        json.dump(most_recent_matches_updated, f, indent=4)

@bot.event
async def setup_hook():
    try:
        # right now, all the commands are global
        # and they are syncing to the global cache,
        # not any specific server
        # it will take longer to update this way
        synced = await bot.tree.sync()  # Sync all slash commands
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print(f'Connected to {len(bot.guilds)} server(s)')
    if not bot.is_testing:
        update_matches_loop.start()

@bot.event
async def on_message(message):
    # ping the bot to get AI responses

    # ignore messages sent by the bot itself to avoid infinite loops
    if message.author == bot.user:
        return
    # anson doesn't get rights
    if message.author.id == 312825670428393472:
        await message.channel.send("stfu nerd")
        return

    # the bot responds when you ping it
    if bot.user.mentioned_in(message):
        # clean the message: remove the <@ID> mention and leading/trailing whitespace
        user_query = message.content.replace(f'<@{bot.user.id}>', '').strip()

        if not user_query:
            await message.channel.send(f"what do you want {message.author.mention}")
            return

        # uses a typing indicator so users know the AI is thinking
        async with message.channel.typing():
            try:
                chat_completion = await async_groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system",
                         "content": """You are a discord bot whose role is to analyze match data and determine
                         whether specificied players are playing "winning league" (i.e., they are contributing
                         in a useful manner), or "losing league" (i.e., actively detrimental to the team )."""},
                        {"role": "user", "content": user_query}
                    ],
                    max_completion_tokens=512  # approximately 2k characters to not run into the message character limit
                )

                response_text = chat_completion.choices[0].message.content
                # safety slice for discord's 2000 character limit for messages
                while len(response_text) > 1990:
                    remainder_text = response_text[1990:]
                    await message.channel.send(response_text[:1990] + "...")
                    # !! perhaps this should be a reply chain
                    response_text = remainder_text
                await message.channel.send(response_text)
                    
            except Exception as e:
                await message.channel.send(f"Error: {e}")

    # lets the bot process other commands? idk if it's necessary since there are no text (non-slash) commands yet
    await bot.process_commands(message)

@bot.tree.command(name="add_channel", description="Registers this channel to the bot, allowing you to add players to be tracked")
async def add_channel(interaction: discord.Interaction):
    # JSON keys must be strings, not ints
    new_channel_id = str(interaction.channel.id)
    async with aiofiles.open("channels.json", "r") as f:
        # json.loads() and json.dumps() are allegedly faster than json.load() and json.dump(),
        # theoretically making them better in async functions even though they still are synchronous
        # therefore, we read the file contents and then use json.loads() instead of json.load() on the file directly
        content = await f.read()
        channels = json.loads(content)
    if new_channel_id in channels:
        await interaction.response.send_message("This channel is already registered!")
        return
    else:
        channels[new_channel_id] = []
        async with aiofiles.open("channels.json", mode="w") as f:
            # same thing, you can't json.dump(f) directly
            await f.write(json.dumps(channels, indent=4))
        await interaction.response.send_message("Channel registered successfully!")
        return

@bot.tree.command(name="remove_channel", description="Removes this channel from tracking, clearing all players")
async def remove_channel(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    async with aiofiles.open("channels.json", "r") as f:
        content = await f.read()
        channels = json.loads(content)
    if channel_id not in channels:
        await interaction.response.send_message("This channel is already not registered!")
        return
    else:
        del channels[channel_id]
        async with aiofiles.open("channels.json", mode="w") as f:
            await f.write(json.dumps(channels, indent=4))
        await interaction.response.send_message("Channel removed successfully!")
        return

@bot.tree.command(name="add_player", description="Adds a player to be tracked in this channel (channel must be registered")
async def add_player(interaction: discord.Interaction, player_name: str):
    channel_id = str(interaction.channel.id)
    async with aiofiles.open("channels.json", "r") as f:
        content = await f.read()
        channels = json.loads(content)
    if channel_id not in channels:
        await interaction.response.send_message("This channel is not registered! Use /register_channel first!")

    # need to make sure this is a real player by verifying that it has a PUUID
    puuid = await get_puuid_from_riot_id(player_name)
    if puuid is None:
        await interaction.response.send_message(f"Player {player_name} not found!")
    if player_name in channels[channel_id]:
        await interaction.response.send_message(f"Player {player_name} is already being tracked in this channel!")
        return
    else:
        channels[channel_id].append(player_name)
        print(f"Adding {player_name} to {channel_id}")

    async with aiofiles.open("channels.json", mode="w") as f:
        await f.write(json.dumps(channels, indent=4))
    await interaction.response.send_message(f"{player_name} added successfully!")

@bot.tree.command(name="remove_player", description="Removes a player from being tracked in this channel (channel must be registered)")
async def remove_player(interaction: discord.Interaction, player_name: str):
    channel_id = str(interaction.channel.id)
    async with aiofiles.open("channels.json", "r") as f:
        content = await f.read()
        channels = json.loads(content)
    if channel_id not in channels:
        await interaction.response.send_message("This channel is not registered! Use /register_channel first!")

    if player_name not in channels[channel_id]:
        await interaction.response.send_message(f"Player {player_name} is already not being tracked in this channel!")
        return
    else:
        channels[channel_id].remove(player_name)
        print(f"Removing {player_name} from {channel_id}")

    async with aiofiles.open("channels.json", mode="w") as f:
        await f.write(json.dumps(channels, indent=4))
    await interaction.response.send_message(f"{player_name} removed successfully!")
