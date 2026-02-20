# lol-kd-bot

### Description


This bot tracks League of Legends players, posting their KDAs (and some other information) in the discord channels (which they are registered to) whenever they finish playing a match. You can also discuss League of Legends related topics with the bot, and also "investigate" players to see if they play "winning league" or "losing league" in their last match.


### Bot Commands


/add_channel -- registers the current channel to the bot, allowing you to track players in it

/remove_channel -- unregisters the current channel, removing all attached players in the process

/add_player -- registers a player to the current channel, allowing the bot to track them and post their KDAs in the channel

/remove_player -- unregisters a player in the current channel

/list_players -- lists all currently tracked players in the current channel

/investigate_player -- checks a player's most recent match to see if they played winning/losing league
// NOTE: you can also invoke this by replying to an automated KDA message and asking the bot to judge the player

/clear_all_data -- clears all channel, player, and match data from the bot's storage


### Project Structure


    jsons (NOT TRACKED) -- folder which contains json files storing the data
    
        - channels.json -- stores all tracked channels and which players are being tracked in those channels
    
        - matches_data_raw.json -- stores all raw match data directly from the Riot API for all matches that at least one player has as their most recent match
    
        - players.json -- stores all tracked players, their most recent match_id, and which channels they're in
    
    logs (NOT TRACKED) -- folder which contains the log files generatd by the bot
    
        - full_info.log -- records all bot activity, even the debug status messages from discord
    
        - important_stuff.log -- records only what is explicitly logged in the code
    
    prompts -- folder which contains the system prompts used by the groq LLM
    
        - prompt_1.txt -- the prompt which asks the bot to perform the check to determine whether a user is requesting a KDA check
    
        - prompt_2.txt -- the prompt which outlines how the bot is supposed to converse with users 
    
        - prompt_3.txt -- the prompt which tells the bot to analyze match data
    
    .env (NOT TRACKED) -- contains API keys and such
    
    .gitignore -- specifies which files should not be tracked by git
    
    requirements.txt -- contains the required packages 
    
    auxiliary_functions.py -- contains functions used frequently by the bot and loads some variables
    
    riot_functionality.py -- the file which contains the code for interacting with the Riot API and processing match data
    
    discord_functionality.py -- the file which contains the code for all the discord functions and commands (including conversing with the LLM)
    
    testing_bot.py (NOT TRACKED) -- a file which I have on my personal laptop that runs a separte "testing" bot with the same (or slightly modified) functionality as the main bot
    
    main.py -- the file which runs the lol-kd-tracker bot