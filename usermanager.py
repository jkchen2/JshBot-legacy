import json, os.path, inspect, asyncio

from jshbot import configmanager, servermanager, botmanager
from jshbot.servermanager import write_data
from jshbot.jbce import bot_exception

commands_dictionary = {'module_commands':['user', 'u'],
                       'shortcut_commands':['userinfo', 'info', 'status', 'setstatus', 'nickname', 'nick', 'setnickname', 'setnick'],
                       'private_module_commands':[],
                       'private_shortcut_commands':[]}
commands = []
for command_list in list(commands_dictionary.values()):
    for command in command_list:
        commands.append(command)

usage_string = """Usage:
    !user [(-info|i) (user name)]
          [-status|s (user name)] [-setstatus|ss (status text)]
          [-nickname|nick|n (user name)] [-setnickname|setnick|sn (nickname)]
          [-setcolor|sc (hex color)] [-updatecolor|uc]"""

def get_formatted_usage_string():
    return "\n```\n{}\n```".format(usage_string)

help_string = """```
Description:
    Shows user information for a specified user, and allows users
    to maintain a custom status and nickname for referencing.

{usage_string}

Aliases:
    !u

Shortcuts:
    !user -info (user name)
        [!userinfo (user name)]
    !user -setstatus (status text)
        [!setstatus (status text)]
    !user -nickname (user name)
        [!nickname (user name)] [!nick (user name)]
    !user -setnickname (nickname)
        [!setnickname (nickname)] [!setnick (nickname)]
```""".format(usage_string=usage_string)

EXCEPT_TYPE = "User manager"

def get_user_id(server_id, name):
    """Gets the user ID from a readable name or nickname."""
    users_data = servermanager.servers_data[server_id]['users']
    name = name.strip()
    if name.startswith('<@') and name.endswith('>'): # Mention
        try: # Check if user exists
            users_data[name[2:-1]]
            return name[2:-1]
        except KeyError:
            pass
    discovered_already = False
    found_id = ''
    for user_id in users_data: # Iterate to find name or nickname
        if users_data[user_id]['name'] == name or users_data[user_id]['nickname'] == name:
            if not discovered_already:
                found_id = user_id
                discovered_already = True
            else:
                raise bot_exception(EXCEPT_TYPE, "Duplicate names found for '{}'! Specify user with a mention".format(name))
    if found_id:
        return found_id
    try: # Raw user ID - last resort
        users_data[name]
        return name
    except KeyError:
        raise bot_exception(EXCEPT_TYPE, "User '{}' was not found".format(name))
        
def get_info(server_id, user_id):
    """Builds a string listing known user information of given user."""
    user_data = servermanager.servers_data[server_id]['users'][user_id]
    config = configmanager.config
    permissions_text = ''
    if servermanager.is_owner(user_id): # Order important here
        permissions_text = "Bot owner"
    elif servermanager.is_bot(user_id):
        permissions_text = "Literally the bot"
    elif servermanager.is_admin(server_id, user_id):
        permissions_text = "Bot admin"
    elif servermanager.is_banned(server_id, user_id):
        permissions_text = "Banned from interaction"
    else:
        permissions_text = "Standard user"
    to_return = """User information for {user_data[name]}:
```
ID: {user_id}
Name: {user_data[name]}
Nickname: {user_data[nickname]}
Discriminator: {user_data[discriminator]}
Aliases: {user_data[aliases]}
Permissions: {permissions_text}
Joined: {user_data[joined]}
Last seen: {user_data[last_seen]}
Last played game: {user_data[last_game]}
Color: {user_data[color]}
Status: {user_data[status]}
Avatar: {user_data[avatar]}
```""".format(user_id=user_id, user_data=user_data, permissions_text=permissions_text)
    return to_return # Placeholder if this will be modified later
    
def get_name(server_id, user_id):
    """Returns the user name of the given user ID."""
    try:
        return servermanager.servers_data[server_id]['users'][user_id]['name']
    except KeyError:
        return "Non-existent"
    
def get_status(server_id, user_id):
    """Builds a string showing the status of the given user."""
    user_data = servermanager.servers_data[server_id]['users'][user_id]
    name = user_data['name']
    status = user_data['status'] if user_data['status'] else "None"
    return "{name}'s status: {status}".format(name=name, status=status)

def set_status(server_id, user_id, status_text):
    """Sets the user status as the given text."""
    if len(status_text) > 1000:
        raise bot_exception(EXCEPT_TYPE, "Status cannot be more than 1000 characters long")
    servers_data = servermanager.servers_data
    servers_data[server_id]['users'][user_id]['status'] = status_text
    write_data()
    return "Status successfully {}!".format("set" if status_text else "cleared")

def get_nickname(server_id, user_id):
    """Builds a string showing the nickname of the given user."""
    user_data = servermanager.servers_data[server_id]['users'][user_id]
    name = user_data['name']
    nickname = user_data['nickname'] if user_data['nickname'] else "None"
    return "{name}'s nickname: {nickname}".format(name=name, nickname=nickname)

