from coc import ClashOfClans
import aiohttp
import plugins
import hangups
import io
import os
import logging

logger = logging.getLogger(__name__)
_internal = {}

def _initialize(bot):
    api_key = bot.get_config_option('clash_api_key')
    if api_key:
        _internal['clash_api_key'] = api_key
        plugins.register_user_command(['clan', 'clanlink', 'clancompare'])
        plugins.register_admin_command(['setclan'])
    else:
        logger.error('CLASH: config["clash_api_key"] required')

def setclan(bot, event, *args):
    """Sets the default Clan for this hangout when searching for Clan data
    /bot setclan <tag>
    """
    clan_tag = ''.join(args).strip()
    if not clan_tag:
        yield from bot.coro_send_message(event.conv_id, _('No Clan tag was specified, please specify a tag.'))
        return
    
    if not bot.memory.exists(["conv_data", event.conv.id_]):
        bot.memory.set_by_path(['conv_data', event.conv.id_], {})

    bot.memory.set_by_path(["conv_data", event.conv.id_, "default_clan"], clan_tag)
    bot.memory.save()
    yield from bot.coro_send_message(event.conv_id, _('This hangouts default Clan has been set to {}.'.format(clan_tag)))

def clan(bot, event, *args):
    """Returns Clan information from ClashOfClans API
    <b>/bot clan</b> Get a clan's current stats. If the default Clan is not set, talk to a hangout admin.
    <b>/bot clan <search criteria></b> Find a clan and return their stats.  Criteria can be the Clan Name or the Clan Tag.  Tag must start with a '#' sign.
    """
    coc = ClashOfClans(bearer_token=_internal['clash_api_key'])
    
    if not args:
        if bot.memory.exists(["conv_data", event.conv.id_]) and (bot.memory.exists(["conv_data", event.conv.id_, "default_clan"])):
            search = bot.memory.get_by_path(["conv_data", event.conv.id_, "default_clan"])
            r = coc.clans(search).get()
        else:
            yield from bot.coro_send_message(event.conv_id, 'No search parameters specified and no default Clan set for this Hangout.')
            return
    else:
        search = ' '.join(args)
        if search.startswith('#'):
            """search by tag"""
            r = coc.clans(search.upper()).get()
            if r=={'reason': 'notFound'}:
                yield from bot.coro_send_message(event.conv_id, 'No results found.')
                return

        else:
            """search by name"""
            r = coc.clans(name=search,limit=1).get()
            if r==[]:
                yield from bot.coro_send_message(event.conv_id, 'No results found.')
                return                
            else:
                r = r[0]

    _internal['last_clan'], _internal['last_tag'] = r['name'], r['tag']
    wars = 0
    wars += r.get('warWins', 0) + r.get('warTies', 0) + r.get('warLosses', 0)
    if wars > 0:
        winrate = r['warWins']/wars
    else:
        winrate = 0
    clanstrings = []
    clanstrings.append("<b>%s</b>" % r['name'])
    clanstrings.append("<i>%s</i>" % r['tag'])
    clanstrings.append("Members: %s" % r['members'])
    clanstrings.append("Level: %s" % r['clanLevel'])
    clanstrings.append("Points: %s" % r['clanPoints'])
    clanstrings.append("Wars: %s" % wars)
    clanstrings.append("Wins: %s" % r.get('warWins', 0))
    clanstrings.append("Ties: %s" % r.get('warTies', 0))
    clanstrings.append("Losses: %s" % r.get('warLosses', 0))
    clanstrings.append("Win Rate: %s" % "{:.0%}".format(winrate))
    result =  "<br/>".join(clanstrings)
    current_clan = {
        'result': result,
        'badge': r['badgeUrls']['small']
    }
    r = yield from aiohttp.request('get', current_clan['badge'] )
    raw = yield from r.read()

    current_clan['image_id'] = yield from bot._client.upload_image(
        io.BytesIO(raw),
        filename=os.path.basename(current_clan['badge'])
    )
    if current_clan:
        result = current_clan['result']
        image_id = current_clan['image_id']
        yield from bot.coro_send_message(event.conv_id, result, image_id=image_id)
    else:
        yield from bot.coro_send_message(event.conv_id, 'There was an error retrieving the Clan')

def clanlink(bot, event, *args):
    """Returns a Clash-of-Stats link to the last-searched Clan
    <b>/bot clanlink</b>
    """
    if _internal.get('last_tag', False):
        tag = _internal['last_tag']
    elif bot.memory.exists(["conv_data", event.conv.id_]) and (bot.memory.exists(["conv_data", event.conv.id_, "default_clan"])):
            tag = bot.memory.get_by_path(["conv_data", event.conv.id_, "default_clan"])
    else:
        yield from bot.coro_send_message(event.conv_id, 'There is no criteria retrieving the link.  Try the Clan command to get a Clan tag in memory.')
    url = 'https://www.clashofstats.com/clans/%s/members' % tag.replace('#', '')
    yield from bot.coro_send_message(event.conv_id, url)

def clancompare(bot, event, *args):
    """Returns a link to a Clash-of-Stats comparison page
    <b>/bot clancompare</b> Returns link to compare Default Clan to the Clan last returned by the <i>/bot clan</i> command.
    <b>/bot clancompare <clan tag(s)></b> Returns link to compare Default Clan to one of more specified Clans.  Tags must include '#' and must be seperated by a space.
    """
    if bot.memory.exists(["conv_data", event.conv.id_]) and (bot.memory.exists(["conv_data", event.conv.id_, "default_clan"])):
        tag1 = bot.memory.get_by_path(["conv_data", event.conv.id_, "default_clan"])
    else:
        yield from bot.coro_send_message(event.conv_id, 'There is no Default clan set. Please ask Admin to set a default')
        return
    if not args:
        if _internal.get('last_tag', False):
            tag2 = _internal['last_tag']
        else:
            yield from bot.coro_send_message(event.conv_id, 'No Clan specified and no Clan in memory.')
            return
        if tag2 == tag1:
            yield from bot.coro_send_message(event.conv_id, 'It\'s pointless to compare the same Clan to itself.')
            return
    else:
        if args[0].startswith('#'):
            tag2 = ','.join(args)
        else:
            yield from bot.coro_send_message(event.conv_id, 'Incorrect Clan tag parameter')
            return
        
    url = 'https://www.clashofstats.com/clans-comparison?clans=%s,%s' % (tag1.replace('#', ''), tag2.replace('#', ''))
    yield from bot.coro_send_message(event.conv_id, url)
