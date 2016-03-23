import json, os.path, threading

from jshbot import configmanager, botmanager
from jshbot.configmanager import data_directory
from jshbot.jbce import bot_exception

EXCEPT_TYPE = "Server manager"

servers_data = {}
write_lock = threading.Lock()

# I hate typing        
def load_data():
    """Loads the servers.json data file into servers_data"""
    global servers_data
    print("Loading servers data...")
    with open(data_directory + '/servers.json', 'r') as servers_file:
        servers_data = json.load(servers_file)
        
# I still hate typing
def write_data():
    """Serializes the given data as servers.json."""
    write_lock.acquire()
    with open(data_directory + '/servers.json', 'w') as servers_file:
        json.dump(servers_data, servers_file, indent=4)
    write_lock.release()

def is_bot(user_id):
    """Checks if user is actually the bot itself"""
    return user_id == botmanager.client_id

def is_owner(user_id):
    """Checks if user is the owner of the bot"""
    return user_id == configmanager.config['owner_id']

def is_admin(server_id, user_id):
    """Checks if user from specified server is a bot admin."""
    return user_id in servers_data[server_id]['admins'] or is_owner(user_id) or is_bot(user_id)

def is_banned(server_id, user_id):
    """Checks if user from specified server is banned from bot interaction."""
    return user_id in servers_data[server_id]['bans']

def is_muted(server_id, channel_id):
    """Checks if the bot is muted on the specified server."""
    return servers_data[server_id]['muted'] or servers_data[server_id]['channels'][channel_id]['muted']
    
def add_ban(server_id, user_id, add=True):
    """Bans or unbans the given user."""
    if (add and is_banned(server_id, user_id)) or (not add and not is_banned(server_id, user_id)):
        raise bot_exception(EXCEPT_TYPE, "User is already {}banned".format('' if add else "un"))
    elif add and is_admin(server_id, user_id):
        raise bot_exception(EXCEPT_TYPE, "Admins cannot be banned (remove admin status first to ban)")
    if add:
        servers_data[server_id]['bans'].append(user_id)
    else:
        servers_data[server_id]['bans'].remove(user_id)
    write_data()
    return "User successfully {}banned".format('' if add else "un")

def add_admin(server_id, user_id, add=True):
    """Adds or revokes admin privileges for given user."""
    if (add and is_admin(server_id, user_id)) or (not add and not is_admin(server_id, user_id)):
        raise bot_exception(EXCEPT_TYPE, "User is already {} as an admin".format("added" if add else "removed"))
    if add:
        servers_data[server_id]['admins'].append(user_id)
    else:
        if user_id == configmanager.config['owner_id']:
            raise bot_exception(EXCEPT_TYPE, "You can't remove yourself, silly goose!")
        servers_data[server_id]['admins'].remove(user_id)
    write_data()
    return "User successfully {} as an admin".format("added" if add else "removed")

def mute_channel(server_id, channel_id, mute=True):
    """Mutes or unmutes the specified channel."""
    channel_muted = servers_data[server_id]['channels'][channel_id]['muted']
    if (mute and channel_muted) or (not mute and not channel_muted):
        raise bot_exception(EXCEPT_TYPE, "Channel is already {}muted".format('' if mute else "un"))
    servers_data[server_id]['channels'][channel_id]['muted'] = mute
    write_data()
    return "Channel successfully {}muted".format('' if mute else "un")
    
def mute_server(server_id, mute=True):
    """Mutes or unmutes the specified server."""
    server_muted = servers_data[server_id]['muted']
    if (mute and server_muted) or (not mute and not server_muted):
        raise bot_exception(EXCEPT_TYPE, "Server is already {}muted".format('' if mute else "un"))
    servers_data[server_id]['muted'] = mute
    write_data()
    return "Server successfully {}muted".format('' if mute else "un")

