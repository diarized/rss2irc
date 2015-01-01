#!/usr/bin/env python
import socket
import sys
import re
from datetime import datetime
import threading

class IRCConnector(threading.Thread):
    def __init__ (self, host, port, channels):
        self.host = host
        self.port = port
        self.channels = channels
        self.identity = "superbot"
        self.realname = "superbot"
        self.hostname = "supermatt.net"
        self.botname = "SPRBT"
        threading.Thread.__init__(self)

    def output(self, message):
        print("Server: %s\nMessage:%s\n" % (self.host, message))

    def say(self, message, channel):
        self.s.send("PRIVMSG %s :%s\n" % (channel, message))

    def run(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            print 'Failed to create socket'
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


        while True:
            try:
                line = self.s.recv(500)
            except socket.error:
                print "Disconnected"
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
                for chan in self.channels:
                    joinchannel = "JOIN %s\n" %chan
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

                if re.search("hello.*sprbt", lower):
                    message = "Hello there, %s" %username
                    self.say(message, channel)

                if lower == "$date":
                    self.say("%s, the time is %s" %(username, datetime.now()), channel)

                if lower== "$kill":
                    self.s.send("QUIT :Bot quit\n")

            if re.search(":Closing Link:", line):
                sys.exit()


def main():
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
        irc_thread.daemon = True
        irc_thread.start()

threads = []
if __name__ == "__main__":
    main()
    while True:
        try:
            threads = [t.join(1) for t in threads if t is not None and t.isAlive()]
        except KeyboardInterrupt:
            print "Ctrl-c received! Sending kill to threads..."
            for t in threads:
                t.kill_received = True

