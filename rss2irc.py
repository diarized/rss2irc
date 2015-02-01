#!/usr/bin/env python


import feedparser
import time
import datetime
import irc
import storage
import threading
import Queue
import logging
import ConfigParser
import sys
from pprint import pprint


REFRESH_TIME = 100
CONFIG_FILE='feeds.cfg'


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


    def run(self):
        logging.info('Entering into grabber()')
        old_storage_debug = storage.DEBUG
        while not self.kill_received.is_set():
            if datetime.datetime.now().second % 5 == 0:
                logging.debug("Grabber.kill_received NOT SET.")
                logging.debug(str([t.name for t in threading.enumerate()]))
            cp = ConfigParser.ConfigParser()
            cp.read(CONFIG_FILE)
            self.feeds = cp.items('feeds')

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
                    self.feed_queue.put((feed_name, 'clear_table'))
    
            for feed_name, feed_url in self.feeds:
                logging.debug('Reading feed {0}'.format(feed_name))
                raw_feed = feedparser.parse(feed_url)
                for entry in raw_feed['entries']:
                    entry['title'] = entry['title'].encode('utf-8', 'ignore')
                    entry['link'] = entry['link'].encode('utf-8')
                    if self.feed_queue:
                        logging.debug("Putting entry '{0}' into feed queue".format(entry['title']))
                        self.feed_queue.put((feed_name, entry))
            time.sleep(REFRESH_TIME)
        logging.debug('Grabber: kill_received set.')
        sys.exit()



class Publisher(threading.Thread):
    def __init__(self, feed_queue, store_queue, irc_queue, botname):
        self.feed_queue = feed_queue
        self.store_queue = store_queue
        self.irc_queue = irc_queue
        self.botname = botname
        self.kill_received = threading.Event()
        threading.Thread.__init__(self, name='Publisher')


    def run(self):
        logging.info('Entering into publisher()')
        feedback_queue = Queue.Queue()
        cleared_tables = {}
        while not self.kill_received.is_set():
            if datetime.datetime.now().second % 5 == 0:
                logging.debug("Publisher.kill_received NOT SET.")
                logging.debug(str([t.name for t in threading.enumerate()]))
            time.sleep(1)
            feed_name, entry = self.feed_queue.get()
    
            if storage.DEBUG and entry == 'clear_table': # and feed_name not in cleared_tables.keys(): # uncomment to clear once
                self.store_queue.put((feedback_queue, 'clear_table', feed_name, None))
                cleared_tables[feed_name] = True
                self.feed_queue.task_done()
                continue
    
            if not feed_name:
                logging.debug("No items in feed_queue.")
            elif feed_name == 'DIRECT_MESSAGE':
                message = entry
                self.irc_queue.put(
                    (
                        self.botname,
                        message,
                    )
                )
            else:
                logging.debug("New item in feed_queue.")
                self.feed_queue.task_done()
                self.store_queue.put((feedback_queue, 'publish', feed_name, entry))
    
            result, feed_name, entry = feedback_queue.get()
            if not feed_name:
                logging.debug("No items in feedback_queue (nothing stored).")
                continue
            else:
                logging.debug("New item in feedback_queue (something stored).")
                feedback_queue.task_done()
    
            if result:
                logging.debug("Entry '{0}' is new, saving.".format(entry['title']))
                self.irc_queue.put(
                        (
                            self.botname,
                            ' | '.join([
                                        feed_name,
                                        entry['title'],
                                        entry['link']
                            ])
                        )
                )
                time.sleep(1)
            else:
                logging.debug("Entry '{0}' already saved.".format(entry['title']))
        logging.debug('Publisher: kill_received set.')
        sys.exit()
    
    
def main():
    host = 'irc.freenode.net'
    port = 6667
    channel = '#999net'
    channels = [channel]
    feed_queue = Queue.Queue(100)

    # Satisfying IRCConnector interface
    main_thread = threading.current_thread()
    main_thread.kill_received = threading.Event()

    grabber_thread = Grabber(feed_queue)
    grabber_thread.daemon = True
    grabber_thread.start()

    irc_thread = irc.IRCConnector(main_thread, host, port, channels)
    irc_thread.daemon = True
    irc_thread.start()

    irc_queue = None
    attempts = 3
    reconnect_time = 5
    while attempts:
        try:
            irc_queue = irc_thread.channel_queues[channel]
        except KeyError:
            logging.warning("No channel_queues['{0}'] instantiated. Get some sleep.".format(channel))
            attempts -= 1
            time.sleep(reconnect_time)
        else:
            logging.info("channel_queues['{0}'] instantiated. Go ahead.".format(channel))
            break

    store = storage.Storage()
    store.daemon = True
    store.start()
    publisher_thread = Publisher(feed_queue, store.queue, irc_queue, irc_thread.botname)
    publisher_thread.start()

    threads = []
    threads.append(grabber_thread)
    threads.append(irc_thread)
    threads.append(store)
    threads.append(publisher_thread)
    while not irc_thread.kill_received.is_set():
        logging.debug("irc_thread.kill_received IS NOT SET.")
        logging.debug(str([t.name for t in threading.enumerate()]))
        time.sleep(1)
    logging.info("irc_thread.kill_received IS SET. Killing all threads and exiting.")
    store.kill_received.set()
    grabber_thread.kill_received.set()
    publisher_thread.kill_received.set()
    time.sleep(1)
    logging.debug(str([t.name for t in threading.enumerate()]))


if __name__ == '__main__':
    main()
