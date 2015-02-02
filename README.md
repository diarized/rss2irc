# rss2irc
IRC feed from RSS

Simple bot that transfers new HackerNews (and others) RSS topics to an IRC channel.

Bot reads feeds.cfg in .INI format

```
[feeds]
HN = https://news.ycombinator.com/rss
TorrentFreak = http://feeds.feedburner.com/Torrentfreak
Pinboard = https://feeds.pinboard.in/rss/popular/
```

It can react on commands $date, $kill and a simple system of plugins was introduced.
Say "list" to the bot to check it out.
