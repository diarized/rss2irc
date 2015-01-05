#!/usr/bin/env python

import socket
import sys
import re
from datetime import datetime
import threading
import logging
import Queue

logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s %(levelname)s] (%(threadName)-10s) %(message)s',
)

class IRCConnector(threading.Thread):
    def __init__ (self, host, port, channels):
        self.host = host
        self.port = port
        self.channels = channels
        self.identity = "superbot"
        self.realname = "superbot"
        self.hostname = "supermatt.net"
        self.botname = "SPRBT"
        self.joinable = False
        self.channel_queues = {}
        self.channel_threads = []
        threading.Thread.__init__(self)

    def output(self, message):
        logging.info("Server: %s\nMessage:%s\n" % (self.host, message))

    def run(self):
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
            q = Queue.Queue()
            self.channel_queues[chan] = q
            channel_thread = IRCChannel(self.s, chan, q)
            self.channel_threads.append(channel_thread)
            channel_thread.daemon = True
            channel_thread.start()

        while True:
            try:
                line = self.s.recv(500)
            except socket.error:
                logging.error("Disconnected")
                sys.exit()
            if line:
                self.output(line)
            line.strip()
            splitline = line.split(" :")
            if splitline[0] == "PING":
                pong = "PONG {0}".format(splitline[1])
                self.output(pong)
                self.s.send(pong)

            if re.search(":End of /MOTD command.", line):
                self.joinable = True
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
                sys.exit()


class IRCChannel(threading.Thread):
    def __init__(self, s, chan, q):
        self.socket = s
        self.channel_name = chan
        self.queue = q
        threading.Thread.__init__(self)

    def say(self, message):
        logging.debug("Saying '{0}' on channel {1}".format(message, self.channel_name))
        self.socket.send("PRIVMSG %s :%s\n" % (self.channel_name, message))

    def run(self):
        while True:
            username, lower = q.get()
            if re.search("hello.*sprbt", lower):
                message = "Hello there, %s" %username
                self.say(message, self.channel_name)

            if lower == "$date":
                self.say("%s: the time is %s" %(username, datetime.now()), self.channel_name)

            if lower== "$kill":
                self.socket.send("QUIT :Bot quit\n")
                self.socket.close()


def main():
    threads = []
    irc_connections = [{
        "host": "irc.freenode.net",
        "port": 6667,
        "channels": ["#999net", "#999ned"]
    },
#    {
#        "host": "localhost",
#        "port": 6667,
#        "channels": ["#999net", "#999ned"]
#    },
    ]

    for irc in irc_connections:
        irc_thread = IRCConnector(irc['host'], irc['port'], irc['channels'])
        threads.append(irc_thread)
        irc_thread.start()


if __name__ == "__main__":
    main()
