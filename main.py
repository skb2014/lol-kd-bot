from discord_functionality import *
from dotenv import load_dotenv

load_dotenv()
discord_token = getenv('DISCORD_TOKEN')

def main():
    bot.run(discord_token, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
