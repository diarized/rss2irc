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


DEBUG = True


def init_irc_socket():
    network = "irc.freenode.net" #Define IRC Network
    port = 6667 #Define IRC Server Port
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket
    irc.connect((network,port)) #Connect to Server
    return irc


def irc_join_to_channel(irc, chan, nick):
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


def store_link(db, entry):
    logging.debug('Storing link ' + entry['title'])
    try:
        db.execute("INSERT INTO rss VALUES('%s', '%s');" % (entry['title'], entry['link']))
        db.commit()
    except (sql.OperationalError, sql.ProgrammingError):
        logging.error('Storing link failed: ' + entry['title'])
        return False
    else:
        return True


def clear_table():
    logging.debug('DELETE FROM rss')
    conn.execute("DELETE FROM rss;")
    conn.commit()


def main():
    chan = '#999net'
    conn = sql.connect('hyrss')
    if not conn:
        os.exit(1)

    while True:
        try:
            if DEBUG:
                clear_table()
            irc = init_irc_socket()
            feed = feedparser.parse('https://news.ycombinator.com/rss')
            for entry in feed['entries']:
                if store_link(conn, entry):
                    time.sleep(1)
                    publish_link(irc, chan, entry)
                else:
                    logging.error('Link not stored and not published: ' + entry['title'])
            time.sleep(120)
        except Exception:
            conn.close()
            irc_command(irc, 'PART', chan)
            irc.close()


if __name__ == '__main__':
    main()
