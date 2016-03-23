import socket, time, sys, asyncio, random

from jshbot import configmanager, usermanager, servermanager, tagmanager, soundtagmanager, decider, utilities, botmanager
from jshbot.jbce import bot_exception

EXCEPT_TYPE = "Parse"
BASE_EXCEPT_TYPE = "Base command"

# These lists get filled when each module is initialized
base_commands = ['ping', 'help', 'admin']
module_commands = []
shortcut_commands = []
private_module_commands = []
private_shortcut_commands = []

help_string = """```
Hi, I'm a chat bot! I can only respond to a few commands, but they include:

!user (manage statuses, nicknames, and other user information)
!tag (create and retrieve tags, essentially a simple macro system)
!soundtag (tags but with sound)
!random (flip a coin, roll a die, choose an option, etc.)
!wikipedia (look things up on Wikipedia)
!wolframalpha (query your input through Wolfram|Alpha)
!define (define a word using Wiktionary) (not in quite yet)
!urbandefine (define a word using Urban Dictionary)

And some other utility commands...

!help (what you're reading right now)
!ping (is the bot alive? Oh, it is)
!admin (admins only)

More commands will be available eventually. Key word here is "eventually".

For more information on a command, type !help <command>```"""

multi_help_strings = {
'help_help_string' : """```
Description:
    Shows basic help information for the given command.
    
Usage:
    !help [(command)]
    
Other information:
    Legend for reading help docs:
    [] - square brackets - denote a valid parameter syntax
    <> - angle brackets - denote a user-input argument that MUST be included
    () - parenthesis - denote a user-input argument or option that is OPTIONAL
    | - vertical bars - denote an alias to the leftmost adjacent option
    "" - quotation marks - denote mandatory use of quotes if there is a space```""",
    
'ping_help_string' : """```
Description:
    Pings the bot for a response.

Usage:
    !ping [(-option1) (-option2) (-...) (argument1) (argument2) (...)]```""",
    
'admin_help_string' : """```
Description:
    Do admin things.
    
Usage:
    !admin [-ban <user name>] [-unban <user name>]
           [-add <user name>] [-remove <user name>]
           [-mute <type>] [-unmute <type>]
           [-info <type>]
           [-version]
           [-source]
           [-uptime]
           [-clear]
           [-halt]
           [-ip]
           
Other information:
    Mute type is either 'server', 'channel', or 'voicechannel'```"""
}

def add_all_commands_init():
    """Loads all of the custom module commands into the parser's command list."""
    print("Adding module commands...")
    add_commands(usermanager.commands_dictionary)
    add_commands(tagmanager.commands_dictionary)
    add_commands(decider.commands_dictionary)
    add_commands(utilities.commands_dictionary)
    add_commands(soundtagmanager.commands_dictionary)

def add_commands(commands_dictionary):
    """Adds the commands in the commands dictionary to total commands."""
    module_commands.extend(commands_dictionary['module_commands'])
    shortcut_commands.extend(commands_dictionary['shortcut_commands'])
    private_module_commands.extend(commands_dictionary['private_module_commands'])
    private_shortcut_commands.extend(commands_dictionary['private_shortcut_commands'])

def is_command(command, private=False):
    """Determines whether or not the given command is available for processing."""
    if private: # Check commands depending on whether or not we're in a private message
        return command in (base_commands + private_module_commands + private_shortcut_commands)
    else:
        return command in (base_commands + module_commands + shortcut_commands)
        
def help(command, *args):
    """Gets the help_string from each submodule by command."""
    
    # Remove leading invoker
    if command and command[0] in configmanager.config['command_invokers']:
        command = command[1:]
    
    if not command: # Just help by itself
        return help_string
    elif command in base_commands:
        return multi_help_strings['{}_help_string'.format(command)]
    elif command == 'me':
        return "Maybe later."
    elif command == 'yourself':
        return "Why, thank you!"
    elif command in usermanager.commands:
        return usermanager.help_string
    elif command in tagmanager.commands:
        return tagmanager.help_string
    elif command in soundtagmanager.commands:
        return soundtagmanager.help_string
    elif command in decider.commands:
        return decider.help_string
    elif command in utilities.commands:
        return utilities.get_help_string(command)
    return "Sorry, I couldn't find help on that."
    
