#!/usr/bin/env python


import feedparser
import time
import irc
import storage
import threading
import Queue


store_queue  = Queue.Queue()
irc_queue    = None


def grabber(feeds, feed_queue):
    while True:
        for feed_name, feed_url in feeds:
            raw_feed = feedparser.parse(feed_url)
            for entry in raw_feed['entries']:
                feed_queue.put((feed_name, entry))
        time.sleep(30)


def publisher():
    while True:
        feed_name, entry = feed_queue.get()
        if store.save
        feed_queue.task_done()
        

def storage(feed_thread, irc_thread):
    pass    



def main():
    host = 'irc.freenode.net'
    port = 6667
    channel = '#999net'
    channels = [channel]
    feeds = [
        ('HN', 'https://news.ycombinator.com/rss'),
        ('TorrentFreak', 'http://feeds.feedburner.com/Torrentfreak')
    ]
    feed_queue   = Queue.Queue()

    grabber_thread = threading.Thread(target=grabber, args=(feeds, feed_queue))
    grabber_thread.daemon = True
    grabber_thread.start()

    irc_thread = irc.IRCConnector(host, port, channels)
    irc_thread.daemon = True
    irc_thread.start()
    irc_queue = irc_thread.channel_threads[channel].queue

    store = storage.Storage()
#====================
# DO NOT TOUCH ABOVE
#====================
    while True:
        feed_name, entry = feed_queue.queue.get()
        if store.store_link(feed_name, entry):
            irc_queue.put(
                    (
                        irc_thread.botname,
                        ' | '.join([
                                    entry['title'],
                                    entry['link']
                        ])
                    )
            )
