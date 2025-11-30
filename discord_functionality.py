import discord
from discord.ext import commands, tasks
from riot_functionality import *
import json

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

guilds = []
channels = []
testing_guild_id = 1288788236608737281
bchat_guild_id = 837511484589735936
bottesting_channel_id = 1443525957271945267
botshit_channel_id = 854026996560560208

@tasks.loop(seconds=5)
async def infinite_loop():
    (print('hello'))
    with open('most_recent_matches.json', 'r') as f:
        most_recent_matches = json.load(f)
    temp_dict = {}
    for riot_id in riot_IDs:
        match_id = get_most_recent_match(get_puuid_from_riot_id(riot_id))
        temp_dict[riot_id] = match_id
        if riot_id not in most_recent_matches:
            for channel in channels:
                print(channel)
                kda = get_kda_from_most_recent_match(get_puuid_from_riot_id(riot_id))
                await channel.send(f'{riot_id} has just played a game! KDA: {kda['kills']}/{kda['deaths']}/{kda['assists']}')
        elif most_recent_matches[riot_id] != match_id:
            for channel in channels:
                print(channel)
                kda = get_kda_from_most_recent_match(get_puuid_from_riot_id(riot_id))
                await channel.send(f'{riot_id} has just played a game! KDA: {kda['kills']}/{kda['deaths']}/{kda['assists']}')
    # overwrite most recent matches
    with open("most_recent_matches.json", "w") as f:
        json.dump(temp_dict, f, indent=4)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    guilds.clear()
    guilds.append(bot.get_guild(testing_guild_id))
    guilds.append(bot.get_guild(bchat_guild_id))
    channels.clear()
    channels.append(bot.get_channel(bottesting_channel_id))
    channels.append(bot.get_channel(botshit_channel_id))
    try:
        synced = await bot.tree.sync()  # Sync all slash commands
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    infinite_loop.start()

@bot.tree.command(name='hello', description='Says hello!', guilds=guilds)
async def hello_command(interaction: discord.Interaction):
    await interaction.response.send_message('Hello There!')


