from discord_functionality import *

# load_dotenv() is already executed when importing riot_functionality
discord_token = getenv('DISCORD_TOKEN')

def main():
    bot.run(discord_token, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
