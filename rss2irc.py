#!/usr/bin/env python

import feedparser
import socket
import sqlite3 as sql
import sys
import time
import logging


DEBUG = True


class IrcSocketError(Exception):


    def __init__(self, irc):
        self.init_irc_socket(irc)


    def init_irc_socket(self, irc):
        attempts = 3
        timeout = 10
        network = "irc.freenode.net" #Define IRC Network
        port = 6667 #Define IRC Server Port
        irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket
        while attempts:
            try:
                irc.connect((network,port)) #Connect to Server
            except socket.error:
                attempts -= 1
                logging.error('Exception: Cannot connect to IRC server. Attempts that left: ' + str(attempts))
                time.sleep(timeout)
                continue
            else:
                break
        else:
            return irc
        raise socket.error


logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


def init_irc_socket():
    attempts = 3
    timeout = 10
    network = "irc.freenode.net" #Define IRC Network
    port = 6667 #Define IRC Server Port
    logging.debug('Connecting to IRC server ' + str(network))
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket
    # DEBUG
    irc.connect((network,port)) #Connect to Server
    irc.recv(4096) #Setting up the Buffer
    return irc
    # END OF DEBUG
    while attempts:
        try:
            irc.connect((network,port)) #Connect to Server
        except socket.error:
            attempts -= 1
            logging.error('Cannot connect to IRC server. Attempts that left: ' + str(attempts))
            time.sleep(timeout)
            continue
    else:
        return irc
    raise IrcSocketError(irc)


def irc_join_to_channel(irc, chan, nick):
    if not irc:
        logging.error('No IRC socket.')
        raise IrcSocketError(irc)
    logging.debug('Entering channel ' + chan + ' as ' + nick)
    try:
        irc.recv(4096) #Setting up the Buffer
        irc.send('NICK ' + nick + '\r\n') #Send our Nick(Notice the Concatenation)
        #irc_command(irc, nick, 'NICK')
        irc.send('USER artur monitor.stonith.pl bla :Artur\r\n') #Send User Info to the server
        #irc_command(irc, 'artur monitor.stonith.pl bla :Artur', 'USER')
        irc.send('JOIN ' + chan + '\r\n') # Join the pre defined channel
        #irc_command(irc, chan, 'JOIN')
    except socket.error:
        logging.error('Writing to IRC socked failed')
        raise IrcSocketError
    else:
        return True


def irc_command(irc, chan, command, message=None):
    if not message:
        command_string = command.upper() + ' ' + chan + '\r\n'
    else:
        message = message.encode('utf-8')
        command_string = command.upper() + ' ' + chan + ' :' + message + '\r\n'
    try:
        irc.send(command_string)
    except socket.error:
        logging.error('Command {0} failed on IRC channel {1}'.format(command, chan))
        raise IrcSocketError(irc)


def irc_privmsg(irc, chan, msg):
    irc_command(irc, chan, 'PRIVMSG', msg)


def publish_link(irc, chan, entry):
    nick = 'hnfeed' #define nick
    if not irc:
        irc = init_irc_socket()
        irc_join_to_channel(irc, chan, nick)
    message = entry['title'] + ' | ' + entry['link']
    irc_privmsg(irc, chan, message)


def store_link(db, entry):
    logging.debug('Storing link ' + entry['title'])
    try:
        db.execute("INSERT INTO rss (title, link) VALUES ('%s', '%s');" % (entry['title'], entry['link']))
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError):
        logging.error('Storing link failed: ' + entry['title'])
        return False
    else:
        return True


def update_link(db, link, published):
    try:
        db.execute("UPDATE rss SET published = %d WHERE link = '%s';" % (published, link))
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError):
        logging.error('Updating link failed: ' + link)
        return False
    else:
        return True


def is_published(db, link):
    #try:
    #    curs = db.execute("SELECT COUNT(*) FROM rss WHERE link = '%s' AND published = 0" % (link))
    #    rows = curs.fetchone()[0]
    #except (sql.OperationalError, sql.ProgrammingError, sql.IntegrityError):
    #    logging.error('Getting link failed: ' + link)
    #    return None
    #else:
    #    logging.debug('Found {0} occurences of link {1}...'.format(rows, link[:15]))
    #    return rows
    curs = db.execute("SELECT COUNT(*) FROM rss WHERE link = '%s' AND published = 0" % (link))
    rows = curs.fetchone()[0]
    return rows


def clear_table(conn):
    sql = "DELETE FROM rss;"
    logging.debug(sql)
    conn.execute(sql)
    conn.commit()


def main():
    chan = '#999net'
    conn = sql.connect('hyrss')
    if not conn:
        sys.exit(1)

    while True:
        if DEBUG:
            clear_table(conn)
        try:
            irc = init_irc_socket()
            logging.debug('Fetching RSS...')
            feed = feedparser.parse('https://news.ycombinator.com/rss')
            for entry in feed['entries']:
                store_link(conn, entry)
                time.sleep(1)
                publish_link(irc, chan, entry)
                update_link(conn, entry['link'], 1)
                logging.info('Link stored, published and updated: ' + entry['title'])
            time.sleep(120)
        except Exception as e:
            conn.close()
            irc_command(irc, 'PART', chan)
            irc.close()
            raise
            #sys.exit(2)


if __name__ == '__main__':
    main()
