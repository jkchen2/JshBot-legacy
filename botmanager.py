BOT_VERSION = "0.2.8 alpha"
BOT_DATE = "March 22nd, 2016"

import discord, asyncio, sys, os.path, urllib.request, time

from jshbot import configmanager, servermanager, parser
from jshbot.jbce import bot_exception

# This is necessary?
class voice_player:
    def __init__(self):
        self.player = None
        self.server_id = None

client = discord.Client()
voice_player = voice_player()
client_id = None
bot_turned_on_date = time.strftime("%c")
bot_turned_on_precise = int(time.time())

last_responses_dictionary = {}

async def cycle_loop():
    """Cycles through the avatars and statuses."""
    while (True):
        await asyncio.sleep(configmanager.config['cycle_period']*60*60)
        if configmanager.config['cycle_avatars']:
            print("Changing avatar...")
            await change_avatar()
        if configmanager.config['cycle_statuses']:
            print("Changing status...")
            await change_status()
        await update_bot()

def initialize():
    """Initializes the bot given the client."""
    global client
    print("Bot initializing! Fingers crossed...")
    path = os.path.split(os.path.realpath(__file__))[0][:-7]
    print("Setting path to {}".format(path))
    configmanager.set_bot_directory(path)
    configmanager.load_config()
    servermanager.load_data()
    parser.add_all_commands_init()
    # TODO: Check for opus here
    print("Logging in the client...")
    try:
        client.run(configmanager.config['email'], configmanager.config['password'])
    except KeyError:
        print("=== ERROR: Could not find the email or password field! Please set up the config.json file.")
    
@client.async_event
def on_ready():
    # Grab client ID
    global client_id
    client_id = client.user.id

    # Set bot name
    try:
        yield from client.edit_profile(
                configmanager.config['password'],
                username=configmanager.config['bot_name'] if configmanager.config['bot_name'] else "JshBot")
    except KeyError:
        print("=== ERROR: Could not find the bot name field! Please set up the config.json file.")
    except:
        print("=== ERROR: Failed to change bot name (limit 2 name changes per hour)")
    
    # Change avatar and status if configured
    if configmanager.config['cycle_avatars']:
        print("Changing avatar...")
        yield from change_avatar()
    if configmanager.config['cycle_statuses']:
        print("Changing status...")
        yield from change_status()
    
    # Change color if configured
    try:
        if configmanager.config['bot_color']:
            print("Setting bot color on each server...")
            for server in client.servers:
                if has_role_permissions(server.id):
                    yield from update_color_role(
                            server.id,
                            client.user.id,
                            int(configmanager.config['bot_color'], 16))
                else:
                    print("=== ERROR: Bot doesn't have role permissions in server {}".format(str(server)))
    except ValueError:
        print("=== ERROR: Could not update the color of the bot (is it in the correct format?)")
    
    print("Updating servers information...")
    for server in client.servers:
        update_server(server, update_all=True)

    yield from update_bot()

    print("---------- {} is ready! ----------".format(client.user.name))
    if configmanager.config['cycle_avatars'] or configmanager.config['cycle_statuses']:
        yield from cycle_loop()

async def get_response(message, send_typing=True):
    """Gets a response. Split up so messages can be edited."""
    # Check if the message is a valid command and the server or channel is not muted
    if (message.content and message.content[0] in configmanager.config['command_invokers'] and message.author.id != client.user.id): # Valid invoker from not the bot
        is_private = (type(message.channel) is discord.PrivateChannel)
        if parser.is_command(message.content.partition(' ')[0][1:].lower(), private=is_private): # Valid command
            if is_private or (not is_private and # Private - skip checks. Not private - do server checks.
                    not servermanager.is_banned(server_id=message.server.id, user_id=message.author.id) and # Author is not banned
                    (not servermanager.is_muted(server_id=message.server.id, channel_id=message.channel.id) or # Server or channel is not muted or
                    (servermanager.is_admin(message.server.id, message.author.id) and message.content[1:].startswith('admin')))): # Admin is unmuting bot
                try:
                    global last_responses_dictionary
                    if send_typing:
                        await client.send_typing(message.channel)
                    return await parser.parse(
                        message.content,
                        message.server.id if not is_private else '0', 
                        message.channel.id if not is_private else '0',
                        message.author.id if not is_private else '0',
                        message.author.voice_channel.id if (not is_private and message.author.voice_channel) else 0, # Previously type None
                        is_private)
                except bot_exception as e: # Something bad happened
                    return [str(e), False]
    return ['', False]

@client.async_event
def on_message(message):
    response = yield from get_response(message)
    if response[0]:
        message_reference = yield from client.send_message(message.channel, response[0], tts=response[1])
        if configmanager.config['edit_timeout'] > 0:
            last_responses_dictionary[message.id] = message_reference
            yield from asyncio.sleep(configmanager.config['edit_timeout'])
            if last_responses_dictionary[message.id].edited_timestamp is None: # Message was not edited
                del last_responses_dictionary[message.id]

