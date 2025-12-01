from discord_functionality import *
import logging
import os
from dotenv import load_dotenv

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

def main():
    # just to see any errors and such
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

    # bot is defined in discord_functionality.py
    bot.run(discord_token, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
