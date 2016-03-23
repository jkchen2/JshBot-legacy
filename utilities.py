import wikipedia, wolframalpha, urllib.parse, urllib.request, json, requests, asyncio

from jshbot import configmanager
from jshbot.jbce import bot_exception

commands_dictionary = {'module_commands':['wikipedia', 'wiki', 'w', 'wolframalpha',
                                          'wolfram', 'wa', 'shorten', 'shortenurl',
                                          'rehost', 'define', 'def', 'urbandefine',
                                          'udef'],
                       'shortcut_commands':['swiki', 'sw', 'swolfram', 'swa', 'sdef'],
                       'private_module_commands':['wikipedia', 'wiki', 'w', 'wolframalpha',
                                                  'wolfram', 'wa', 'shorten', 'shortenurl',
                                                  'rehost', 'define', 'def', 'urbandefine',
                                                  'udef'],
                       'private_shortcut_commands':['swiki', 'sw', 'swolfram', 'swa', 'sdef']}
commands = []
for command_list in list(commands_dictionary.values()):
    for command in command_list:
        commands.append(command)

# Specifically for the utiliies module
wikipedia_commands = ['wikipedia', 'wiki', 'w', 'swiki', 'sw']
wolfram_alpha_commands = ['wolframalpha', 'wolfram', 'wa', 'swolfram', 'swa']
urban_dictionary_commands = ['urbandefine', 'udef']
wiktionary_commands = ['define', 'def', 'sdef']
shortener_commands = ['shortenurl', 'shorten']
rehoster_commands = ['rehost']

multi_usage_strings = {
'wikipedia_usage_string' : """Usage:
    !wikipedia [(-simple|s|url) <query>]""",

'wolfram_alpha_usage_string' : """Usage:
    !wolframalpha [(-simple|s) <query>]
                  [(-results=<number of results>) <query>]""",

'urban_dictionary_usage_string' : """Usage:
    !urbandefine [<word>]""",

'wiktionary_usage_string' : """Usage:
    !define [(-simple|s) <word>]""",

'shortener_usage_string' : """Usage:
    !shortenurl [<url>]""",

'rehoster_usage_string' : """Usage:
    !rehost [<image url>]"""
}

def get_formatted_usage_string(command):
    return "\n```\n{}\n```".format(multi_usage_strings['{}_usage_string'.format(command)])

multi_help_strings = {
'wikipedia_help_string' : """```
Description:
    Returns a Wikipedia result if the query can be found, or just the URL if it is requested.

{wikipedia_usage_string}
      
Aliases:
    !wiki !w
    
Shortcuts:
    !wikipedia -simple <query>
        [!swiki <query>] [!sw <query>]
```""".format(wikipedia_usage_string=multi_usage_strings['wikipedia_usage_string']),

'wolfram_alpha_help_string' : """```
Description:
    Returns a Wolfram|Alpha result if the query can be found, or just the first result if it is requested.
    Number of results can be specified, but defaults to 3.

{wolfram_alpha_usage_string}
      
Aliases:
    !wolfram !wa
    
Shortcuts:
    !wolframalpha -simple <query>
        [!swolfram <query>] [!swa <query>]
```""".format(wolfram_alpha_usage_string=multi_usage_strings['wolfram_alpha_usage_string']),

'urban_dictionary_help_string' : """```
Description:
    Returns the first definition of the specified word from urbandictionary.com.

{urban_dictionary_usage_string}

Aliases:
    !udef
```""".format(urban_dictionary_usage_string=multi_usage_strings['urban_dictionary_usage_string']),

'wiktionary_help_string' : """```
Description:
    Returns a definition of the specified word from wiktionary.org.

{wiktionary_usage_string}

Aliases:
    !def

Shortcuts:
    !define -simple <word>
        [!sdef <word>]
```""".format(wiktionary_usage_string=multi_usage_strings['wiktionary_usage_string']),

'shortener_help_string' : """```
Description:
    Shortens the given URL to the goo.gl format.

{shortener_usage_string}

Aliases:
    !shorten
```""".format(shortener_usage_string=multi_usage_strings['shortener_usage_string']),

'rehoster_help_string' : """```
Description:
    Reuploads the given image URL to Imgur for faster and more reliable hosting.

{rehoster_usage_string}
```""".format(rehoster_usage_string=multi_usage_strings['rehoster_usage_string'])
}

WIKIPEDIA_EXCEPTION = "Wikipedia query"
WOLFRAM_ALPHA_EXCEPTION = "Wolfram|Alpha query"
URBAN_DICTIONARY_EXCEPTION = "Urban Dictionary query"
WIKTIONARY_EXCEPTION = "Wiktionary query"
SHORTENER_EXCEPTION = "URL shortener processor"
REHOSTER_EXCEPTION = "Imgur rehoster"

