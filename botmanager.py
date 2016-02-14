BOT_VERSION = "0.2.5 hasty alpha (Git Edition)"
BOT_DATE = "February 10th, 2015"

import discord, asyncio, sys, os.path, urllib.request

from jshbot import configmanager, servermanager, parser
from jshbot.jbce import bot_exception

# This is dumb.
class voice_player:
    def __init__(self):
        self.player = None

client = discord.Client()
voice_player = voice_player()
client_id = None

async def cycle_loop():
    while (True): # Change avatar and status if configured
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
        print("Could not find the email or password field! Please set up the config.json file.")
    
@client.async_event
def on_ready():
    # Grab client ID
    global client_id
    client_id = client.user.id

    # Set bot name and avatar if applicable
    yield from client.edit_profile(configmanager.config['password'],username=configmanager.config['bot_name'] if configmanager.config['bot_name'] else "JshBot")
    
    # Change avatar and status if configured
    if configmanager.config['cycle_avatars']:
        print("Changing avatar...")
        yield from change_avatar()
    if configmanager.config['cycle_statuses']:
        print("Changing status...")
        yield from change_status()
    
    print("Updating servers information...")
    for server in client.servers:
        update_server(server)

    yield from update_bot()

    print("---------- {} is ready! ----------".format(client.user.name))
    if configmanager.config['cycle_avatars'] or configmanager.config['cycle_statuses']:
        yield from cycle_loop()

@client.async_event
def on_message(message):

    # Check if the message is a valid command and the server or channel is not muted
    if (message.content and message.content[0] in configmanager.config['command_invokers'] and message.author.id != client.user.id): # Valid invoker from not the bot
        is_private = (type(message.channel) is discord.PrivateChannel)
        if parser.is_command(message.content.partition(' ')[0][1:].lower(), private=is_private): # Valid command
            if is_private or (not is_private and # Private - skip checks. Not private - do server checks.
                    not servermanager.is_banned(server_id=message.server.id, user_id=message.author.id) and # Author is not banned
                    (not servermanager.is_muted(server_id=message.server.id, channel_id=message.channel.id) or # Server or channel is not muted or
                    (servermanager.is_admin(message.server.id, message.author.id) and message.content[1:].startswith('admin')))): # Admin is unmuting bot
                try:
                    yield from client.send_typing(message.channel)
                    response_list = yield from parser.parse(
                        message.content,
                        message.server.id if not is_private else '0', 
                        message.channel.id if not is_private else '0',
                        message.author.id if not is_private else '0',
                        message.author.voice_channel.id if (not is_private and message.author.voice_channel) else 0, # Previously type None
                        is_private)
                    for response in response_list:
                        if response[0]:
                            yield from client.send_message(message.channel, response[0], tts=response[1])
                            asyncio.sleep(2)
                except bot_exception as e: # Something bad happened
                    yield from client.send_message(message.channel, str(e))

@client.async_event
def interrupt_broadcast(server_id, channel_id, text):
    server = discord.utils.get(client.servers, id=server_id)
    yield from client.send_message(discord.utils.get(server.channels, id=channel_id), text)

@client.async_event
def disconnect_bot():
    yield from client.logout()

def get_voice_channel(server_id, voice_channel_id):
    server = discord.utils.get(client.servers, id=server_id)
    return discord.utils.get(server.channels, id=voice_channel_id)


def check_opus(): # Check opus and load if it isn't
    pass

async def update_bot():
    nickname = configmanager.config['bot_nickname'] if len(configmanager.config['bot_nickname']) <= 50 else ''
    status = configmanager.config['bot_status'] if len(configmanager.config['bot_status']) <= 1000 else ''
    for server in client.servers:
        print("DEBUG: Updating bot in server {}".format(str(server)))
        servermanager.update_user(server.id, client_id, **{'nickname':nickname, 'status':status})
        update_user(server, server.me)

async def change_avatar():
    await client.edit_profile(configmanager.config['password'], avatar=configmanager.get_random_avatar())

async def change_status():
    await client.change_status(game=discord.Game(name=configmanager.get_random_status()), idle=False)
    
def update_server(server):
    servermanager.update_server(
        server_id=server.id,
        name=server.name,
        total_members=len(server.members),
        owner=server.owner.id,
        icon=server.icon_url)
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

def update_user(server, user):
    servermanager.update_user(
        server_id=server.id,
        user_id=user.id,
        name=user.name,
        avatar=user.avatar_url,
        discriminator=str(user.discriminator),
        joined=str(user.joined_at),
        last_game=str(user.game) if (type(user) is discord.Member and user.game is not None) else '')
                                   
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
    #print("DEBUG: Updating a member") # Prints VERY frequently
    update_user(after.server, after)
@client.async_event
def on_member_join(member):
    print("DEBUG: Member joining")
    update_server(member.server)

