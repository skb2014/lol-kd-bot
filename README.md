# lol-kd-bot

this bot tracks several selected players, collecting their KDA in recent lol matches and printing them in specified discord channels

developer notes:
I'm extending what andrew was trying to do (store puuids in order to avoid potential rate limits). The bot still does seem to be very broken and I'm not sure why -- I'm getting tons of warnings regarding failure to get puuids and tracebacks involving discord stuff -- I suspect that there is something the bot is doing that is not async.

I will rework the .json files soon. DO NOT TOUCH!!