EXCEPT_TYPE = "General" # This should never be displayed

def wikipedia_query(query, simple_result=False):
    if not query:
        return "Try searching for *something* next time, knucklehead."
    try:
        page = wikipedia.page(query, auto_suggest=True)
        if simple_result: # Just return the url of the found page
            return page.url
        else: # Return the first ~500 characters of the summary
            title = page.title
            summary = page.summary
            for i in range(0, (len(summary) if len(summary) < 500 else 500) - 1):
                if summary[i] == '=' and summary[i+1] == '=':
                    summary = summary[0:i]
                    break;
            if len(summary) >= 500:
                summary = summary[0:500]
                summary += ' ...*`[truncated]`*'
            return "***```{title}```***\n{summary}".format(title=title, summary=summary)
    except wikipedia.exceptions.PageError:
        raise bot_exception(WIKIPEDIA_EXCEPTION, 
            "Page doesn't exist. Trying for some suggestions...", '```{}```'.format(
            (wikipedia.suggest(query) if wikipedia.suggest(query) is not None else "None")))
    except wikipedia.exceptions.DisambiguationError as tp: # Try to get list of suggestions
        suggestions = wikipedia.search(query, results=5)
        if len(suggestions) > 0:
            formatted_suggestions = '```\n'
            for suggestion in suggestions:
                formatted_suggestions += '{}\n'.format(suggestion)
            formatted_suggestions += '```'
            raise bot_exception(WIKIPEDIA_EXCEPTION, "Query is too ambiguous. Here are some suggestions:", formatted_suggestions)
        else:
            raise bot_exception(WIKIPEDIA_EXCEPTION, "Query is too ambiguous. No suggestions found.")

def wolfram_alpha_query(query, simple_result=False, results_limit=2):
    """Returns a query result from Wolfram|Alpha, either in full text or just one result."""
    
    if results_limit < 1:
        raise bot_exception(EXCEPT_TYPE, "Invalid number of results (1 to 8)")
    results_limit += 1 # Increment to account for input result, which doesn't really count
    
    query_url = "Query URL: http://www.wolframalpha.com/input/?i={}\n".format(urllib.parse.quote_plus(query))
    to_return = ''
    try:
        query_result = wolframalpha.Client(configmanager.config['wolfram_api_key']).query(query)
    except:
        raise bot_exception(WOLFRAM_ALPHA_EXCEPTION, "Wolfram|Alpha is not configured for use right now, sorry")
    result_root = query_result.tree.getroot()
    
    # Error handling
    if result_root.get('success') == 'false':
        try: # 
            suggestion = result_root.find('didyoumeans').find('didyoumean').text
        except Exception as e: # TODO: Get proper exception type
            print("Something bad happened to the query:\n" + str(e)) # DEBUG
            raise bot_exception(WOLFRAM_ALPHA_EXCEPTION, "Wolfram|Alpha could not interpret your query\n{}".format(query_url))
        raise bot_exception(WOLFRAM_ALPHA_EXCEPTION,
            "Wolfram|Alpha could not interpret your query. Trying for first suggestion '{}'...".format(suggestion),
            wolfram_alpha_query(suggestion))
    elif result_root.get('timedout'):
        if len(query_result.pods) == 0:
            raise bot_exception(WOLFRAM_ALPHA_EXCEPTION, "Query timed out", query_url)
        elif not simple_result:
            to_return += "```\nWarning: query timed out but returned some results:```\n"
    elif len(query_result.pods) == 0:
        raise bot_exception(WOLFRAM_ALPHA_EXCEPTION, "No result given (general error)", query_url)
    
    number_of_results = 0
    # Format answer
    if simple_result: # Return a straight, single answer
        if len(list(query_result.results)) > 0:
            to_return += list(query_result.results)[0].text + "\n"
        else: # No explicit 'result' was found
            try:
                to_return += "Closest result:\n{}\n".format(list(query_result.pods)[1].text)
            except IndexError:
                to_return += "No valid result returned. This is a bug! Avert your eyes!"
            except Exception as e: # This shouldn't happen, really
                print("Something bad happened to the query (returning simple result):\n" + str(e)) # DEBUG
                raise bot_exception(WOLFRAM_ALPHA_EXCEPTION, "Wolfram|Alpha is now dead. Nice work.")
    else: # Full answer, up to 1800 characters long
        for pod in list(query_result.pods):
            for sub_pod in list(pod.node):
                image = sub_pod.find('img')
                if image is not None:
                    to_return += "{pod_title}: {image_url}\n".format(pod_title=pod.__dict__['title'], image_url=image.get('src'))
                    number_of_results += 1
                    if len(to_return) > 1800: # We're getting a very large result. Truncate.
                        to_return += "```\nWarning: truncating very long result here...```\n"
                        break
            if number_of_results >= results_limit:
                break
        to_return += query_url
    
    return to_return

