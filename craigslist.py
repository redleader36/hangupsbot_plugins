"""
Identify Craigslist ads, upload them to google plus, post in hangouts
"""
import hangups
import asyncio
import aiohttp
import os
import io
import re
import plugins
from lxml import etree
from urllib.request import urlopen

def _initialise(Handlers, bot=None):
    Handlers.register_handler(_watch_cl_link, type="message")
    return []

def _get_cl(url):
    with urlopen(url) as f:
        tree = etree.parse(f, etree.HTMLParser())
    cl = {}
    try:
        cl['image'] = tree.xpath("//*[contains(@class, \"slide first visible\")]/img/@src")[0]
    except IndexError:
        pass
    cl['title'] = "%s - "%(tree.xpath("//*[contains(@id, \"titletextonly\")]/text()")[0])
    try:
        cl['title'] += tree.xpath("//*[contains(@class, \"price\")]/text()")[0]
    except IndexError:
        pass
    return cl


@asyncio.coroutine
def _watch_cl_link(bot, event, command):
    # Don't handle events caused by the bot himself
    if event.user.is_self:
        return
    elif event.user_id.chat_id == "109361416879118616043":
        # brandon = "109361416879118616043"
        # matt = "103786724590957129619"
        #Dont handle event if Brandon Corpman
        return

    if " " in event.text:
        """immediately reject anything with spaces, must be a link"""
        return

    event_text_lower = event.text.lower()
    if re.match("^(https?://)?([a-z0-9.]*?\.)?craigslist.org/", event_text_lower, re.IGNORECASE):
        """imgur links can be supplied with/without protocol and extension"""
        cl = _get_cl(event.text)

        segments = [
            hangups.ChatMessageSegment(cl['title'], is_bold=True)
        ]
        if 'image' in cl:

            r = yield from aiohttp.request('get', cl['image'])
            raw = yield from r.read()

            image_id = yield from bot._client.upload_image(
                io.BytesIO(raw),
                filename=os.path.basename(cl['image'])
            )

            bot.send_message_segments(event.conv, segments, image_id=image_id)
        else:
            bot.send_message_segments(event.conv, segments)