@client.async_event
def on_message_edit(before, after):
    try:
        message_reference = last_responses_dictionary[before.id]
    except KeyError: # The bot did not previous respond to this message
        return
    print("DEBUG: Message was edited. Bot is editing response.")
    response = yield from get_response(after, send_typing=False)
    if response[0]:
        message_reference = yield from client.edit_message(message_reference, response[0])
    else:
        yield from client.delete_message(message_reference)
    if configmanager.config['edit_timeout'] > 0:
        last_responses_dictionary[before.id] = message_reference
        yield from asyncio.sleep(configmanager.config['edit_timeout'])
        if last_responses_dictionary[before.id].edited_timestamp == message_reference.edited_timestamp: # Message was not edited
            del last_responses_dictionary[before.id]

@client.async_event
def interrupt_broadcast(server_id, channel_id, text):
    server = discord.utils.get(client.servers, id=server_id)
    yield from client.send_message(discord.utils.get(server.channels, id=channel_id), text)

@client.async_event
def disconnect_bot():
    yield from client.logout()

async def update_color_role(server_id, user_id, color):

    # Get server and user, along with role name
    server = discord.utils.get(client.servers, id=server_id)
    user = discord.utils.get(server.members, id=user_id)
    role_name = 'c_{}'.format(user_id)
    
    # Remove role if it exists, even if it's not used
    current_role = discord.utils.get(user.roles, name=role_name)
    if current_role is not None:
        await client.delete_role(server, current_role)
    if color is not None: # Assign new color
        new_role = await client.create_role(
            server,
            colour=discord.Color(color),
            name=role_name)
        
        # Finally, assign new role to user
        await client.add_roles(user, new_role)
    

def has_role_permissions(server_id):
    server = discord.utils.get(client.servers, id=server_id)
    for role in server.me.roles:
        if role.permissions.manage_roles:
            return True
    return False

def get_voice_channel(server_id, voice_channel_id):
    server = discord.utils.get(client.servers, id=server_id)
    return discord.utils.get(server.channels, id=voice_channel_id)

def check_opus(): # Check opus and load if it isn't
    pass # Oh look, we loaded Opus. Champagne for everyone!

async def update_bot():
    nickname = configmanager.config['bot_nickname'] if len(configmanager.config['bot_nickname']) <= 50 else ''
    status = configmanager.config['bot_status'] if len(configmanager.config['bot_status']) <= 1000 else ''
    for server in client.servers:
        #print("DEBUG: Updating bot in server {}".format(str(server)))
        servermanager.update_user(server.id, client_id, 
                **{'nickname':nickname, 'status':status, 'last_seen':'behind you', 'last_game':'',
                        'color':'#{}'.format(configmanager.config['bot_color'])})
        update_user(server, server.me)

async def change_avatar():
    await client.edit_profile(configmanager.config['password'], avatar=configmanager.get_random_avatar())

async def change_status():
    await client.change_status(game=discord.Game(name=configmanager.get_random_status()), idle=False)
    
def update_server(server, update_all=False):
    servermanager.update_server(
            server_id=server.id,
            name=server.name,
            total_members=len(server.members),
            owner=server.owner.id,
            icon=server.icon_url)
    if update_all:
        for channel in server.channels:
            update_channel(server, channel)
        for user in server.members:
            update_user(server, user)

def update_channel(server, channel):
    servermanager.update_channel(
            server_id=server.id,
            channel_id=channel.id,
            name=channel.name,
            position=channel.position,
            default=channel.is_default,
            voice=str(channel.type) == 'voice')

def update_user(server, user, update_seen=False):
    last_game = ''
    last_seen = ''
    if type(user) is discord.Member and user.game is not None:
        last_game = str(user.game)
    if update_seen:
        last_seen = time.strftime("%c")
    servermanager.update_user(
            server_id=server.id, user_id=user.id, name=user.name,
            avatar=user.avatar_url, discriminator=str(user.discriminator),
            joined=str(user.joined_at), last_game=last_game, last_seen=last_seen)
                                   
def remove_server(server):
    servermanager.remove_server(server.id)
def remove_channel(server, channel):
    servermanager.remove_channel(server.id, channel.id)
def remove_user(server, user):
    servermanager.remove_user(server.id, user.id)
    
@client.async_event # Channels
def on_channel_delete(channel):
    print("DEBUG: Removing a channel")
    servermanager.remove_channel(channel.server.id, channel.id)
@client.async_event
def on_channel_create(channel):
    print("DEBUG: Adding a channel")
    update_channel(channel.server, channel)
@client.async_event
def on_channel_update(before, after):
    print("DEBUG: Updating a channel")
    update_channel(after.server, after)
@client.async_event # Servers
def on_server_remove(server):
    print("DEBUG: Removing a server")
    servermanager.remove_server(server.id)
@client.async_event
def on_server_update(server):
    print("DEBUG: Updating a server")
    update_server(server)
@client.async_event
def on_server_join(server):
    print("DEBUG: Joining a server")
    update_server(server)
@client.async_event # Users
def on_member_remove(member):
    print("DEBUG: Removing a member")
    servermanager.remove_user(member.server.id, member.id)
    update_server(member.server)
@client.async_event
def on_member_update(before, after):
    #print("DEBUG: Updating a member ({})".format(after.name)) # Prints VERY frequently
    update_user(after.server, after, update_seen=True)
@client.async_event
def on_member_join(member):
    print("DEBUG: Member joining")
    update_server(member.server)

