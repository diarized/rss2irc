import sys
import time
import datetime
import logging
import storage
import threading
import ConfigParser
import feedparser

CONFIG_FILE='feeds.cfg'
REFRESH_TIME = 300

if storage.DEBUG:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logging.basicConfig(
        level=loglevel,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


class Grabber(threading.Thread):
    def __init__(self, feed_queue):
        self.feeds = None
        self.feed_queue = feed_queue
        self.kill_received = threading.Event()
        threading.Thread.__init__(self, name='Grabber')

    def clear_tables(self, feed_name):
        self.feed_queue.put((feed_name, 'clear_table'))

    def feed_the_queue(self, feed_name, feed_url):
        logging.debug('Reading feed {0}'.format(feed_name))
        raw_feed = feedparser.parse(feed_url)
        for entry in raw_feed['entries']:
            entry['title'] = entry['title'].encode('utf-8', 'ignore')
            entry['link'] = entry['link'].encode('utf-8')
            if self.feed_queue:
                logging.debug("Putting entry '{0}' into feed queue".format(entry['title']))
                self.feed_queue.put((feed_name, entry))

    def read_config(self):
        cp = ConfigParser.ConfigParser()
        cp.read(CONFIG_FILE)
        self.feeds = cp.items('feeds')

    def run(self):
        logging.info('Entering into grabber()')
        old_storage_debug = storage.DEBUG
        while not self.kill_received.is_set():
            if datetime.datetime.now().second % 5 == 0:
                logging.debug("Grabber.kill_received NOT SET.")
                logging.debug(str([t.name for t in threading.enumerate()]))
            self.read_config()

            if old_storage_debug != storage.DEBUG:
                self.feed_queue.put(
                        (
                            'DIRECT_MESSAGE',   # feed_name
                            {                   # entry
                                'title': 'storage.DEBUG changed to ',
                                'link': str(storage.DEBUG)
                            }
                        )
                )
                old_storage_debug = storage.DEBUG

            if storage.DEBUG:
                for feed_name, feed_url in self.feeds:
                    self.clear_tables(feed_name)
    
            for feed_name, feed_url in self.feeds:
                self.feed_the_queue(feed_name, feed_url)
            time.sleep(REFRESH_TIME)
        logging.debug('Grabber: kill_received set.')
        sys.exit()
