#!/usr/bin/env python

import feedparser
import socket
import sqlite3 as sql
import os
import sys
import time
import datetime
import re
import logging
import threading
import Queue


logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)


DEBUG = True
REFRESH_TIME = 30
RECONNECT_TIME = REFRESH_TIME/2


class IrcConnection(threading.Thread):
    def __init__(self):
        """
        Initiate TCP connection (IP:port)
        """
        self.network = "irc.freenode.net" #Define IRC Network
        self.port = 6667 #Define IRC Server Port
        self.irc = None
        self.queue = Queue.Queue(100)
        self.attempts = 3
        self.joinable = False
        threading.Thread.__init__(self)

    def run(self):
        logging.debug('Thread IrcConnection started')
        while True:
            if not self.irc:
                self.connect()
            msg_received = self.receive()
            #self.send_to_channel()


    def connect(self):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket

        while self.attempts:
            try:
                self.irc.connect((self.network,self.port)) #Connect to Server
            except socket.error:
                # Try again
                logging.warning("socket.error: cannot connect to IRC server.")
                time.sleep(RECONNECT_TIME)
                self.attempts -= 1
            else:
                logging.debug("connected to IRC server {0}.".format(self.network))
                break
        else:
            error_msg = "socket.error: could not connect to IRC server for {0} secs"
            logging.error(error_msg.format(RECONNECT_TIME*self.attempts))
            sys.exit(1)


    def receive(self):
        if not self.irc:
            self.connect()
        try:
            line = self.irc.recv(512)
        except socket.error:
            self.irc = None
            logging.error('Disconnected')
            sys.exit(1)
        if line:
            logging.debug("Received: " + line)
        line.strip()
        if re.search("PING", line):
            self.ping(line)
            return None
        if re.search(":End of /MOTD command.", line):
            logging.debug("Received ':End of /MOTD command.'. IRC channels are joinable.")
            self.is_joinable(line)
        if re.search("PRIVMSG", line):
            logging.debug("Received PRIVMSG to me: " + line)
            self.examine(self.get_command(line))
        return line


    def ping(self, line):
        splitline = line.split(' :')
        if splitline[0] == "PING":
            pong = "PONG {0}".format(splitline[1])
            logging.info(pong)
            self.say(pong)


    def is_joinable(self, line):
        if re.search(":End of /MOTD command.", line):
            self.joinable = True


    def get_command(self, line):
        details = line.split()
        user = details[0].split("!")
        username = user[0][1:]
        channel = details[2]
        messagelist = details[3:]
        message = " ".join(messagelist)[1:]
        logging.debug("Extacting command '{0}' from user {1} on channel '{2}'.".format(message.lower(), username, channel))
        return (channel, username, message.lower())


    def examine(cmd):
        channel, username, command = cmd
        if command == "$date":
            self.irc_privmsg(channel, "{0}, the time is {1}".format(username, datetime.now()))
        if command == "$kill":
            self.say("QUIT :Bot quit\n")


    def send(self):
        if self.queue.empty():
            return
        channel, data = self.queue.get()
        logging.debug('Data to send: {0}'.format(data))
        self.irc_privmsg(channel, data)


    def say(self, cmd):
        if not self.irc:
            self.connect()
        try:
            self.irc.send(cmd)
        except socket.error:
            logging.error('Sending command "{0}" failed on IRC'.format(cmd))
            sys.exit(2)
        else:
            logging.info('Sending command "{0}" on IRC succeeded.'.format(cmd))
    

    def irc_command(self, channel_name, command, message=None):
        if not message:
            command_string = command.upper() + ' ' + channel_name + '\r\n'
        else:
            message = message.encode('utf-8')
            command_string = command.upper() + ' ' + channel_name + ' :' + message + '\r\n'
        self.say(command_string)


    def irc_privmsg(self, channel, msg):
        self.irc_command(channel, 'PRIVMSG', msg)


    def quit(self):
        self.say("QUIT :Bot quit\r\n")
        if self.irc:
            self.irc.close()


class IrcChannel(threading.Thread):
    def __init__(self, irc_connection, channel_name, nick_name):
        self.irc          = irc_connection
        self.network      = irc_connection.network
        self.channel_name = channel_name
        self.nick_name    = nick_name
        self.real_name    = 'Artur'
        self.identity     = 'artur'
        self.hostname     = 'monitor.stonith.pl'
        self.queue        = self.irc.queue
        self.joined       = False
        threading.Thread.__init__(self)


    def join(self):
        """
        Connects to IRC channel, no matter what
        """
        if not self.irc:
            logging.error('No IRC socket when JOINing channel {0} on {1}.'.format(
                self.channel_name,
                self.network
                )
            )
            return False
        try:
            self.irc.say('NICK {0}\r\n'.format(self.nick_name)) #Send our Nick(Notice the Concatenation)
            self.irc.say('USER {0} {1} {2} :{3}\r\n'.format(
                self.identity,
                self.hostname,
                self.network,
                self.real_name
                )
            ) #Send User Info to the server
            self.irc.say('JOIN {0}\r\n'.format(self.channel_name)) # Join the pre defined channel
        except socket.error:
            logging.error('Writing to IRC socked failed')
            raise
        else:
            self.joined = True
            return True

    def irc_privmsg(self, msg):
        self.irc.irc_privmsg(self.channel_name, msg)

    def run(self):
        logging.debug('Thread IrcChannel initiated')
        while True:
            if not self.irc.joinable:
                continue
            if not self.joined:
                self.join()
            if not self.queue.empty():
                channel, data = self.queue.get()
                self.irc_privmsg(data)


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

    irc_connection = IrcConnection()
    irc_connection.daemon = True
    irc_connection.start()
    irc_channel    = IrcChannel(irc_connection, chan, 'hnnfeed')
    irc_channel.daemon = True
    irc_channel.start()

    irc = None
    while True:
        try:
            if DEBUG: # DEBUG clears table in database
                clear_table(conn)
            feed = feedparser.parse('https://news.ycombinator.com/rss')
            for entry in feed['entries']:
                if store_link(conn, entry):
                    time.sleep(1)
                    message = entry['title'].strip() + ' | ' + entry['link'].strip()
                    if irc_channel.queue.put(message):
                        set_link_published(conn, entry)
                else:
                    logging.error('Link not stored and not published: ' + entry['title'])
            time.sleep(REFRESH_TIME)
        except Exception, e:
            if conn:
                conn.close()
            irc_connection.quit()
            print("Exception {0}. Exiting...".format(e))
            raise


if __name__ == '__main__':
    # Main invoked only in calling program from shell
    main()