async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Responds to the basic commands that are always available."""
    
    to_return = ''
    
    # Base commands (sans admin)
    if command == 'ping':
        to_return += "Pong!\nOptions: {options}\nArguments: {arguments}\nArguments blocks: {arguments_blocks}".format(
            options = str(options),
            arguments = str(arguments),
            arguments_blocks = str(arguments_blocks))
    elif command == 'help':
        if len(arguments) > 1:
            raise bot_exception(BASE_EXCEPT_TYPE, "You can only get help on one command")
        to_return += help(arguments[0] if len(arguments) == 1 else '')
    
    # Admin commands
    elif command == 'admin' and len(options) == 1 and not is_private:
        if not is_admin:
            raise bot_exception(BASE_EXCEPT_TYPE, "You must be an admin or the bot owner for these commands")
        if len(arguments) == 1 and not is_private:
            if options[0] in ['ban', 'unban']: # All checks here are explicit to enforce strict syntax
                to_return += servermanager.add_ban(server_id, usermanager.get_user_id(server_id, arguments[0]), add=(options[0] == 'ban'))
            elif options[0] in ['add', 'remove']:
                if not servermanager.is_owner(user_id):
                    raise bot_exception(BASE_EXCEPT_TYPE, "You must be the bot owner for this command")
                to_return += servermanager.add_admin(server_id, usermanager.get_user_id(server_id, arguments[0]), add=(options[0] == 'add'))
            elif options[0] in ['mute', 'unmute']:
                to_mute = options[0] == 'mute'
                if arguments[0] in ['channel', 'voicechannel']:
                    to_return += servermanager.mute_channel(server_id, channel_id if arguments[0] == 'channel' else voice_channel_id, mute=to_mute)
                elif arguments[0] == 'server':
                    to_return += servermanager.mute_server(server_id, mute=to_mute)
            elif options[0] == 'info':
                if arguments[0] in ['channel', 'voicechannel']:
                    to_return += servermanager.get_channel_info(server_id, channel_id if arguments[0] == 'channel' else voice_channel_id)
                elif arguments[0] == 'server':
                    to_return += servermanager.get_server_info(server_id)
        elif len(arguments) == 0:
            if options[0] == 'version':
                to_return += '**`{version}`** ({date})'.format(version=botmanager.BOT_VERSION, date=botmanager.BOT_DATE)
            elif options[0] == 'ip':
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80)) # Thanks Google, you da real MVP
                ret = s.getsockname()[0]
                s.close()
                to_return += "Local IP: " + ret
            elif options[0] == 'halt':
                if not servermanager.is_owner(user_id):
                    raise bot_exception(BASE_EXCEPT_TYPE, "You must be the bot owner for this command")
                print("Halting execution...")
                if not is_private:
                    await botmanager.interrupt_broadcast(server_id, channel_id, "Going down...")
                await botmanager.disconnect_bot()
                await asyncio.sleep(2)
                sys.exit()
            elif options[0] == 'source':
                to_return += random.choice([
                    "It's shit. I'm sorry.", "You want to see what the Matrix is like?",
                    "Script kiddie level stuff in here.", "Beware the lack of PEP 8 guidelines inside!",
                    "Snarky comments inside and out.", "The last codebender. And he's shit at it.",
                    "Years down the road, this will all just be a really embarrassing but funny joke.",
                    "Made with ~~love~~ pure hatred.", "At least he's using version control."])
                to_return += "\nhttps://github.com/TheJsh/JshBot"
            elif options[0] == 'clear':
                to_return += '```\n'
                for i in range(0, 80):
                    to_return += '.\n'
                to_return += random.choice([
                    "Think twice before scrolling up.", "clear ver {}".format(botmanager.BOT_VERSION),
                    "Can you find the one comma?", "Are people watching? If so, best not to scroll up.",
                    "Don't worry, just censorship doing its thing.", "This is why we can't have nice things.",
                    "The only one who can spam is ME.", "That made me feel a bit queasy...",
                    "We need a better content filter. 18+ checks, maybe?", "You ANIMALS. At least I'm not one.",
                    "Scroll up if you want to be on a list.", "I'll bet the NSA will have a fun time scrolling up.",
                    "So much wasted space...", "This is pretty annoying, huh? Well TOO BAD.",
                    "No time to delete!"])
                to_return += '```\n'
            elif options[0] == 'ca':
                await botmanager.change_avatar()
                to_return += "Avatar changed"
            elif options[0] == 'cs':
                await botmanager.change_status()
                to_return += "Status changed"
            elif options[0] == 'uptime':
                uptime_total_seconds = int(time.time()) - botmanager.bot_turned_on_precise
                uptime_struct = time.gmtime(uptime_total_seconds)
                days = int(uptime_total_seconds / 86400)
                hours = uptime_struct.tm_hour
                minutes = uptime_struct.tm_min
                seconds = uptime_struct.tm_sec
                return "The bot has been on since **{initial}**\n{days} days\n{hours} hours\n{minutes} minutes\n{seconds} seconds".format(
                        initial=botmanager.bot_turned_on_date, days=days, hours=hours, minutes=minutes, seconds=seconds)
                
            
    if to_return:
        return to_return
    else: # Invalid command
        raise bot_exception(BASE_EXCEPT_TYPE, "Invalid syntax")
        
    return to_return
    
async def parse(text, server_id, channel_id, author_id, voice_channel_id, is_private=False):
    """Parses the text to separate the command, options, and arguments, and passes them into the apropriate modules."""
    is_admin = servermanager.is_admin(server_id, author_id) if not is_private else False
    text_partition, _, text = text[1:].partition(' ') # Remove invoker character
    text = text.strip()
    raw_parameters = text # Used for some functions (mostly shortcuts)
    command = text_partition.lower()
    option_invoker = configmanager.config['option_invoker']
    
    # Look for options
    options = []
    while text.startswith(option_invoker):
        option_partition, _, text = text[1:].partition(' ')
        text = text.strip()
        if option_partition:
            options.append(option_partition)

    # Look for arguments
    arguments = []
    arguments_blocks = []
    while text:
        if len(arguments_blocks) < 4:
            arguments_blocks.append(text)
        if text.startswith('"'): # Search for end quote
            try:
                text = text[1:]
                closed_quote_index = 0
                next_quote_index = text[closed_quote_index:].index('"') # Maybe use do while?
                while text[closed_quote_index + next_quote_index - 1] == '\\': # Run until proper closed quote found
                    closed_quote_index += next_quote_index
                    text = text[:closed_quote_index - 1] + text[closed_quote_index:]
                    next_quote_index = text[closed_quote_index:].index('"')
            except ValueError:
                raise bot_exception(EXCEPT_TYPE, "An argument has an unclosed quote")
            closed_quote_index += next_quote_index
            if closed_quote_index > 0: # No null argument
                to_append = text[:closed_quote_index].strip()
                if to_append: # No empty string
                    arguments.append(to_append)
                text = text[closed_quote_index + 1:].strip()
            else: # If there is a null argument, remove it
                text = text[2:].strip()
        else: # Search for next space
            argument_partition, _, text = text.partition(' ')
            arguments.append(argument_partition)
            text = text.strip()
    
    # Debug printing
    print("DEBUG:\n{}\n{}\n{}\n{}\n------".format(command, options, arguments, arguments_blocks))
    
    # Get proper response
    to_return = ['', False] # Text response, TTS
    get_response_function = help # Function placeholder
    
    # TODO: See if there is an object representation of modules
    if command in tagmanager.commands: # Tag manager
        get_response_function = getattr(tagmanager, 'get_response')
    elif command in soundtagmanager.commands: # Sound tag manager
        get_response_function = getattr(soundtagmanager, 'get_response')
    elif command in usermanager.commands: # User manager
        get_response_function = getattr(usermanager, 'get_response')
    elif command in decider.commands: # Decider
        get_response_function = getattr(decider, 'get_response')
    elif command in utilities.commands: # Utilities
        get_response_function = getattr(utilities, 'get_response')
    elif command in base_commands: # Base commands
        get_response_function = get_response
    
    if get_response_function != help: # Found a response function
        to_return[0] = await get_response_function(
            command,
            options,
            arguments,
            arguments_blocks,
            raw_parameters,
            server_id,
            channel_id,
            voice_channel_id,
            author_id,
            is_admin,
            is_private)
    
    else:
        to_return[0] += "Sorry, I can't seem to do that right now. You should never see this, by the way. What is most likely going on is that you are hallucinating this error."
        
    if to_return[0] is not None and len(to_return[0]) > 1900: # Split responses up if it is too long
        to_return[0] = "```\n***Looks like the response is very large. It might look a little messed up because it's gettin' chopped up.***```\n" + to_return[0][:1900]
        
    return to_return
    
