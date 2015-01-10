import irc
import threading
import logging
import sqlite3 as sql
import time
import feedparser
import sys

DEBUG = False
REFRESH_TIME = 300

def store_link(db, entry):
    logging.debug('Storing link ' + entry['title'])
    try:
        db.execute("INSERT INTO rss VALUES (?, ?, ?)", (entry['title'], entry['link'], 0))
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError), e:
        logging.error(e)
        logging.error('Storing link failed: ' + entry['title'])
        return False
    else:
        return True


def set_link_published(db, entry):
    title = entry['title']
    link  = entry['link']
    logging.debug(u'Link on IRC, setting it as published in database. ({0})'.format(title))
    try:
        db.execute("UPDATE rss SET published = 1")
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError), e:
        logging.error('Setting link as published failed: ' + title)
        logging.debug(e)
        return False
    else:
        return True


def clear_table(conn):
    logging.debug('Clearing the database.')
    conn.execute("DELETE FROM rss;")
    conn.commit()


class FeedStorage(threading.Thread):
    def __init__(
            self,
            ircc={
                'host': 'irc.freenode.net',
                'port': 6667,
                'channels': ['#999net',],
            },
            url='https://news.ycombinator.com/rss'
        ):
        self.url = url
        self.conn = None
        self.kill_received = threading.Event()
        self.irc_thread = irc.IRCConnector(self, ircc['host'], ircc['port'], ircc['channels'])
        self.irc_thread.daemon = True
        self.irc_thread.start()

        time.sleep(5)
        self.thr, self.botname = irc.get_thread([self.irc_thread], ircc['host'], ircc['channels'][0])

        threading.Thread.__init__(self, name='FeedStorage')

    def disconnect(self):
        if self.conn:
            self.conn.close()
        self.irc_thread.kill_received.set()
        self.kill_received.set()
        sys.exit()

    def store_and_publish(self, entry):
        entry['link'] = entry['link'].encode('ascii', 'ignore')
        entry['title'] = entry['title'].encode('ascii', 'ignore')
        logging.debug('Parsing entry {0}'.format(entry['title']))
        if store_link(self.conn, entry):
            logging.debug('Link {0} stored'.format(entry['link']))
            message = entry['title'].strip() + ' | ' + entry['link'].strip()
            irc.put_in_queue(self.thr, self.botname, message)
            set_link_published(self.conn, entry)
            return True
        else:
            logging.error('Link not stored and not published: ' + entry['title'])
        return False


    def connect(self):
        if not self.conn:
            self.conn = sql.connect('hyrss')
        if not self.conn:
            logging.error('Sqlite3 db file disappeared or locked.')
            sys.exit(1)
        logging.debug('Connection to database established.')
        if DEBUG: # DEBUG clears table in database
            clear_table(self.conn)


    def run(self):
        self.connect()
        while not self.kill_received.is_set():
            try:
                logging.debug('Getting the feed')
                feed = feedparser.parse(self.url)
                for entry in feed['entries']:
                    if self.store_and_publish(entry):
                        time.sleep(1) # Do not abuse IRC
                time.sleep(REFRESH_TIME)
            except Exception, e:
                logging.error("Exception {0}. Exiting...".format(e))
                self.disconnect()

