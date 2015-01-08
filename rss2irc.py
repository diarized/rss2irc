#!/usr/bin/env python

import feed_storage

def main():
    storage = feed_storage.FeedStorage()
    storage.daemon = True
    storage.start()
    storage.join()

if __name__ == "__main__":
    main()
