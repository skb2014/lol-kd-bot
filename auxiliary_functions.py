from dotenv import load_dotenv
from os import getenv
import aiohttp
import aiofiles
import json
import logging
from groq import AsyncGroq
import inspect

# logger stuff
# the idea is to have 2 different log files -- one with every single logging message from discord.py
# and one with only "higher level" log stuff which is easier to read
logger = logging.getLogger('Bot Logger')
logger.setLevel(logging.DEBUG)
full_info_handler = logging.FileHandler(filename='full_info.log', encoding='utf-8', mode='w')
full_info_handler.setLevel(logging.DEBUG)
important_stuff_handler = logging.FileHandler(filename='important_stuff.log', encoding='utf-8', mode='w')
important_stuff_handler.setLevel(logging.INFO)
logger.addHandler(full_info_handler)
logger.addHandler(important_stuff_handler)

def print_to_log(type: str, message: str):
    """Prints a message to the log file with the specified type (e.g. INFO, WARNING, DEBUG))."""
    if type not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        print_to_log("ERROR", f"Invalid log type: {type}")
        match type:
            case "DEBUG":
                level_int = logging.DEBUG
            case "INFO":
                level_int = logging.INFO
            case "WARNING":
                level_int = logging.WARNING
            case "ERROR":
                level_int = logging.ERROR
            case "CRITICAL":
                level_int = logging.CRITICAL
    logger.log(level=level_int, msg=f"{inspect.stack()[1].function} -- {message}")

async def read_json_file(filename):
    """Safely reads a JSON file and returns a dictionary."""
    try:
        async with aiofiles.open(filename, mode="r") as f:
            content = await f.read()
            # json.loads() and json.dumps() are allegedly faster than json.load() and json.dump(),
            # theoretically making them better in async functions even though they still are synchronous
            # therefore, we read the file contents and then use json.loads() instead of json.load() on the file directly
            return json.loads(content)
    except FileNotFoundError:
        print_to_log("WARNING", f"File not found: {filename}. Returning empty dict.")
        return {}
    except json.JSONDecodeError:
        print_to_log("WARNING", f"JSONDecodeError: {filename}. Returning empty dict.")
        return {}

async def write_json_file(filename, data):
    """Safely writes a dictionary to a JSON file."""
    async with aiofiles.open(filename, mode="w") as f:
        if data:
            # same thing, you can't json.dump(f) directly
            # also adding a new line character to make it look better when read in the terminal
            await f.write(json.dumps(data, indent=4) + "\n")
        # if there is no data, write an empty dictionary
        else:
            await f.write("{}\n")

async def get_http_response(url):
    """Sends a GET request to the specified URL and returns the response. Checks the status code as well."""
    async with aiohttp.ClientSession() as session:
        # the next with block automatically releases the response after it's done with it
        async with session.get(url) as response:
            response_code_errors = {
                400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 429: "Rate Limit Exceeded",
                500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"
            }
            # you do not need to await response.status as it is just an integer, not a coroutine (unlike .json() for example)
            if response.status != 200:
                print_to_log("WARNING", "Request to Riot API failed with status code {response.status} {response_code_errors[response.status]}")
                logger.warning(f"{get_http_response.__name__} -- Request to Riot API failed with status code {response.status} {response_code_errors[response.status]}")
                return None
            else:
                return await response.json()

# loading all the environment variables now
load_dotenv()

#groq
async_groq_client = AsyncGroq(api_key=getenv('GROQ_API_KEY'))