import json, os.path, time, random, asyncio

from jshbot import servermanager, usermanager, configmanager
from jshbot.servermanager import write_data
from jshbot.jbce import bot_exception

commands_dictionary = {'module_commands':['tag', 't'],
                       'shortcut_commands':['tc', 'tr', 'tl', 'ts'],
                       'private_module_commands':[],
                       'private_shortcut_commands':[]}
commands = []
for command_list in list(commands_dictionary.values()):
    for command in command_list:
        commands.append(command)

usage_string = """Usage:
    !tag [<tag name>]
         [-create|c (-private|p) <"tag name"> <tag text>] [-remove|r <tag name>]
         [-edit|e <"tag name"> <tag text>]
         [-edit|e -setprivate <tag name>] [-edit|e -setpublic <tag name>]
         [-list|l (user name)]
         [-search|s <tag name>]
         [-info|i <tag name>]"""

def get_formatted_usage_string():
    return "\n```\n{}\n```".format(usage_string)

help_string = """```
Description:
    Create, remove, and recall tags (or macros) for commonly used links or phrases

{usage_string}
      
Aliases:
    !t
    
Shortcuts:
    !tag -create <"tag name"> <tag text>
        [!tc <"tag name"> <tag text>]
    !tag -remove <tag name>
        [!tr <tag name>]
    !tag -list (user name)
        [!tl (user name)]
    !tag -search <tag name>
        [!ts <tag name>]
```""".format(usage_string=usage_string)

EXCEPT_TYPE = "Tag manager"

def get_tag_data(server_id, tag_name):
    """Ensures that the given tag exists and return tag data, otherwise throw an exception."""
    try:
        return servermanager.servers_data[server_id]['tags'][tag_name]
    except KeyError:
        raise bot_exception(EXCEPT_TYPE, "Tag '{}' doesn't exist".format(tag_name))

def get_info(server_id, tag_name):
    """Builds a string listing known information of given tag."""
    tag_data = get_tag_data(server_id, tag_name)
    author_name = usermanager.get_name(server_id, tag_data['author_id'])
    to_return = """Tag information for {tag_data[full_name]}:
```
Author: {author_name}
Private: {tag_data[private]}
Hits: {tag_data[hits]}
Date created: {tag_data[date_created]}
```""".format(author_name=author_name, tag_data=tag_data)
    return to_return # Placeholder if this will be modified later
    
def list_tags(server_id, user_id=''):
    """Lists either all tags or tags made by a specific user."""
    initial_text = "Listing all tags:"
    if user_id:
        initial_text = "Listing tags created by {}:".format(usermanager.get_name(server_id, user_id))
    tags = servermanager.servers_data[server_id]['tags']
    found_list = []
    for tag_name, tag_data in tags.items():
        if not user_id or user_id == tag_data['author_id']:
            found_list.append(tag_data['full_name'])
    return process_found_list(initial_text, found_list)
    
def search_tags(server_id, search_text):
    """Tries to find a tag that has the search text in it."""
    initial_text = "Searching tags for '{}':".format(search_text)
    tags = servermanager.servers_data[server_id]['tags']
    found_list = [tag_name for tag_name in tags if search_text in tag_name]
    return process_found_list(initial_text, found_list)

# Helper for listing functions
def process_found_list(initial_text, found_list):
    """Helper function for search_tags and list_tags."""
    found_list.sort()
    list_string = ''
    #list_string += '{}, '.format(tag_name) for tag_name in found_list
    for tag_name in found_list:
        list_string += '{}, '.format(tag_name)
    if not list_string:
        list_string = "No tags found!  " # Horrible! WOSH U CODE ALREADY
    return "{initial_text}{block}{list_string}{block}".format(initial_text=initial_text, block='\n```\n', list_string=list_string[:-2])
    
def get_random_tag(server_id, user_id):
    """Gets a random tag for shiggles."""
    tags = servermanager.servers_data[server_id]['tags']
    if len(tags) == 0:
        return "No tags available!"
    tag_name = random.choice(list(tags.keys()))
    return "Tag: {tag_name}\n{tag_text}".format(tag_name=tag_name, tag_text=get_tag_text(server_id, tag_name, user_id))

def update_tag(server_id, tag_name, increment_hits=False, **kwargs):
    """Updates or creates a tag in the server under the given author ID.
    
    Keyword arguments:
    increment_hits -- increments the hits counter of the tag
    user_id -- user trying to modify the tag
    author_id -- author of the tag
    tag_text -- text to go along with the tag
    private -- whether or not the tag can only be called by the author
    hits -- how many times the tag has been called
    full_name -- what the full name (with spaces) is (never passed in)
    """
    to_return = ''
    full_name = tag_name
    tag_name = tag_name.replace(' ', '')
    servers_data = servermanager.servers_data
    if increment_hits: # Updating hit counter
        servers_data[server_id]['tags'][tag_name]['hits'] += 1
    else: # Creating or modifying a tag
        try: # Modify a tag
            tag_data = servers_data[server_id]['tags'][tag_name]
            try:
                check_tag_access(server_id, tag_data, tag_name, kwargs['user_id'], need_owner=True)
            except KeyError: # user_id not found, meant to create but tag exists
                raise bot_exception(EXCEPT_TYPE, "Tag '{}' already exists".format(tag_name))
            del kwargs['user_id'] # Don't write user_id to updated tag
            servers_data[server_id]['tags'][tag_name].update(kwargs)
            to_return += "Tag '{}' successfully modified!".format(full_name)
        except KeyError: # Tag doesn't exist. Create it.
            if configmanager.config['tags_per_server'] > 0 and len(servers_data[server_id]['tags']) >= configmanager.config['tags_per_server']:
                raise bot_exception(EXCEPT_TYPE, "This server has hit the tag limit of {}".format(configmanager.config['tags_per_server']))
            if 'tag_text' not in kwargs:
                raise bot_exception(EXCEPT_TYPE, "Tag '{}' does not exist".format(tag_name))
            if len(tag_name) > 50:
                raise bot_exception(EXCEPT_TYPE, "Tag names cannot be larger than 50 characters long")
            if len(kwargs['tag_text']) > 2000: # This shouldn't really happen, ever
                raise bot_exception(EXCEPT_TYPE, "Tag text cannot be larger than 2000 characters long")
            # Edit safety
            if 'user_id' in kwargs:
                kwargs['author_id'] = kwargs['user_id']
                del kwargs['user_id']
            kwargs['full_name'] = full_name
            servers_data[server_id]['tags'][tag_name] = {**kwargs, 'hits':0, 'date_created':time.strftime("%c")}
            to_return += "Tag '{}' successfully created!".format(full_name)
    write_data()
    return to_return