def update_server(server_id, **kwargs):
    """Updates server information, or adds a new server.
    
    Keyword arguments:
    name -- server name
    total_members -- how many users there are on the server
    owner -- user ID of the owner of the server, not the bot
    icon -- URL of the server's icon
    """
    server_id = str(server_id)
    try:
        servers_data[server_id].update(kwargs)
    except KeyError: # Server doesn't exist. Create it.
        servers_data[server_id] = {
            **kwargs,
            'muted':False,
            'channels':{},
            'users':{},
            'tags':{},
            'sound_tags':{},
            'bans':[],
            'admins':[]
        }
    write_data()

def update_channel(server_id, channel_id, **kwargs):
    """Updates channel information, or adds a new channel.
    
    Keyword arguments:
    name -- channel name
    position -- position of the channel in the channel list
    default -- whether or not this is the default text channel
    voice -- whether or not this is a voice channel
    """
    try:
        servers_data[server_id]['channels'][channel_id].update(kwargs)
    except KeyError: # Channel doesn't exist. Create it.
        servers_data[server_id]['channels'][channel_id] = {**kwargs, 'muted':False}
    write_data()
    
def update_user(server_id, user_id, **kwargs):
    """Updates user information, or adds a new user.
    
    Keyword arguments:
    name -- user name
    avatar -- URL of the user's avatar
    discriminator -- discriminator?????
    joined -- date the user joined
    last_seen -- date of when the user was last seen online
    last_game -- last known game the user played
    nickname -- nickname (should only be passed when bot is changing nickname)
    status -- status (same as nickname, only for bot use)
    """
    try:
        aliases = servers_data[server_id]['users'][user_id]['aliases']
        try:
            if kwargs['name'] not in aliases: # Add new name to list
                aliases.append(kwargs['name'])
                kwargs['aliases'] = aliases
        except KeyError: # No name was given - it's the bot
            pass
        if not kwargs['last_seen']: # The last seen date and game shouldn't be overwritten
            del kwargs['last_seen']
        if not kwargs['last_game']:
            del kwargs['last_game']
        servers_data[server_id]['users'][user_id].update(kwargs)
    except KeyError: # User doesn't exist. Create it.
        servers_data[server_id]['users'][user_id] = {
            **kwargs,
            'nickname':'',
            'status':'',
            'color':'',
            'friend_level':0,
            'pun_level':0,
            'repost_level':0,
            'love_level':0,
            'aliases':[kwargs['name']]
        }
    write_data()
    
# Remove user, remove channel, and remove server
def remove_server(server_id):
    """Removes specified server."""
    del servers_data[server_id]
    write_data()
    
def remove_channel(server_id, channel_id):
    """Removes specified channel."""
    del servers_data[server_id]['channels'][channel_id]
    write_data()
    
def remove_user(server_id, user_id):
    """Removes specified user."""
    del servers_data[server_id]['users'][user_id]
    write_data()
    
def get_server_info(server_id):
    """Retrieves a bundle of server information."""
    return """Server information for {server_data[name]}:
```
ID: {server_id}
Name: {server_data[name]}
Total members: {server_data[total_members]}
Muted: {server_data[muted]}
Bans: {server_data[bans]}
Admins: {server_data[admins]}
Server owner: {server_data[owner]}
Bot owner: {config[owner_id]}
Total tags: {total_tags}
Total sound tags: {total_sound_tags}
Icon: {server_data[icon]}
```""".format(server_id=server_id, server_data=servers_data[server_id], config=configmanager.config,
        total_tags=len(servers_data[server_id]['tags']), total_sound_tags=len(servers_data[server_id]['sound_tags']))

def get_channel_info(server_id, channel_id):
    """Retrieves a bundle of channel information."""
    if channel_id == 0: # No voice channel
        raise bot_exception(EXCEPT_TYPE, "You are not in a voice channel on this server")
    return """Channel information for {channel_data[name]}:
```
ID: {channel_id}
Name: {channel_data[name]}
Muted: {channel_data[muted]}
Position: {channel_data[position]}
Voice channel: {channel_data[voice]}
Default: {channel_data[default]}
```""".format(channel_id=channel_id, channel_data=servers_data[server_id]['channels'][channel_id], config=configmanager.config)

