import os
from dotenv import load_dotenv
from discord_functionality import *
import logging

load_dotenv()  # Load the .env file to environment variables
discord_token = os.getenv('DISCORD_TOKEN')  # Get the token from the environment variables

# just to see any errors and such
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# bot is defined in discord_functionality.py
bot.run(discord_token, log_handler=handler, log_level=logging.DEBUG)
