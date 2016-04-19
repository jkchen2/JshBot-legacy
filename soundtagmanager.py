import json, os.path, time, random, asyncio, urllib.response, pafy, threading

from xml.dom.minidom import parseString
from mutagen.mp3 import MP3

from jshbot import servermanager, usermanager, botmanager, configmanager
from jshbot.servermanager import write_data
from jshbot.jbce import bot_exception

commands_dictionary = {'module_commands':['soundtag', 'st'],
                       'shortcut_commands':['stc', 'str', 'stl', 'sts', 'stfu'],
                       'private_module_commands':[],
                       'private_shortcut_commands':[]}
commands = []
for command_list in list(commands_dictionary.values()):
    for command in command_list:
        commands.append(command)

usage_string = """Usage:
    !soundtag [<sound name>]
              [-create|c (-private|p) <"sound name"> <"sound url">] [-remove|r <sound name>]
              [-edit|e <"sound name"> <"sound url">]
              [-edit|e -setprivate <sound name>] [-edit|e -setpublic <sound name>]
              [-list|l (user name)]
              [-search|s <sound name>]
              [-info|i <sound name>]
              [-stop|silent|silence|fu]"""

def get_formatted_usage_string():
    return "\n```\n{}\n```".format(usage_string)

help_string = """```
Description:
    Create, remove, and recall sounds by a sound tag. Soundboard!

{usage_string}
      
Aliases:
    !st
    
Shortcuts:
    !soundtag -create <"sound name"> <"sound url">
        [!stc <"sound name"> <"sound url">]
    !soundtag -remove <sound name>
        [!str <sound name>]
    !soundtag -list (user name)
        [!stl (user name)]
    !soundtag -search <sound name>
        [!sts <sound name>]
    !soundtag -stop
        [!stfu]
```""".format(usage_string=usage_string)

EXCEPT_TYPE = "Sound Tag manager"

timeout_reset_lock = threading.Lock()
timeout_goal = 0
timeout_running = False

async def timeout_disconnect():
    global timeout_goal
    global timeout_running
    
    timeout_reset_lock.acquire()
    if timeout_running:
        timeout_reset_lock.release()
        return
    timeout_reset_lock.release()
    while (True): # Loop until timeout goal reached
        timeout_reset_lock.acquire()
        timeout_running = True
        time_difference = timeout_goal - time.time()
        if time_difference <= 1:
            break;
        timeout_reset_lock.release()
        await asyncio.sleep(time_difference)
    
    timeout_running = False
    timeout_reset_lock.release()
    await stop_sounds(None, timeout=True)

def get_sound_tag_data(server_id, sound_tag_name):
    """Ensures that the given sound tag exists and return sound tag data, otherwise throw an exception."""
    try:
        return servermanager.servers_data[server_id]['sound_tags'][sound_tag_name]
    except KeyError:
        raise bot_exception(EXCEPT_TYPE, "Sound tag '{}' doesn't exist".format(sound_tag_name))

def get_sound_info(server_id, sound_tag_name):
    """Builds a string listing known information of the given sound tag."""
    sound_tag_data = get_sound_tag_data(server_id, sound_tag_name)
    author_name = usermanager.get_name(server_id, sound_tag_data['author_id'])
    to_return = """Sound tag information for {sound_tag_data[full_name]}:
```
Author: {author_name}
Private: {sound_tag_data[private]}
Hits: {sound_tag_data[hits]}
Date created: {sound_tag_data[date_created]}
Sound URL: {sound_tag_data[url]}
Type: {sound_tag_data[type]}
Length: {sound_tag_data[length]} second(s)
```""".format(author_name=author_name, sound_tag_data=sound_tag_data)
    return to_return # Placeholder if this will be modified later
    
def list_sound_tags(server_id, user_id=''):
    """Lists either all sound tags or sound tags made by a specific user."""
    initial_text = "Listing all sound tags:"
    if user_id:
        initial_text = "Listing sound tags created by {}:".format(usermanager.get_name(server_id, user_id))
    sound_tags = servermanager.servers_data[server_id]['sound_tags']
    found_list = []
    for sound_tag_name, sound_tag_data in sound_tags.items():
        if not user_id or user_id == sound_tag_data['author_id']:
            found_list.append(sound_tag_data['full_name'])
    return process_found_list(initial_text, found_list)
    