def remove_tag(server_id, tag_name, user_id):
    """Removes the given tag in the server."""
    tag_data = get_tag_data(server_id, tag_name)
    check_tag_access(server_id, tag_data, tag_name, user_id, need_owner=True)
    servers_data = servermanager.servers_data
    del servers_data[server_id]['tags'][tag_name]
    write_data()
    return "Tag '{}' successfully removed!".format(tag_name)
    
def get_tag_text(server_id, tag_name, user_id):
    """Gets the tag text from the tag name, if user is allowed."""
    tag_data = get_tag_data(server_id, tag_name)
    check_tag_access(server_id, tag_data, tag_name, user_id, need_owner=False)
    update_tag(server_id, tag_name, increment_hits=True) # Increment hits
    return tag_data['tag_text']
    
# Helper security function
def check_tag_access(server_id, tag_data, tag_name, user_id, need_owner=False):
    """Ensures that the given user is author of the tag (or a bot admin) if the tag is private, otherwise throw an exception."""
    if (tag_data['private'] or need_owner) and (tag_data['author_id'] != user_id and not servermanager.is_admin(server_id, user_id)):
        tag_author = usermanager.get_name(server_id, tag_data['author_id'])
        if need_owner:
            raise bot_exception(EXCEPT_TYPE, "User is not the author of tag '{tag_name}', created by {tag_author}".format(tag_name=tag_name, tag_author=tag_author))
        else:
            raise bot_exception(EXCEPT_TYPE, "The tag '{tag_name}' was made private by the author, {tag_author}".format(tag_name=tag_name, tag_author=tag_author))

async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Gets a response from the command and parameters."""
    
    to_return = ''
    num_options = len(options)
    num_arguments = len(arguments)
    using_shortcut = command in commands_dictionary['shortcut_commands']
    
    # Get tag text
    if (not using_shortcut and num_options == 0 and num_arguments >= 1):
        try: # For convenience, try with both raw parameters and single argument
            if num_arguments == 1:
                return get_tag_text(server_id, arguments[0].lower().replace(' ', ''), user_id)
        except bot_exception:
            pass
        return get_tag_text(server_id, raw_parameters.lower().replace(' ', ''), user_id)

    # Create tag
    elif (num_arguments >= 2 and ((command in ['tc'] and num_options == 0) or
            (not using_shortcut and (num_options == 1 or (num_options == 2 and options[1] in ['p', 'private'])) and options[0] in ['c', 'create']))):
        use_private = num_options == 2 and options[1] in ['p', 'private'] # Private tag
        tag_text = arguments[1] if num_arguments == 2 else arguments_blocks[1]
        return update_tag(server_id, tag_name=arguments[0].lower(), tag_text=tag_text, author_id=user_id, private=use_private)

    # Remove tag
    elif (num_arguments >= 1 and ((command in ['tr'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['r', 'remove']))):
        tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return remove_tag(server_id, tag_name, user_id)
    
    # List tags
    elif ((command in ['tl'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['l', 'list'])):
        user_name = arguments[0] if num_arguments == 1 else (arguments_blocks[0] if num_arguments > 1 else '')
        return list_tags(server_id, user_id=usermanager.get_user_id(server_id, user_name) if num_arguments >= 1 else '')
    
    # Search tags
    elif (num_arguments >= 1 and ((command in ['ts'] and num_options == 0) or
            (not using_shortcut and num_options == 1 and options[0] in ['s', 'search']))):
        tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return search_tags(server_id, tag_name)
        
    # Tag info
    elif not using_shortcut and num_options == 1 and num_arguments >= 1 and options[0] in ['i', 'info']:
        tag_name = (arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()).replace(' ', '')
        return get_info(server_id, tag_name)
    
    # Edit tag
    elif not using_shortcut and (num_options in range(1,3)) and num_arguments >= 1 and options[0] in ['e', 'edit']:
        if num_options == 2: # Set private or public
            tag_name = arguments[0].lower() if num_arguments == 1 else arguments_blocks[0].lower()
            if options[1] == 'setpublic': # Explicit to follow a strict syntax
                return update_tag(server_id, tag_name=tag_name, user_id=user_id, private=False)
            elif options[1] == 'setprivate':
                return update_tag(server_id, tag_name=tag_name, user_id=user_id, private=True)
        elif num_options == 1 and num_arguments >= 2: # Modify tag text
            tag_text = arguments[1] if num_arguments == 2 else arguments_blocks[1]
            return update_tag(server_id, tag_name=arguments[0].lower(), user_id=user_id, tag_text=tag_text, private=False)

    # Invalid command
    raise bot_exception(EXCEPT_TYPE, "Invalid syntax", get_formatted_usage_string())

