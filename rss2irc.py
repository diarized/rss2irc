#!/usr/bin/env python

import feedparser
import socket
import sqlite3 as sql
import os
import time
import logging


logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


DEBUG = False
REFRESH_TIME = 300


def init_irc_socket():
    """
    Initiate TCP connection (IP:port)
    """
    network = "irc.freenode.net" #Define IRC Network
    port = 6667 #Define IRC Server Port
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket
    attempts = 3
    while attempts:
        try:
            irc.connect((network,port)) #Connect to Server
        except socket.error:
            # Try again
            time.sleep(REFRESH_TIME/2)
            attempts -= 1
        else:
            break
    else:
        raise
    return irc


def irc_join_to_channel(irc, chan, nick):
    """
    Connects to IRC channel, no matter what
    """
    if not irc:
        logging.error('No IRC socket.')
        return False
    try:
        irc.recv(4096) #Setting up the Buffer
        irc.send('NICK ' + nick + '\r\n') #Send our Nick(Notice the Concatenation)
        irc.send('USER artur monitor.stonith.pl bla :Artur\r\n') #Send User Info to the server
        irc.send('JOIN ' + chan + '\r\n') # Join the pre defined channel
    except socket.error:
        logging.error('Writing to IRC socked failed')
        raise
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
    except socker.error:
        logging.error('Command {0} failed on IRC channel {1}'.format(command, chan))
        raise KeyboardInterrupt


def irc_privmsg(irc, chan, msg):
    irc_command(irc, chan, 'PRIVMSG', msg)


def publish_link(irc, chan, entry):
    nick = 'hnfeed' #define nick
    if not irc_join_to_channel(irc, chan, nick):
        irc = init_irc_socket()
        irc_join_to_channel(irc, chan, nick)
    message = entry['title'] + ' | ' + entry['link']
    irc_privmsg(irc, chan, message)
    return True # possible exception makes it nonTrue


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


def main():
    chan = '#999net' # channel semi-private
    conn = sql.connect('hyrss')
    if not conn:
        logging.error('Sqlite3 db file disappeared or locked.')
        os.exit(1)
    logging.debug('conn is {0}'.format(conn))

    while True:
        irc = None
        try:
            if DEBUG: # DEBUG clears table in database
                clear_table(conn)
            irc = init_irc_socket()
            feed = feedparser.parse('https://news.ycombinator.com/rss')
            for entry in feed['entries']:
                if store_link(conn, entry):
                    time.sleep(1)
                    if publish_link(irc, chan, entry):
                        set_link_published(conn, entry)
                else:
                    logging.error('Link not stored and not published: ' + entry['title'])
            time.sleep(REFRESH_TIME)
        except Exception, e:
            if conn:
                conn.close()
            if irc:
                irc_command(irc, 'PART', chan)
                irc.close()
            print("Exception {0}. Exiting...".format(e))
            raise


if __name__ == '__main__':
    # Main invoked only in calling program from shell
    main()
