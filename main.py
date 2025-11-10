import os
from dotenv import load_dotenv
from functionality import *

load_dotenv()  # Load the .env file
TOKEN = os.getenv('DISCORD_TOKEN')  # Get the token from the environment

# bot is defined in functionality.py
bot.run(TOKEN)