def search_sound_tags(server_id, search_text):
    """Tries to find a tag that has the search text in it."""
    initial_text = "Searching sound tags for '{}':".format(search_text)
    sound_tags = servermanager.servers_data[server_id]['sound_tags']
    found_list = [sound_tag_name for sound_tag_name in sound_tags if search_text in sound_tag_name]
    return process_found_list(initial_text, found_list)

# Helper for listing functions
def process_found_list(initial_text, found_list):
    """Helper function for search_sound_tags and list_sound_tags."""
    found_list.sort()
    list_string = ''
    for sound_tag_name in found_list:
        list_string += '{}, '.format(sound_tag_name)
    if not list_string:
        list_string = "No sound tags found!  " # Maybe I can't avoid this one.
    return "{initial_text}\n```\n{list_string}\n```\n".format(initial_text=initial_text, list_string=list_string[:-2])
    
# This function does not work. Don't use it. Or maybe it does. I dunno.
async def get_random_sound_tag(server_id, voice_channel_id, user_id):
    """Gets a random sound tag for shiggles."""
    sound_tags = servermanager.servers_data[server_id]['sound_tags']
    if len(sound_tags) == 0:
        return "No sound tags available!"
    sound_tag_name = random.choice(list(sound_tags.keys()))
    await play_sound_tag(server_id, voice_channel_id, sound_tag_name, user_id)
    return "Sound tag: {sound_tag_name}".format(sound_tag_name=sound_tag_name)

def update_sound_tag(server_id, sound_tag_name, increment_hits=False, **kwargs):
    """Updates or creates a tag in the server under the given author ID.
    
    Keyword arguments:
    increment_hits -- increments the hits counter of the tag
    user_id -- user trying to modify the tag
    author_id -- author of the tag
    duration -- how long the sound should play for
    url -- url of the audio source
    private -- whether or not the tag can only be called by the author
    hits -- how many times the tag has been called
    type -- tag type (either YouTube or direct)
    length -- how long the sound tag is in seconds
    full_name -- what the full name (with spaces) is
    """
    to_return = ''
    full_name = sound_tag_name
    sound_tag_name = sound_tag_name.replace(' ', '')
    servers_data = servermanager.servers_data
    if increment_hits: # Updating hit counter
        servers_data[server_id]['sound_tags'][sound_tag_name]['hits'] += 1
    else: # Creating or modifying a tag
        if kwargs['url'].startswith('https://www.youtube.com/') or kwargs['url'].startswith('https://youtu.be/'):
            kwargs['type'] = 'YouTube'
        else:
            kwargs['type'] = 'direct'
        
        # Check tag length
        if kwargs['type'] == 'YouTube': # Find length of YouTube video
            try:
                length = pafy.new(kwargs['url']).length
            except:
                raise bot_exception(EXCEPT_TYPE, "Invalid YouTube video")
        else: # Download file and check length
            try:
                urllib.request.urlretrieve (kwargs['url'], '{}/tempsound'.format(configmanager.data_directory))
                length = MP3('{}/tempsound'.format(configmanager.data_directory)).info.length
            except:
                raise bot_exception(EXCEPT_TYPE, "Invalid direct download file or URL")
            
        length_limit = int(configmanager.config['sound_tag_length_limit'])
        if length_limit > 0 and int(length) > length_limit:
            raise bot_exception(EXCEPT_TYPE, "Sound tags can be no longer than {} second{}".format(
                length_limit, 's' if length_limit > 1 else ''))
        kwargs['length'] = int(length)
        
        try:
            sound_tag_data = servers_data[server_id]['sound_tags'][sound_tag_name]
            try:
                check_sound_tag_access(server_id, sound_tag_data, kwargs['user_id'], need_owner=True)
            except KeyError: # user_id not found, meant to create but tag exists
                raise bot_exception(EXCEPT_TYPE, "Sound tag '{}' already exists".format(sound_tag_name))
            del kwargs['user_id'] # Don't write user_id to updated tag
            servers_data[server_id]['sound_tags'][sound_tag_name].update(kwargs)
            to_return += "Sound tag '{}' successfully modified!".format(full_name)
        except KeyError: # Tag doesn't exist. Create it.
            if configmanager.config['sound_tags_per_server'] > 0 and len(servers_data[server_id]['sound_tags']) >= configmanager.config['sound_tags_per_server']:
                raise bot_exception(EXCEPT_TYPE, "This server has hit the sound tag limit of {}".format(configmanager.config['sound_tags_per_server']))
            if 'url' not in kwargs:
                raise bot_exception(EXCEPT_TYPE, "Sound tag '{}' does not exist".format(sound_tag_name))
            if len(sound_tag_name) > 50:
                raise bot_exception(EXCEPT_TYPE, "Sound tag names cannot be larger than 50 characters long")
            if len(kwargs['url']) > 2000: # This shouldn't really happen, ever
                raise bot_exception(EXCEPT_TYPE, "Sound tag url cannot be larger than 2000 characters long (how did you do this)")
            # Edit safety
            if 'user_id' in kwargs:
                kwargs['author_id'] = kwargs['user_id']
                del kwargs['user_id']
            kwargs['full_name'] = full_name
            servers_data[server_id]['sound_tags'][sound_tag_name] = {**kwargs, 'hits':0, 'date_created':time.strftime("%c")}
            to_return += "Sound tag '{}' successfully created!".format(full_name)
    write_data()
    return to_return

