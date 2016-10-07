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
    plugins.register_user_command(["packt"])

def _get_feed():
    url = 'https://www.packtpub.com/packt/offers/free-learning'
    r  = requests.get(url, headers={'User-Agent': 'icbot v360.N0.SC0P3'})
    data = r.text
    soup = BeautifulSoup(data)
    url = "http:%s" % soup.find('img', class_="bookimage")['src']
    title = soup.find('h2').text.strip()
    image = urljoin(url, urlparse(url).path)
    packt_obj = {'title': title,'link': 'https://www.packtpub.com/packt/offers/free-learning', 'image': image }
    return packt_obj

def packt(bot, event, *args):

    packt_obj = _get_feed()

    segments = [
        hangups.ChatMessageSegment(packt_obj['title'], is_bold=True)
    ]

    segments.append(hangups.ChatMessageSegment(' '))

    segments.append(
        hangups.ChatMessageSegment(
            packt_obj['link'],
            hangups.SegmentType.LINK,
            link_target=packt_obj['link']
        )
    )

    segments.append(hangups.ChatMessageSegment(' '))

    r = yield from aiohttp.request('get', packt_obj['image'])
    raw = yield from r.read()

    image_id = yield from bot._client.upload_image(
        io.BytesIO(raw),
        filename=os.path.basename(packt_obj['image'])
    )

    bot.send_message_segments(event.conv, segments, image_id=image_id)