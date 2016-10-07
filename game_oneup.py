import logging, time
from collections import defaultdict, Counter
import asyncio
from datetime import datetime, timedelta
from math import floor
import hangups
import operator, functools
import plugins
import inflect
p = inflect.engine()


logger = logging.getLogger(__name__)

def _initialise(bot):
    # plugins.register_handler(_handle_oneup, "message")
    plugins.register_user_command(["oneup"])
    # bot.register_shared("game_OneUp.oneup", oneup)

def humandate(timestamp):    
    d = datetime.fromtimestamp(timestamp).strftime('%m-%d-%Y %H:%M')
    return d

def format_timedelta(value):
    """format a timedelta into something human readable"""
    d = {"days": value.days}
    d["hours"], rem = divmod(value.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)    
    fmt=''
    for x in ['days', 'hours', 'minutes']:
        if d[x]>0:
            fmt+="{%s} %s, " % (x,p.singular_noun(x,d[x]))
    if fmt != '':
        fmt += 'and '
    fmt+='{seconds} %s' % p.singular_noun('seconds',d['seconds'])
    return fmt.format(**d)   

def timeleft(deadline, lasttime):
    tdelta = (lasttime + timedelta(hours=deadline)) - time.time()
    timeleft = format_timedelta(tdelta)
    return timeleft

def nextsunday(today):
    timeleft = today + timedelta(days=-today.weekday(), weeks=1, hours=-today.hour, minutes=-today.minute, seconds=-today.second, microseconds=-today.microsecond)
    return timeleft

def mulimit(value, multiplier, increase):
    """figures which is greater of the MU multiplier or increase"""
    goal = max(value*multiplier, value+increase)
    return goal

