import discord
from discord.ext import commands, tasks
from riot_functionality import *
import json
from dotenv import load_dotenv
import os

load_dotenv()
guild_ids = list(map(int, os.getenv('DISCORD_GUILD_IDS').split(',')))
channel_ids = list(map(int, os.getenv('DISCORD_CHANNEL_IDS').split(',')))
guilds = []
channels = []

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def print_match_kda(riot_id, kda):
    """Prints the Riot ID and KDA in each of the given discord channels."""
    for channel in channels:
        await channel.send(f'{riot_id} has just played a game! KDA: {kda["kills"]}/{kda["deaths"]}/{kda["assists"]}')

@tasks.loop(seconds=15)
async def update_matches_loop():
    """Repeatedly checks all players for new matches, and if one is found, the bot types their KDA in the given discord channels.
    The most recent match IDs are saved in a .json file."""
    print("Checking for new matches...")
    # read .json file
    with open('most_recent_matches.json', 'r') as f:
        most_recent_matches = json.load(f)
    most_recent_matches_updated = {}
    for riot_id in riot_ids:
        puuid = get_puuid_from_riot_id(riot_id)
        match_id = get_most_recent_match(puuid)
        if riot_id not in most_recent_matches:
            kda = get_kda_from_most_recent_match(puuid, match_id)
            await print_match_kda(riot_id, kda)
        elif most_recent_matches[riot_id] != match_id:
            kda = get_kda_from_most_recent_match(puuid, match_id)
            await print_match_kda(riot_id, kda)
        most_recent_matches_updated[riot_id] = match_id
    # update the .json file
    with open("most_recent_matches.json", "w") as f:
        json.dump(most_recent_matches_updated, f, indent=4)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    guilds.clear()
    for guild_id in guild_ids:
        guild = bot.get_guild(guild_id)
        guilds.append(guild)
        print(f'Added guild: {guild.name}')
    channels.clear()
    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        channels.append(channel)
        print(f'Added channel: {channel.name}')
    try:
        synced = await bot.tree.sync()  # Sync all slash commands
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    update_matches_loop.start()

