# rss2irc
Simple bot that transfers new HackerNews (and others) RSS topics to an IRC channel.

Bot reads feeds.cfg in .INI format that defines a name and an URL of the RSS:

```
[feeds]
HN = https://news.ycombinator.com/rss
TorrentFreak = http://feeds.feedburner.com/Torrentfreak
Pinboard = https://feeds.pinboard.in/rss/popular/
```

It can react on commands like $date and a simple system of plugins was introduced.

Please visit #999net on Freenode to check it out, but in your version use our own, please.
Say "list" to the bot to find out what is currently published.

Its my excersise how to write multithreading programs in Python. Feel free to pull request if you see anything to improve. Thank you.