def remove_sound_tag(server_id, sound_tag_name, user_id):
    """Removes the given sound tag in the server."""
    sound_tag_data = get_sound_tag_data(server_id, sound_tag_name)
    check_sound_tag_access(server_id, sound_tag_data, user_id, need_owner=True)
    servers_data = servermanager.servers_data
    del servers_data[server_id]['sound_tags'][sound_tag_name]
    write_data()
    return "Tag '{}' successfully removed!".format(sound_tag_name)
    
async def play_sound_tag(server_id, voice_channel_id, sound_tag_name, user_id):
    """Plays the sound from the given sound tag if it is available."""
    
    try:
        if servermanager.is_muted(server_id, voice_channel_id):
            raise bot_exception(EXCEPT_TYPE, "The bot is muted in this voice channel")
    except KeyError:
        raise bot_exception(EXCEPT_TYPE, "You are not in a voice channel (are you perhaps on a different server?)")
    
    sound_tag_data = get_sound_tag_data(server_id, sound_tag_name)
    check_sound_tag_access(server_id, sound_tag_data, user_id, need_owner=False)
    update_sound_tag(server_id, sound_tag_name, increment_hits=True) # Increment hits
    
    from jshbot.botmanager import client
    from jshbot.botmanager import voice_player
    global timeout_goal
    
    channel = botmanager.get_voice_channel(server_id, voice_channel_id)
    if client.voice == None or client.voice.channel != channel or not client.voice.is_connected(): # Connect to channel
        if client.voice: # Disconnect from old channel
            await client.voice.disconnect()
        client.voice = await client.join_voice_channel(channel)
        voice_player.server_id = server_id
    
    if voice_player.player is not None and voice_player.player.is_playing(): # Stop if playing
        voice_player.player.stop()
        
    if sound_tag_data['type'] == 'YouTube':
        # To prevent playlist downloads
        # 'noplaylist': True
        voice_player.player = await client.voice.create_ytdl_player(sound_tag_data['url'])
    else: # Direct download (or stream? Not sure)
        try:
            # One day, I will figure out how to stream this crap. But today is not that day.
            #response = urllib.request.urlopen(sound_tag_data['url'])
            #voice_player.player = client.voice.create_ffmpeg_player(response, use_avconv=True)
            urllib.request.urlretrieve (sound_tag_data['url'], '{}/tempsound'.format(configmanager.data_directory))
            voice_player.player = client.voice.create_ffmpeg_player('{}/tempsound'.format(configmanager.data_directory))
        except:
            raise bot_exception(EXCEPT_TYPE, "An error occurred when downloading the sound file")
    voice_player.player.start()
    
    timeout = configmanager.config['voice_timeout']
    if timeout >= 0:
        timeout_reset_lock.acquire()
        timeout_goal = time.time() + ((timeout*60) if timeout > 0 else (sound_tag_data['length']+1))
        timeout_reset_lock.release()
        await timeout_disconnect()

async def stop_sounds(server_id, timeout=False):
    """Stops all audio and disconnects the bot from the voice channel."""
    from jshbot.botmanager import client
    from jshbot.botmanager import voice_player
    if voice_player.player and voice_player.player.is_playing():
        if not timeout:
            if voice_player.server_id != server_id: # Ensure we're stopping the bot on the server it is playing at
                raise bot_exception(EXCEPT_TYPE, "The bot is not connected to this server")
        voice_player.player.stop()
        if client.voice:
            await client.voice.disconnect()
        voice_player.server_id = None
    elif client.voice.is_connected():
        if not timeout:
            if voice_player.server_id != server_id: # Ensure we're stopping the bot on the server it is playing at
                raise bot_exception(EXCEPT_TYPE, "The bot is not connected to this server")
        await client.voice.disconnect()
        if voice_player:
            voice_player.server_id = None
    elif not timeout:
        raise bot_exception(EXCEPT_TYPE, "No sound is playing")
    return "Stopping all sounds and disconnecting..."
    