def set_nickname(server_id, user_id, nickname_text):
    """Sets the user nickname as the given text."""
    if len(nickname_text) > 50:
        raise bot_exception(EXCEPT_TYPE, "Nickname cannot be more than 50 characters long")
    servers_data = servermanager.servers_data
    servers_data[server_id]['users'][user_id]['nickname'] = nickname_text
    write_data()
    return "Nickname successfully {}!".format("set" if nickname_text else "cleared")

def get_color(server_id, user_id):
    """Returns the given user's color in hex format, starting with '#'."""
    user_data = servermanager.servers_data[server_id]['users'][user_id]
    name = user_data['name']
    color = user_data['color'] if user_data['color'] else "None"
    return "{name}'s custom color: {color}".format(name=name, color=color)

async def set_color(server_id, user_id, color):
    """Gives the user the given color as a role."""
    if not botmanager.has_role_permissions(server_id): # Check bot permissions first
        raise bot_exception(EXCEPT_TYPE, "Bot must be able to manage permissions in order to change role colors.")
    if color is None:
        servermanager.servers_data[server_id]['users'][user_id]['color'] = ''
        write_data()
        await botmanager.update_color_role(server_id, user_id, None)
        return "Color successfully cleared!"
    if color.startswith('#'): # Just in case people just copy values over
        color = color[1:]
    try: # Make sure we're given a valid hex value here
        converted = int(color, 16)
    except ValueError:
        raise bot_exception(EXCEPT_TYPE, "'{}' does not appear to be a valid hex color.".format(color))
    await botmanager.update_color_role(server_id, user_id, converted)
    servermanager.servers_data[server_id]['users'][user_id]['color'] = '#{}'.format(color.upper())
    write_data()    
    return "Color successfully set!"

async def update_color(server_id, user_id):
    """Refreshes the color role so that it is on top."""
    if not botmanager.has_role_permissions(server_id):
        raise bot_exception(EXCEPT_TYPE, "Bot must be able to manage permissions in order to change role colors.")
    color = servermanager.servers_data[server_id]['users'][user_id]['color']
    if color:
        converted = int(color[1:], 16)
        await botmanager.update_color_role(server_id, user_id, converted)
    else:
        raise bot_exception(EXCEPT_TYPE, "You currently don't have a custom color!")
    return "Color successfully refreshed!"

async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Gets a response from the command and parameters."""
    
    to_return = ''
    num_options = len(options)
    num_arguments = len(arguments)
    using_shortcut = command in commands_dictionary['shortcut_commands']
    
    # User information
    if (command in ['userinfo', 'info', 'user', 'u'] and (num_options == 0 or
            (num_options == 1 and options[0] in ['i', 'info']))):
        if num_arguments == 0: # Self information
            return get_info(server_id, user_id)
        else: # Other user information
            return get_info(server_id, get_user_id(server_id, arguments[0] if num_arguments == 1 else arguments_blocks[0]))

    # User status
    elif ((command in ['status'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['s', 'status'])):
        if num_arguments == 0: # Self status
            return get_status(server_id, user_id)
        else: # Other user status
            return get_status(server_id, get_user_id(server_id, arguments[0] if num_arguments == 1 else arguments_blocks[0]))

    # User nickname
    elif ((command in ['nickname', 'nick'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['n', 'nick', 'nickname'])):
        if num_arguments == 0: # Self nickname
            return get_nickname(server_id, user_id)
        else: # Other user nickname
            return get_nickname(server_id, get_user_id(server_id, arguments[0] if num_arguments == 1 else arguments_blocks[0]))

    # Modify status
    elif ((command in ['setstatus'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['ss', 'setstatus'])):
        if num_arguments == 0: # Clear status
            return set_status(server_id, user_id, '')
        else: # Set status
            return set_status(server_id, user_id, arguments[0] if num_arguments == 1 else arguments_blocks[0])

    # Modify nickname
    elif ((command in ['setnickname', 'setnick'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['setnickname', 'setnick', 'sn'])):
        if num_arguments == 0: # Clear nickname
            return set_nickname(server_id, user_id, '')
        else: # Set nickname
            return set_nickname(server_id, user_id, arguments[0] if num_arguments == 1 else arguments_blocks[0])
    
    # Set role color
    elif (not using_shortcut and num_options == 1 and options[0] in ['setcolor', 'sc'] and num_arguments <= 1):
        if num_arguments == 0: # Clear nickname
            return await set_color(server_id, user_id, None)
        else: # Set nickname
            return await set_color(server_id, user_id, arguments[0])

    # Refresh color
    elif (not using_shortcut and num_options == 1 and options[0] in ['updatecolor', 'uc'] and num_arguments == 0):
        return await update_color(server_id, user_id)
    
    # Invalid command
    raise bot_exception(EXCEPT_TYPE, "Invalid syntax", get_formatted_usage_string())

