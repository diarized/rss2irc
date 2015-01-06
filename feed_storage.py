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
        db.execute("INSERT INTO rss VALUES('%s', '%s', '%s');" % (entry['title'], entry['link'], 0))
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError), e:
        logging.error('Storing link failed: ' + entry['title'])
        print e
        return False
    else:
        return True


def set_link_published(db, entry):
    title = entry['title']
    link  = entry['link']
    logging.debug(u'Link on IRC, setting it as published in database. ({0})'.format(title))
    try:
        db.execute("UPDATE rss SET published = '%s';" % 1)
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError), e:
        logging.error('Setting link as published failed: ' + title)
        print e
        return False
    else:
        return True


def clear_table(conn):
    logging.debug('DELETE FROM rss')
    conn.execute("DELETE FROM rss;")
    conn.commit()


class FeedStorage(threading.Thread):
    def __init__(self):
        ircc = {
            "host": "irc.freenode.net",
            "port": 6667,
            "channels": ["#999net",]
        }
    
        self.irc_thread = irc.IRCConnector(ircc['host'], ircc['port'], ircc['channels'])
        self.irc_thread.daemon = True
        self.irc_thread.start()

        time.sleep(5)
        self.thr, self.botname = irc.get_thread([self.irc_thread], 'irc.freenode.net', '#999net')

        threading.Thread.__init__(self, name='FeedStorage')

    def run(self):
        self.conn = sql.connect('hyrss')
        if not self.conn:
            logging.error('Sqlite3 db file disappeared or locked.')
            sys.exit(1)
        logging.debug('conn is {0}'.format(self.conn))
        while True:
            try:
                if DEBUG: # DEBUG clears table in database
                    logging.debug('Clearing the database.')
                    clear_table(self.conn)
                logging.debug('Getting the feed')
                feed = feedparser.parse('https://news.ycombinator.com/rss')
                for entry in feed['entries']:
                    entry['link'] = entry['link'].encode('ascii', 'ignore')
                    entry['title'] = entry['title'].encode('ascii', 'ignore')
                    logging.debug('Parsing entry {0}'.format(entry['title']))
                    if store_link(self.conn, entry):
                        logging.debug('Link {0} stored'.format(entry['link']))
                        time.sleep(1)
                        message = entry['title'].strip() + ' | ' + entry['link'].strip()
                        irc.put_in_queue(self.thr, self.botname, message)
                        set_link_published(self.conn, entry)
                    else:
                        logging.error('Link not stored and not published: ' + entry['title'])
                time.sleep(REFRESH_TIME)
            except Exception, e:
                if self.conn:
                    self.conn.close()
                self.irc_thread.join()
                print("Exception {0}. Exiting...".format(e))
                sys.exit()


