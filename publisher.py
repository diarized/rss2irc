import logging
import time
import datetime
import storage
import sys
import threading
import Queue


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
    

