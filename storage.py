import sqlite3 as sql
import threading
import Queue
import logging
import sys
import re


DEBUG = True


logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


class Storage(threading.Thread):
    def __init__(self, db_name='hyrss'):
        self.db_name = db_name
        self.conn = None
        self.queue = Queue.Queue()
        self.kill_received = threading.Event()
        threading.Thread.__init__(self, name='Storage')
        logging.debug('Thread {0} initialized'.format(self.name))


    def connect(self):
        logging.debug("storage.connect(): my thread name is '{0}'".format(self.name))
        if not self.conn:
            self.conn = sql.connect(self.db_name)
        if not self.conn:
            logging.error('Sqlite3 db file disappeared or locked.')
            sys.exit(1)
        logging.debug('Connection to database established.')
        # I do not know which table to truncate :-(
        #if DEBUG: # DEBUG clears table in database
        #    self.clear_table()
    

    def disconnect(self):
        logging.debug("storage.disconnect(): my thread name is '{0}'".format(self.name))
        if self.conn:
            self.conn.close()


    def create_table(self, table_name):
        logging.warning('No table {0}. To be created.'.format(table_name))
        self.conn.execute('CREATE TABLE {0} (title TEXT PRIMARY KEY, link TEXT, published BOOLEAN);'.format(table_name))
        self.conn.commit()
        self.conn.execute('CREATE UNIQUE INDEX {0} ON {1} (title, link);'.format(table_name + '_index', table_name))
        self.conn.commit()


    def insert(table_name, entry):
        self.conn.execute("INSERT INTO {0} VALUES (?, ?, ?)".format(table_name),
                (
                    entry['title'],
                    entry['link'],
                    0
                )
        )
        self.conn.commit()


    def store_link(self, table_name, entry):
        logging.debug("Storing in table '{0}' link >>>{1}<<<".format(table_name, entry['title']))
        try:
            self.insert(table_name, entry)
        except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError), e:
            if re.search('no such table', str(e)):
                self.create_table(table_name)
                self.insert(table_name, entry)
            logging.error(e)
            logging.error('Storing link failed: ' + entry['title'])
            return False
        except AttributeError:
            self.connect()
            self.insert(table_name, entry)
        else:
            logging.error('Storing link succeeded: ' + entry['title'])
            return True
    
    
    def set_link_published(self, table_name, entry):
        title = entry['title']
        link  = entry['link']
        logging.debug(u'Link on IRC, setting it as published in database. ({0})'.format(title))
        try:
            self.conn.execute("UPDATE ? SET published = 1 WHERE title = ?", (table_name, entry['title']))
            self.conn.commit()
        except (sql.OperationalError, sql.ProgrammingError), e:
            logging.error('Setting link as published failed: ' + title)
            logging.debug(e)
            return False
        else:
            return True
    
    
    def clear_table(self, table_name):
        logging.debug('Clearing the database.')
        try:
            self.conn.execute("DELETE FROM {0};".format(table_name))
            self.conn.commit()
        except sql.OperationalError, e:
            if re.search('no such table', str(e)):
                self.create_table(table_name)
    

    def run(self):
        self.connect()
        while not self.kill_received.is_set():
            feeder_queue, action, feed_name, entry = self.queue.get()
            logging.debug("Storage received action '{0}'".format(action))
            if action == 'publish':
                if self.store_link(feed_name, entry) and feeder:
                    logging.debug("Putting in feeder '{0}' queue an info about the success of storing link >>>{1}<<<.".format(feeder.name, entry['title']))
                    feeder_queue.put((True, feed_name, entry))
            elif action == 'clear_table':
                table_name = feed_name
                self.clear_table(table_name)
            else:
                logging.error("Unknown action '{0}' from Feeder to Storage".format(action))
            self.queue.task_done()


