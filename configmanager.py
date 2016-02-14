import json, os.path, urllib.request, random

from jshbot import jbce
from jshbot.jbce import bot_exception

from pprint import pprint

EXCEPT_TYPE = "Configuration manager"

config = {}

# Defaults to the current working directory of the Python environment
bot_directory = ''
config_directory = 'config'
data_directory = 'data'

def set_bot_directory(directory=''):
    """Sets the directory of the initial start.py to find config and data files."""
    bot_directory = directory
    default_text = '{}'
    # Create config  and data files if they don't exist
    config_directory = bot_directory + '/config'
    data_directory = bot_directory + '/data'
    if not os.path.exists(config_directory):
        os.makedirs(config_directory)
    if not os.path.isfile(config_directory + '/config.json'):
        with open(config_directory + '/config.json', 'w') as config_file:
            config_file.write('{}')
    if not os.path.isfile(config_directory + '/avatars.txt'):
        with open(config_directory + '/avatars.txt', 'w') as avatars_file: pass
    if not os.path.isfile(config_directory + '/statuses.txt'):
        with open(config_directory + '/statuses.txt', 'w') as statuses_file: pass
    # Data files
    if not os.path.exists(data_directory):
        os.makedirs(bot_directory + '/data')
    if not os.path.isfile(data_directory + '/servers.json'):
        with open(data_directory + '/servers.json', 'w') as servers_file:
            servers_file.write('{}')

# TODO: Remove after migrating
def get_config():
    """Returns a dictionary of the configuration file."""
    with open(bot_directory + 'config/config.json', 'r') as config_file:
        return json.load(config_file)
        
def load_config():
    """Sets the configuration file."""
    global config
    print("Loading config file...")
    with open(bot_directory + 'config/config.json', 'r') as config_file:
        config = json.load(config_file)

def print_config():
    """DEBUG"""
    global config
    print("Pretty printing config:")
    pprint(config)
    
def get_random_avatar():
    """Returns a bytes-like file from a downloaded image specified in avatars.txt."""

    if os.stat(config_directory + '/avatars.txt').st_size > 0:
        image_url = random.choice(list(open(config_directory + '/avatars.txt')))
        try: # Make sure the file can actually be downloaded
            urllib.request.urlretrieve(image_url, data_directory + '/tempavatar')
            with open(data_directory + '/tempavatar', 'rb') as avatar:
                return avatar.read()
        except:
            raise bot_exception(EXCEPT_TYPE, "Failed to download avatar from url {}\n(ensure that the url is a direct link to a PNG or JPG image, or try uploading the image to a better host, such as imgur.com or mixtape.moe)".format(image_url))
    else:
        raise bot_exception(EXCEPT_TYPE, "Failed to update the avatar because the avatars.txt file is empty")

def get_random_status():
    """Returns a random status from the statuses.txt file."""
    
    if os.stat(config_directory + '/statuses.txt').st_size > 0:
        with open(config_directory + '/statuses.txt', 'r') as statuses_file:
            return str(random.choice(list(statuses_file))).rstrip()
    else:
        raise bot_exception(EXCEPT_TYPE, "Failed to update the status because the statuses.txt file is empty")