def urban_dictionary_definition(query):
    parsed_query = urllib.parse.quote_plus(query)
    query_url = 'http://www.urbandictionary.com/define.php?term={}'.format(parsed_query)
    try:
        urban_data = requests.get('http://api.urbandictionary.com/v0/define?term={}'.format(parsed_query)).json()
    except:
        raise bot_exception(URBAN_DICTIONARY_EXCEPTION, "Failed to get definition from Urban Dictionary", query_url)
    if urban_data['result_type'] != 'exact': # Probably 'no_result', but this is safer
        raise bot_exception(URBAN_DICTIONARY_EXCEPTION, "The query '{}' returned no results".format(query), query_url)
    definition = urban_data['list'][0]
    rating = '{}% rating (:thumbsup:{} | :thumbsdown:{})'.format(
            int(100*definition['thumbs_up'] / (definition['thumbs_up'] + definition['thumbs_down'])),
            definition['thumbs_up'], definition['thumbs_down'])
    # Truncate definition and examples so that they aren't so freakin' long
    if len(definition['definition']) > 500:
        definition['definition'] = '{} ...*`[truncated]`*'.format(definition['definition'][:499])
    if len(definition['example']) > 500:
        definition['example'] = '{} ...`[truncated]`'.format(definition['example'][:499])
    elif len(definition['example']) == 0:
        definition['example'] = 'No example provided'
    return '***```{definition[word]}```***\n{definition[definition]}\n\n*{definition[example]}*\n\n*{query_url}* - {rating}'.format(
            definition=definition, rating=rating, query_url=query_url)

def wiktionary_definition(query): #TODO: Implement
    return ''

def get_command_info(command):
    if command in wikipedia_commands: # TODO There has to be a better way to do this...
        command = 'wikipedia'
        EXCEPT_TYPE = WIKIPEDIA_EXCEPTION
    elif command in wolfram_alpha_commands:
        command = 'wolfram_alpha'
        EXCEPT_TYPE = WOLFRAM_ALPHA_EXCEPTION
    elif command in urban_dictionary_commands:
        command = 'urban_dictionary'
        EXCEPT_TYPE = URBAN_DICTIONARY_EXCEPTION
    elif command in wiktionary_commands:
        command = 'wiktionary'
        EXCEPT_TYPE = WIKTIONARY_EXCEPTION
    elif command in shortener_commands:
        command = 'shortener'
        EXCEPT_TYPE = SHORTENER_EXCEPTION
    elif command in rehoster_commands:
        command = 'rehoster'
        EXCEPT_TYPE = REHOSTER_EXCEPTION
    
    return [command, EXCEPT_TYPE]

def get_help_string(command):
    try:
        return multi_help_strings['{}_help_string'.format(get_command_info(command)[0])]
    except KeyError:
        return 'Help for command {} was not found. This shouldn\'t happen!'.format(command)

async def get_response(command, options, arguments, arguments_blocks, raw_parameters, server_id, channel_id, voice_channel_id, user_id, is_admin, is_private):
    """Gets a response from the command and parameters."""
    
    to_return = ''
    num_options = len(options)
    num_arguments = len(arguments)
    using_shortcut = command in commands_dictionary['shortcut_commands']
    
    # Wikipedia query
    if command in wikipedia_commands and ((num_options == 1 and options[0] in ['s', 'simple', 'url']) or num_options == 0):
        simple_result = False
        if using_shortcut or num_options == 1:
            simple_result = True
        return wikipedia_query(arguments[0] if num_arguments == 1 else arguments_blocks[0], simple_result=simple_result)
    
    # Wolfram|Alpha query
    elif (command in wolfram_alpha_commands and num_arguments >= 1 and 
            ((num_options == 1 and (options[0].startswith('results=') or options[0] in ['s', 'simple']) or num_options == 0))):
        simple_result = False
        results_limit = 2
        if using_shortcut or (num_options == 1 and options[0] in ['s', 'simple']):
            simple_result = True
        elif num_options == 1: # Result number specification
            results_limit = int(options[0][8:])
        wolfram_query = arguments[0] if num_arguments == 1 else arguments_blocks[0]
        return wolfram_alpha_query(wolfram_query, simple_result=simple_result, results_limit=results_limit)
    
    # Urban Dictionary definition
    elif command in urban_dictionary_commands and num_arguments >= 1 and num_options == 0:
        urban_query = arguments[0] if num_arguments == 1 else arguments_blocks[0]
        return urban_dictionary_definition(urban_query)
    
    # Invalid command
    command, EXCEPT_TYPE = get_command_info(command)
    raise bot_exception(EXCEPT_TYPE, "Invalid syntax", get_formatted_usage_string(command))

