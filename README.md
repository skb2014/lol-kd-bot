# lol-kd-bot

this bot tracks several selected players, collecting their KDA in recent lol matches and printing them in specified discord channels

bot commands:
/add_channel -- registers the current channel to the bot, allowing you to track players in it
/remove_channel -- unregisters the current channel, removing all attached players in the process
/add_player -- registers a player to the current channel, allowing the bot to track them and post their KDAs in the channel
/remove_player -- unregisters a player in the current channel
/list_players -- lists all currently tracked players in the current channel
/clear_all_data -- clears all channel, player, and match data from the bot's storage
