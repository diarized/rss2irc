#!/bin/bash

kill -9 `ps | grep [p]ython | awk '{ print $1; }'`
sleep 1
./rss2irc.py > ./rss2irc.log 2>&1 &
tail -F ./rss2irc.log 
