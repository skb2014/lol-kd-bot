from discord_functionality import *
import logging
import os
from dotenv import load_dotenv

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

def main():
        bot.run(discord_token, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
