#!/usr/bin/env python

import argparse
import time
import datetime
import ircc
import storage
import grabber
import publisher
import threading
import Queue
import logging
from pprint import pprint

if storage.DEBUG:
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO

logging.basicConfig(
        level=loglevel,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)

    
def main():
    parser = argparse.ArgumentParser(description='Irc Bot.')
    parser.add_argument('--server', dest='server', help='IRC server')
    parser.add_argument('--channel', dest='channel', help='IRC channel')
    args = parser.parse_args()
    if args.server:
        host = args.server
    else:
        host = 'irc.freenode.net'
    if args.channel:
        channel = args.channel
        if not channel.startswith('#'):
            channel = '#' + channel
    else:
        channel = '#999net'
    channels = [channel]
    port = 6667
    feed_queue = Queue.Queue(100)

    # Satisfying IRCConnector interface
    main_thread = threading.current_thread()
    main_thread.kill_received = threading.Event()

    grabber_thread = grabber.Grabber(feed_queue)
    grabber_thread.daemon = True
    grabber_thread.start()

    irc_thread = ircc.IRCConnector(main_thread, host, port, channels)
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
    publisher_thread = publisher.Publisher(feed_queue, store.queue, irc_queue, irc_thread.botname)
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
