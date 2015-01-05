#!/usr/bin/env python

import socket
import sys
import re
from datetime import datetime
import threading
import logging
import Queue
from pprint import pprint

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)

DEBUG = True
REFRESH_TIME = 30
RECONNECT_TIME = REFRESH_TIME/2

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
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Define  IRC Socket

        while attempts:
            try:
                self.s.connect((self.network,self.port)) #Connect to Server
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

    def run(self):
        logging.info("Thread of class IRCConnector started: '{0}'".format(self.name))
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            logging.error('Failed to create socket')
            sys.exit()

        remote_ip = socket.gethostbyname(self.host)
        self.output(remote_ip)

        self.s.connect((remote_ip, self.port))
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
                username = user[0][1:]
                channel = details[2]
                messagelist = details[3:]
                message = " ".join(messagelist)[1:]
                lower = message.lower()
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
        self.socket.send("PRIVMSG %s :%s\n" % (self.channel_name, message))

    def run(self):
        logging.debug("Thread of class IRCChannel started: '{0}'".format(self.name))
        while not self.kill_received.is_set():
            username, lower = self.queue.get()
            if re.search("hello.*sprbt", lower):
                message = "Hello there, %s" %username
                self.say(message, self.channel_name)

            if lower == "$date":
                self.say("{0}: the time is {1}".format(username, datetime.now()))

            if lower== "$kill":
                self.socket.send("QUIT :Bot quit\n")
                [t.kill_received.set() for t in threading.enumerate()]
                self.irc_conn.disconnect()
                sys.exit()

            self.queue.task_done()


def main():
    threads = []
    irc_connections = [{
        "host": "irc.freenode.net",
        "port": 6667,
        "channels": ["#999net", "#999ned"]
    },
    ]

    for irc in irc_connections:
        irc_thread = IRCConnector(irc['host'], irc['port'], irc['channels'])
        threads.append(irc_thread)
        irc_thread.daemon = True
        irc_thread.start()

    logging.debug("All server threads started.")
    [t.join() for t in threads]
    

if __name__ == "__main__":
    main()
