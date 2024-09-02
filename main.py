"""Weekly"""
import os
from pathlib import Path
import json
import logging
import urllib
import time
import feedparser

def update_channel(item):
    """Update Channel"""
    fname_channel = f'channels/{item["channel"]}.md'
    md_old = ''

    Path('channels').mkdir(parents=True, exist_ok=True)
    if os.path.isfile(fname_channel):
        with open(fname_channel, mode='r', encoding='utf-8') as fd_channel_old:
            md_old = fd_channel_old.read()
            if md_old.find(item['link']) != -1:
                return

    md_new_entry = f'- [{item["title"]}]({item["link"]})\n'
    with open(fname_channel, mode='w', encoding='utf-8') as fd_channel_new:
        fd_channel_new.write(f'{md_new_entry}{md_old}')

def generate_readme(items):
    """Update Readme"""
    fname_readme = 'README.md'

    with open(fname_readme, mode='w', encoding='utf-8') as fd_readme:
        fd_readme.write('# 周刊\n\n')
        for item in items:
            md_channel = f'## {item["channel"]}\n'
            md_entry = f'- {item["published"]} [{item["title"]}]({item["link"]})'
            md_more = f'| [More](channels/{urllib.parse.quote(item["channel"])}.md)\n\n'
            fd_readme.write(f'{md_channel}{md_entry} {md_more}')

def main():
    """Main loop"""
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) '\
        'AppleWebKit/537.36 (KHTML, like Gecko) '\
        'Chrome/109.0.0.0 Safari/537.36'
    request_headers = {
        'user-agent': user_agent
    }
    feedparser.USER_AGENT = user_agent

    logger = logging.getLogger(__name__)
    logger.setLevel(os.environ.get('LOGLEVEL', 'INFO'))
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)

    conf = {}
    latest_items = []
    with open('feed.json', mode='r', encoding='utf-8') as fd_conf:
        conf = json.load(fd_conf)

    if 'feed' in conf:
        for feed in conf['feed']:
            if 'enable' in feed and feed['enable'] == 0:
                continue

            logger.debug(feed['url'])
            try:
                resp = feedparser.parse(feed['url'], request_headers=request_headers)
            except TimeoutError as e_timeout:
                logger.warning(e_timeout)
                continue
            except Exception as e_req:
                logger.warning(e_req)
                continue

            if not resp.has_key('entries'):
                logger.debug('no entries')
                continue

            # Order by ascending, most feed is descending by default
            if 'order' not in feed or 'descending' == feed['order']:
                resp.entries.reverse()
            # Filter by title
            if 'filter' in feed and len(feed['filter']) > 0:
                resp.entries = [entry for entry in resp.entries
                                if any(k in entry.title for k in feed['filter'])]
            # Limit size
            if 'limit' in feed:
                limit = int(feed['limit'])
                if limit > 0:
                    resp.entries = resp.entries[-limit:]

            i = 0
            total = len(resp.entries)
            for entry in resp.entries:
                if 'LWN.net Weekly Edition' in feed['channel']:
                    entry.title = entry.title.replace('[$] LWN.net Weekly Edition', 'LWN.net Weekly Edition')
                elif '艾迪蓝波' in feed['channel']:
                    entry.link = entry.link.replace('tangly1024.com', 'www.idnunber.top')
                elif '1Link.Fun 科技周刊' in feed['channel']:
                    if 'xiaobot.net' in entry.link and entry.has_key('guid'):
                        entry.link = entry['guid']
                elif feed['channel'] in ['GitHub Trending Weekly', 'B站每周必看']:
                    entry['published_parsed'] = time.localtime()
                item = {
                    'channel': feed['channel'],
                    'title': entry.title,
                    'link': entry.link,
                    'published': time.strftime(
                        '%Y/%m/%d', entry.published_parsed if entry.has_key(
                        'published_parsed') else entry.updated_parsed)
                }
                logger.debug(item)
                update_channel(item)
                i = i + 1
                # Update the latest
                if i == total:
                    latest_items.append(item)

    if len(latest_items) > 0:
        latest_items = sorted(latest_items, key=lambda x: x['published'], reverse=True)
        generate_readme(latest_items)

if __name__ == '__main__':
    main()