# Helper security function
def check_sound_tag_access(server_id, sound_tag_data, user_id, need_owner=False):
    """Ensures that the given user is author of the tag (or a bot admin) if the tag is private, otherwise throw an exception."""
    if (sound_tag_data['private'] or need_owner) and (sound_tag_data['author_id'] != user_id and not servermanager.is_admin(server_id, user_id)):
        tag_author = usermanager.get_name(server_id, sound_tag_data['author_id'])
        if sound_tag_data['private']:
            raise bot_exception(EXCEPT_TYPE,
                "This sound tag was made private by the author, {tag_author}".format(tag_author=tag_author))
        else:
            raise bot_exception(EXCEPT_TYPE,
                "User is not the author of sound tag '{sound_tag_name}', created by {tag_author}".format(
                sound_tag_name=sound_tag_data['name'], tag_author=tag_author))

async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Gets a response from the command and parameters."""
    
    to_return = ''
    num_options = len(options)
    num_arguments = len(arguments)
    using_shortcut = command in commands_dictionary['shortcut_commands']

    # Play sounds
    if (not using_shortcut and num_options == 0 and num_arguments >= 1):
        try: # For convenience, try with both raw parameters and single argument
            if num_arguments == 1:
                await play_sound_tag(server_id, voice_channel_id, arguments[0].lower().replace(' ', ''), user_id)
                return None;
        except bot_exception:
            pass
        await play_sound_tag(server_id, voice_channel_id, arguments_blocks[0].lower().replace(' ', ''), user_id)
        return None;

    # Create sound tag
    elif (num_arguments == 2 and ((command in ['stc'] and num_options == 0) or
            (not using_shortcut and (num_options == 1 or (num_options == 2 and options[1] in ['p', 'private'])) and
            options[0] in ['c', 'create']))):
        use_private = num_options == 2 and options[1] in ['p', 'private'] # Private tag
        return update_sound_tag(server_id, sound_tag_name=arguments[0].lower(), url=arguments[1], author_id=user_id, private=use_private)

    # Remove sound tag
    elif (num_arguments >= 1 and ((command in ['str'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['r', 'remove']))):
        sound_tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return remove_sound_tag(server_id, sound_tag_name, user_id)
    
    # List sound tags
    elif ((command in ['stl'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and num_arguments <= 1 and options[0] in ['l', 'list'])):
        return list_sound_tags(server_id, user_id=usermanager.get_user_id(server_id, arguments[0]) if num_arguments == 1 else '')
    
    # Search sound tags
    elif (num_arguments >= 1 and ((command in ['sts'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['s', 'search']))):
        sound_tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return search_sound_tags(server_id, sound_tag_name)
        
    # Sound tag info
    elif not using_shortcut and num_options == 1 and num_arguments >= 1 and options[0] in ['i', 'info']:
        sound_tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return get_sound_info(server_id, sound_tag_name)
    
    # Edit sound tag
    elif not using_shortcut and (num_options in range(1,3)) and num_arguments <= 2 and options[0] in ['e', 'edit']:
        if num_options == 2 and num_arguments == 1: # Set private or public
            if options[1] == 'setpublic': # Explicit to follow a strict syntax
                return update_sound_tag(server_id, sound_tag_name=arguments[0].lower(), user_id=user_id, private=False)
            elif options[1] == 'setprivate':
                return update_sound_tag(server_id, sound_tag_name=arguments[0].lower(), user_id=user_id, private=True)
        elif num_options == 1 and num_arguments == 2: # Modify sound tag url
            return update_sound_tag(server_id, sound_tag_name=arguments[0].lower(), user_id=user_id, url=arguments[1], private=False)
    
    # Stop sounds
    elif ((command in ['stfu'] and num_arguments == 0 and num_options == 0) or
            (not using_shortcut and num_options == 1 and num_arguments == 0 and options[0] in ['stop', 'silence', 'silent', 'fu'])):
        return await stop_sounds(server_id)
    

    # Invalid command
    raise bot_exception(EXCEPT_TYPE, "Invalid syntax", get_formatted_usage_string())

