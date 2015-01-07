#!/usr/bin/env python

import socket
import sys
import re
import time
from datetime import datetime
import threading
import logging
import Queue

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)

DEBUG = True

class IRCConnector(threading.Thread):
    def __init__ (self, host, port, channels):
        self.host = host
        self.port = port
        self.channels = channels
        self.identity = "superbot"
        self.realname = "superbot"
        self.hostname = "supermatt.net"
        self.botname = "SPRBT"
        self.channel_queues = {}
        self.channel_threads = {}
        self.kill_received = threading.Event()
        threading.Thread.__init__(self, name=host)

    def output(self, message):
        logging.info("Server: %s\nMessage:%s\n" % (self.host, message))

    def disconnect(self):
        self.s.close()
        sys.exit()

    def receive(self):
            try:
                line = self.s.recv(500)
            except socket.error:
                logging.error("Disconnected")
                [t.join() for t in threading.enumerate()]
                self.disconnect()
            if line:
                return line
            return None


    def connect(self):
        attempts = 3
        irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket
        remote_ip = socket.gethostbyname(self.host)
        while attempts:
            try:
                irc_socket.connect((remote_ip,self.port)) #Connect to Server
            except socket.error:
                # Try again
                logging.warning("socket.error: cannot connect to IRC server.")
                time.sleep(RECONNECT_TIME)
                attempts -= 1
            else:
                logging.debug("connected to IRC server {0}.".format(self.host))
                break
        else:
            error_msg = "socket.error: could not connect to IRC server for {0} secs"
            logging.error(error_msg.format(RECONNECT_TIME*attempts))
            sys.exit(1)
        return irc_socket

    def run(self):
        logging.info("Thread of class IRCConnector started: '{0}'".format(self.name))
        self.s = self.connect()
        message1 = "NICK %s\r\n" %self.botname
        message2 = 'USER %s %s %s :%s\r\n' %(self.identity, self.hostname, self.host, self.realname)
        self.output(message1)
        self.output(message2)
        self.s.send(message1)
        self.s.send(message2)

        for chan in self.channels:
            logging.debug("Building thread for channel {0}".format(chan))
            q = Queue.Queue(10)
            self.channel_queues[chan] = q
            channel_thread = IRCChannel(self, self.s, chan, q)
            self.channel_threads[chan] = channel_thread
            channel_thread.daemon = True
            channel_thread.start()

        while not self.kill_received.is_set():
            line = self.receive()
            if line:
                self.output(line)
                logging.debug("Number of threads alive: {0}".format(threading.active_count()))
                logging.debug(str([t.name for t in threading.enumerate()]))
            else:
                continue

            line.strip()
            splitline = line.split(" :")
            if splitline[0] == "PING":
                pong = "PONG {0}".format(splitline[1])
                self.output(pong)
                self.s.send(pong)

            if re.search(":End of /MOTD command.", line):
                for chan in self.channels:
                    joinchannel = "JOIN {0}\n".format(chan)
                    self.output(joinchannel)
                    self.s.send(joinchannel)

            if re.search("PRIVMSG", line):
                details = line.split()
                user = details[0].split("!")
                username = user[0][1:].encode('utf-8')
                channel = details[2]
                messagelist = details[3:]
                message = " ".join(messagelist)[1:]
                lower = message.lower().encode('utf-8')
                logging.debug("Putting '{0}' into channel {1} queue".format(lower, channel))
                try:
                    self.channel_queues[channel].put((username, lower))
                except KeyError:
                    logging.warning("No channel {0} to put message '{1}' on".format(channel, lower))

            if re.search(":Closing Link:", line):
                [t.kill_received.set() for t in self.channel_threads.values()]
                self.disconnect()


class IRCChannel(threading.Thread):
    def __init__(self, irc_conn, s, chan, q):
        self.irc_conn = irc_conn
        self.socket = s
        self.channel_name = chan
        self.queue = q
        self.kill_received = threading.Event()
        threading.Thread.__init__(self, name=chan)

    def say(self, message):
        logging.debug("Saying '{0}' on channel {1}".format(message, self.channel_name))
        try:
            self.socket.send("PRIVMSG %s :%s\n" % (self.channel_name, message))
        except socket.error:
            logging.error('Network socket unavailable. Exiting.')
            self.queue = None

    def run(self):
        logging.debug("Thread of class IRCChannel started: '{0}'".format(self.name))
        while not self.kill_received.is_set():
            logging.debug("Reading from queue in thread '{0}'".format(self.name))
            username, lower = self.queue.get()
            logging.debug("Read ('{0}', '{1}') from queue in thread {2}".format(username, lower, self.name))
            if re.search("hello.*sprbt", lower):
                message = "Hello there, %s" %username
                self.say(message, self.channel_name)
            elif lower == "$date":
                self.say("{0}: the time is {1}".format(username, datetime.now()))
            elif lower== "$kill":
                self.socket.send("QUIT :Bot quit\n")
                [t.kill_received.set() for t in threading.enumerate()]
                self.irc_conn.disconnect()
                sys.exit()
            else:
                self.say(lower)

            self.queue.task_done()


def get_thread(threads, server, channel):
    for irc_thread in threads:
        logging.debug('Seeking IRC thread {0} for channel threads'.format(irc_thread.name))
        if irc_thread.host == server:
            logging.debug('Found thread on IRC server {0}'.format(server))
            try:
                chan_thread = irc_thread.channel_threads[channel]
            except KeyError:
                logging.debug('No channel {0} on server {1}'.format(channel, server))
                pass
            else:
                logging.debug('Found thread {0} on IRC server {1}'.format(channel, server))
                return (chan_thread, irc_thread.botname)
    logging.debug('Thread on IRC server {0} not found'.format(server))
    return None


def put_in_queue(thread, recipient, message):
    logging.debug('Putting values ({0}, {1}) in queue of thread {2}'.format(recipient, message, thread.queue))
    thread.queue.put((recipient, message))


