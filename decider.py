import json, random, asyncio

from jshbot import usermanager, tagmanager, soundtagmanager
from jshbot.jbce import bot_exception

commands_dictionary = {'module_commands':['random', 'rand', 'r'],
                       'shortcut_commands':['roll', 'flip', 'pick'],
                       'private_module_commands':['random', 'rand', 'r'],
                       'private_shortcut_commands':['roll', 'flip', 'pick']}
commands = []
for command_list in list(commands_dictionary.values()):
    for command in command_list:
        commands.append(command)

usage_string = """Usage:
    !random [(<"minimum number"> <"maximum number">)]
            [-tag|t] [-soundtag|st]
            [-flip|f]
            [-roll|r|dice|d (faces)]
            [-pick|p|choose|c|decide|d|fluky|f <"choice 1"> <"choice 2"> ("choice 3") ("...")]"""

def get_formatted_usage_string():
    return "\n```\n{}\n```".format(usage_string)

help_string = """```
Description:
    Generate random results, including numbers, dice rolls, coin flips, and contextual decisions.

{usage_string}
      
Aliases:
    !rand !r
    
Shortcuts:
    !random -roll (faces)
        [!roll (faces)]
    !random -flip
        [!flip]
    !random -pick <"choice 1"> <"choice 2"> ("choice 3") ("...")
        [!pick <"choice 1"> <"choice 2"> ("choice 3") ("...")]
```""".format(usage_string=usage_string)

EXCEPT_TYPE = "Decider"

def flip_coin(is_private=True, **kwargs):
    """Flips a coin and returns a text result.
    
    Keyword arguments:
    is_private -- determines whether a name should be obtained
    server_id -- ID of the server requesting the flip
    user_id -- ID of the user requesting the flip
    """
    to_return = "You" if is_private else usermanager.get_name(kwargs['server_id'], kwargs['user_id'])
    to_return += " flipped a coin: It's "
    if (random.randint(0,1) == 0):
        to_return += "heads! Ⓗ "
    else:
        to_return += "tails! Ⓣ"
    return to_return

def roll_die(faces=6, is_private=True, **kwargs):
    """Rolls a 6 sided die unless specified. Same keyword arguments as flip_coin."""
    try: # Typecheck faces value
        faces = int(faces)
    except:
        raise bot_exception(EXCEPT_TYPE, "Input is not a valid integer")
    to_return = "You" if is_private else usermanager.get_name(kwargs['server_id'], kwargs['user_id'])
    if (faces == 1):
        to_return += " rolled a {}. Just kidding.".format(random.randint(1,2147483647))
    elif (faces <= 0):
        return "Look, I can't roll something that breaks the laws of physics."
    else: # Valid roll
        to_return += " rolled a {}.".format(random.randint(1, faces))
    return to_return

def get_random_number(minimum=1, maximum=100, is_private=True, **kwargs):
    """Obtains a random number with the specified minimum and maximum values. Same keyword arguments as flip_coin."""
    try: # Typecheck minimum and maximum values
        minimum = int(minimum)
        maximum = int(maximum)
    except:
        raise bot_exception(EXCEPT_TYPE, "Inputs are not valid integers")
    if (minimum == maximum):
        return "You must think you're really clever."
    if (minimum > maximum):
        minimum, maximum = maximum, minimum
    return "{identifier} got {result}.".format(
        identifier="You" if is_private else usermanager.get_name(kwargs['server_id'], kwargs['user_id']),
        result=random.randint(minimum, maximum))

def pick_choice(*args):
    """Picks a choice from the arguments list."""
    if len(args) <= 1 or args[1:] == args[:-1]:
        return "You're, uh... not giving me much to work with here."
    return "I pick {}.".format(random.choice(args))

async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Gets a response from the command and parameters."""
    
    to_return = ''
    num_options = len(options)
    num_arguments = len(arguments)
    using_shortcut = command in commands_dictionary['shortcut_commands']

    # Flip a coin
    if ((command in ['flip'] and num_options == 0 and num_arguments == 0) or
            (not using_shortcut and num_options == 1 and num_arguments == 0 and options[0] in ['f', 'flip'])):
        public_info = {}
        if not is_private: # Bundle server and user ID if we need a name
            public_info = {'server_id':server_id, 'user_id':user_id}
        return flip_coin(is_private=is_private, **public_info)

    # Roll dice
    elif ((command in ['roll'] and num_arguments <= 1) or
            (not using_shortcut and num_options == 1 and num_arguments <= 1 and options[0] in ['r', 'roll', 'd', 'dice'])):
        public_info = {}
        if not is_private:
            public_info = {'server_id':server_id, 'user_id':user_id}
        return roll_die(faces=arguments[0] if num_arguments == 1 else 6, is_private=is_private, **public_info)

    # Pick a choice
    elif ((command in ['pick'] and num_options == 0 and num_arguments >= 0) or
            (not using_shortcut and num_options == 1 and num_arguments >= 0 and options[0] in ['p', 'pick', 'c', 'choose', 'd', 'decide', 'f', 'fluky'])):
        return pick_choice(*arguments) # Number of arguments is checked in function
        
    # Get a random tag lolwat
    elif not using_shortcut and num_options == 1 and num_arguments == 0 and options[0] in ['t', 'tag']:
        return tagmanager.get_random_tag(server_id, user_id)

    # Get a random tag uw0t
    elif not using_shortcut and num_options == 1 and num_arguments == 0 and options[0] in ['st', 'soundtag']:
        return await soundtagmanager.get_random_sound_tag(server_id, voice_channel_id, user_id)
    
    # Get random number
    elif not using_shortcut and num_options == 0 and (num_arguments == 0 or num_arguments == 2):
        public_info = {}
        if not is_private:
            public_info = {'server_id':server_id, 'user_id':user_id}
        if num_arguments == 2:
            return get_random_number(minimum=arguments[0], maximum=arguments[1], is_private=is_private, **public_info)
        else:
            return get_random_number(is_private=is_private, **public_info)

    # Invalid command
    raise bot_exception(EXCEPT_TYPE, "Invalid syntax", get_formatted_usage_string())

