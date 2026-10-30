from discord_functionality import *

# load_dotenv() is already executed when importing riot_functionality
discord_bot_token = getenv('DISCORD_BOT_TOKEN')
testing_bot_token = getenv('TESTING_BOT_TOKEN')

def main():
    if bot.is_testing:
        bot.run(testing_bot_token, log_handler=full_info_handler, log_level=logging.DEBUG)
    else:
        bot.run(discord_bot_token, log_handler=full_info_handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
