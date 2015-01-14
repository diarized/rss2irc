import irc
import storage
import threading
import Queue
import logging
import time
import feedparser
import sys

DEBUG = True
REFRESH_TIME = 30

class Feeder(threading.Thread):
    def __init__(
            self,
            ircc={
                'host': 'irc.freenode.net',
                'port': 6667,
                'channels': ['#999net',],
            },
            urls=[
                    ('HN', 'https://news.ycombinator.com/rss'),
                    ('TorrentFreak', 'http://feeds.feedburner.com/Torrentfreak')
                ]
        ):
        self.urls = urls
        self.conn = None
        self.kill_received = threading.Event()
        self.queue = Queue.Queue()
        self.irc_thread = irc.IRCConnector(self, ircc['host'], ircc['port'], ircc['channels'])
        self.irc_thread.daemon = True
        self.irc_thread.start()

        self.store = storage.Storage(ircc['host'])
        self.store.daemon = True
        self.store.start()

        time.sleep(5)
        self.thr, self.botname = irc.get_thread([self.irc_thread], ircc['host'], ircc['channels'][0])
        if DEBUG:
            for feed_name, url in self.urls:
              self.store.queue.put((self, 'clear_table', feed_name, None))

        threading.Thread.__init__(self, name='Feeder')


    def disconnect(self):
        logging.debug("feed.disconnect(): my thread name is '{0}'".format(self.name))
        self.irc_thread.kill_received.set()
        self.store.kill_received.set()
        self.kill_received.set()
        sys.exit()


    def store_and_publish(self, feed_name, entry):
        entry['link'] = entry['link'].encode('ascii', 'ignore')
        entry['title'] = entry['title'].encode('ascii', 'ignore')
        action = 'publish'
        logging.debug(
            "Putting 'publish' request from '{local_thread_name}' to storage thread '{storage_thread_name}' for link '{link}'".format(
                local_thread_name   = self.name,
                storage_thread_name = self.store.name,
                link                = entry['title']
            )
        )
        self.store.queue.put((self, action, feed_name, entry))


    def publish_feed(self, feed_name, url):
        logging.debug('Getting the feed {0} from {1}'.format(feed_name, url))
        feed = feedparser.parse(url)
        for entry in feed['entries']:
            self.store_and_publish(feed_name, entry)


    def run(self):
        while not self.kill_received.is_set():
            try:
                for feed_name, url in self.urls:
                    logging.debug("Processing feed '{0}' in thread '{1}'.".format(feed_name, self.name))
                    self.publish_feed(feed_name, url))
                    result, feed_name, entry = self.queue.get()
                    if result:
                        message = entry['title'].strip() + ' | ' + entry['link'].strip()
                        irc.put_in_queue(self, self.thr, self.botname, message)
                        self.store.set_link_published(feed_name, entry)
                        time.sleep(1)
            except Exception, e:
                logging.error("Exception {0}. Exiting...".format(e))
                self.disconnect()
                raise
            time.sleep(REFRESH_TIME)

