#!/usr/bin/env python


import feedparser
import time
import irc
import storage
import threading
import Queue
import logging


logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


def grabber(feeds, feed_queue):
    logging.debug('Entering into grabber()')
    while True:
        for feed_name, feed_url in feeds:
            logging.debug('Reading feed {0}'.format(feed_name))
            raw_feed = feedparser.parse(feed_url)
            for entry in raw_feed['entries']:
                logging.debug("Putting entry '{'title'}' into feed queue".format(entry))
                feed_queue.put((feed_name, entry))
        time.sleep(30)


def publisher(feed_queue, store, irc_queue):
    logging.debug('Entering into publisher()')
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
            time.sleep(1)


def main():
    host = 'irc.freenode.net'
    port = 6667
    channel = '#999net'
    channels = [channel]
    feeds = [
        ('HN', 'https://news.ycombinator.com/rss'),
        ('TorrentFreak', 'http://feeds.feedburner.com/Torrentfreak')
    ]
    feed_queue = Queue.Queue()

    # Satifying IRCConnector interface
    main_thread = threading.current_thread()
    main_thread.kill_received = threading.Event()

    threads = []
    grabber_thread = threading.Thread(target=grabber, args=(feeds, feed_queue))
    #grabber_thread.daemon = True
    grabber_thread.start()
    threads.append(grabber_thread)

    irc_thread = irc.IRCConnector(main_thread, host, port, channels)
    #irc_thread.daemon = True
    irc_thread.start()
    threads.append(irc_thread)
    irc_queue = irc_thread.channel_threads[channel].queue

    store = storage.Storage()
    publisher_thread = threading.Thread(target=publisher, args=(feed_queue, store, irc_queue))
    publisher_thread.start()
    threads.append(publisher_thread)
    [t.join() for t in threads]


if __name__ == '__main__':
    main()
