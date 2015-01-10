import irc
#import storage
import threading
import logging
import time
import feedparser
import sys

REFRESH_TIME = 300

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
        self.irc_thread = irc.IRCConnector(self, ircc['host'], ircc['port'], ircc['channels'])
        self.irc_thread.daemon = True
        self.irc_thread.start()

        self.store = storage.Storage(host)

        time.sleep(5)
        self.thr, self.botname = irc.get_thread([self.irc_thread], ircc['host'], ircc['channels'][0])

        threading.Thread.__init__(self, name='Feeder')


    def disconnect(self):
        storage.disconnect()
        self.irc_thread.kill_received.set()
        self.kill_received.set()
        sys.exit()


    def store_and_publish(self, feed_name, entry):
        entry['link'] = entry['link'].encode('ascii', 'ignore')
        entry['title'] = entry['title'].encode('ascii', 'ignore')
        logging.debug('Parsing entry {0}'.format(entry['title']))
        if self.store.store_link(feed_name, entry):
            logging.debug('Link {0} stored'.format(entry['link']))
            message = entry['title'].strip() + ' | ' + entry['link'].strip()
            irc.put_in_queue(self.thr, self.botname, message)
            storage.set_link_published(feed_name, entry)
            return True
        else:
            logging.error('Link not stored and not published: ' + entry['title'])
        return False


    def publish_feed(feed_name, url):
        logging.debug('Getting the feed {0} from {1}'.format(feed_name, url))
        feed = feedparser.parse(url)
        for entry in feed['entries']:
            if self.store.store_and_publish(feed_name, entry):
                time.sleep(1) # Do not abuse IRC
        time.sleep(REFRESH_TIME)


    def run(self):
        self.connect()
        while not self.kill_received.is_set():
            try:
                for feed_name, url in self.urls:
                    self.publish_feed(feed_name, url)
            except Exception, e:
                logging.error("Exception {0}. Exiting...".format(e))
                self.disconnect()

