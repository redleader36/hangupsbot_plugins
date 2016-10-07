import aiohttp
import hangups
import io
import os
# import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import plugins

def _initialise(bot):
    plugins.register_user_command(["blipshift"])

def _get_feed():
    url = 'http://www.blipshift.com'
    r  = requests.get(url)
    data = r.text
    soup = BeautifulSoup(data)
    url = "http:%s" % soup.find('ul', class_="slides").findAll('li')[1].find('img')['src']
    title = soup.find('h2').text
    image = urljoin(url, urlparse(url).path)
    blipshift_obj = {'title': title,'link': 'http://www.blipshift.com', 'image': image }
    return blipshift_obj

def blipshift(bot, event, *args):

    blipshift_obj = _get_feed()

    segments = [
        hangups.ChatMessageSegment(blipshift_obj['title'], is_bold=True)
    ]

    segments.append(hangups.ChatMessageSegment(' '))

    segments.append(
        hangups.ChatMessageSegment(
            blipshift_obj['link'],
            hangups.SegmentType.LINK,
            link_target=blipshift_obj['link']
        )
    )

    segments.append(hangups.ChatMessageSegment(' '))

    r = yield from aiohttp.request('get', blipshift_obj['image'])
    raw = yield from r.read()

    image_id = yield from bot._client.upload_image(
        io.BytesIO(raw),
        filename=os.path.basename(blipshift_obj['image'])
    )

    bot.send_message_segments(event.conv, segments, image_id=image_id)