def oneup(bot, event, *args):
    """OneUp contest for increasing MU counts
Usage:
/bot oneup
    Lists the standings for the current round
/bot oneup add <mu> <optional player name>
    Adds mu score for you (or other player if specified
/bot oneup rules
    Print the rules for OneUp
/bot oneup round
    Prints the entries for the current round
/bot oneup history
    Prints the result of all past rounds
/bot oneup score
    Prints a tally of winners of past rounds
/bot oneup delete
    [Admin only] Deletes the last entry of the current round
    """
    mu_multiplier=1.5
    mu_increase=200
    mu_minimum=100
    mu_maximum=500
    today = datetime.now()
    deadline = nextsunday(today)

    # bot.send_message_parsed(event.conv,_("Plugin working."))
    parameters = list(args)

    message = ""
    oneup_mem = bot.conversation_memory_get(event.conv_id, "oneup")
    if oneup_mem:
        print("oneup_mem exists")
    else:
        bot.conversation_memory_set(event.conv_id, "oneup", { "games": [], "history": [] })
        oneup_mem = bot.conversation_memory_get(event.conv_id, "oneup")
    # if not bot.memory.exists(['conv_data', event.conv_id, 'oneup']):
    #     bot.memory.set_by_path(['conv_data', event.conv_id, 'oneup'], {"games": []})

    mem_games = oneup_mem['games']
    if not 'history' in oneup_mem:
        oneup_mem['history']= []
    mem_history = oneup_mem['history']

    # print(mem_games)       

    message = "Error with command.  Please check syntax."

    # command with no parameters

    if (not parameters) or (parameters[0] == "current"):
        if not mem_games:
            message="New Game! Be the first to OneUp with at least %s MUs and less than %s MUs!" % (mu_minimum, mu_maximum)
        else:
            current = mem_games[-1]
            if today > nextsunday(datetime.fromtimestamp(current['time'])):
                message="New Game! Be the first to OneUp with at least %s MUs and less than %s MUs!" % (mu_minimum, mu_maximum)
            else:    
                message = "The current OneUp is at %i MUs scored by %s." % ( current['mus'] , current['user'])
                message += "\nThe next field must be no greater than %i MUs." % mulimit(current['mus'], mu_multiplier, mu_increase)
                message += "\nAgents: You have %s left to OneUp this field!" % format_timedelta(deadline-today)
        bot.send_message_parsed(event.conv_id, message)
        return
    
    # add or submit command 

    if parameters[0] in ["add", "submit"] and len(parameters) > 1:
        # if int(parameters[1]).isdigit():
        try:
            mus = int(parameters[1])
            # convert a datetime to a timestamp
            entrytime = today.timestamp()
            # convert a timestamp to a datetime
            # datetime.fromtimestamp(entrytime)
            total = mus
            if mem_games:
                current = mem_games[-1]
                if 'total' in current:
                    total += current['total']

                if current['time']:
                    if today > nextsunday(datetime.fromtimestamp(current['time'])):
                        """New Game Starts"""
                        if mus < mu_minimum or mus > mu_maximum:
                            message="I'm sorry, the first OneUp field of each round must be at least %s MUs and no greater than %s MUs. %s" % (mu_minimum, mu_maximum, type(mus))
                            bot.send_message_parsed(event.conv_id, message)
                            return
                        game=current['game']+1
                        mem_history += [ current ]
                        mem_games = []


                    else:
                        """Enter a new round on current game"""
                        game=current['game']
                        limit = mulimit(current['mus'], mu_multiplier, mu_increase)
                        if mus < mu_minimum or mus <= current['mus'] or mus>= limit:
                            message="I'm sorry, the next OneUp field must be greater than the previous entry of %i MUs no greater than %i MUs." % (current['mus'],limit)
                            bot.send_message_parsed(event.conv_id, message)
                            return
            else:
                if mus < mu_minimum or mus > mu_maximum:
                    message="I'm sorry, the first OneUp field of each round must be at least %s MUs and no greater than %s MUs." % (mu_minimum, mu_maximum)
                    bot.send_message_parsed(event.conv_id, message)
                    return
                game=1
                current = {}

            if len(parameters) > 2:
                user = " ".join(parameters[2:])
            else:
                user =  event.user.full_name
            fields = len(mem_games) + 1
            game_entry = {'game': game, 'user': user, 'mus': mus, 'total': total, 'fields': fields, 'time':entrytime};
            mem_games += [ game_entry ]
            bot.conversation_memory_set(event.conv_id, "oneup", {'games': mem_games, 'history': mem_history})
            print(mem_games)
            print(mem_history)
            message = "Added score for {} of {} MUs at {}.".format(user, mus, humandate(entrytime))
        except ValueError:
            pass

    elif parameters[0] == "score":
        get_values = functools.partial(map, operator.itemgetter('user'))
        message = "Oneup Scoreboard"
        scores = dict(Counter(get_values(mem_history)))
        message = "OneUp Scoreboard"
        for user, value in scores.items():
            message += "\n%s has won %s %s" % (user, value, p.plural_noun("game", value))
        
    elif parameters[0] == "history":
        """lists the history of all past games"""
        message = "Game History"
        try:
            for g in mem_history:
                message += "\n%s) %s MUs by %s on %s" % (g['game'], g['mus'], g['user'], humandate(g['time']))
        except IndexError:
            message = "No history entries, yet"
            pass
    
    
    elif parameters[0] == "round":
        """lists the entries for the current round"""
        message = "Round History"
        x = 0
        try:      
            for g in mem_games:
                x += 1
                message += "\n%s) %s MUs by %s on %s" % (x, g['mus'], g['user'], humandate(g['time']))
                
        except IndexError:
            message = "No entries for this week, yet"
            pass
    # elif parameters[0] == "myscore":
    #     message = parameters[0]
    # elif parameters[0] == "history":
    #     """lists the history of all past games"""
    #     message = "Game History"
    #     try:
    #         for g in mem_history:
    #             message += "\n%s) %s MUs by %s on %s" % (g['game'], g['mus'], g['user'], humandate(g['time']))
    #     except IndexError:
    #         message = "No history entries, yet"
    #         pass
    
    elif parameters[0] == "delete":
        """Deletes last game entry
        /bot oneup delete"""
        admins_list = bot.get_config_suboption(event.conv_id, 'admins')
        if event.user_id.chat_id in admins_list:
            try:
                mem_games.pop()
                bot.conversation_memory_set(event.conv_id, "oneup", {'games': mem_games, 'history': mem_history})
                message = "Last entry has been deleted."
            except IndexError:
                message = "No more entries for this week.  New Game!"
        else:
            message = "I'm afraid I can't do that.  That command is for Admins only"

    elif parameters[0] == "debug":
        """Deletes last game entry
        /bot oneup delete"""
        admins_list = bot.get_config_suboption(event.conv_id, 'admins')
        if event.user_id.chat_id in admins_list:
            try:
                message = "mem_games\n %s \n" % mem_games
                message += "mem_history\n %s \n" % mem_history
                message += "memory.json\n %s \n" % bot.conversation_memory_get(event.conv_id, "oneup")
                message += "mu_minimum: %s\n" %type(mu_minimum)
                message += "mu_maximum: %s\n" %type(mu_maximum)

            except IndexError:
                message = "No more entries for this week.  New Game!"
        else:
            message = "I'm afraid I can't do that.  That command is for Admins only"
            
    elif parameters[0] == "rules":
        message = "Rules: The goal of the game is to incrementally build a larger field within Ames compared to the current OneUp field leader. \n The rules are as follows: You cannot use a jarvis in order to clear another person's field to make way for your own. \n Only MU from a single field will be counted towards your OneUp score. The first field of the week must be at least %i MUs, but no greater than %i MUs. Subsequent fields must not exceed %i%% or %i MU gain [whichever is larger] from prior OneUp field.\n The round ends Sunday Night at Midnight, when the last field wins and the game starts over with a new round." % (mu_minimum, mu_maximum, (mu_multiplier-1)*100, mu_increase)

    bot.send_message_parsed(event.conv_id, message)

