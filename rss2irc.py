#!/usr/bin/env python

import feed

def main():
    storage = feed.Feeder()
    storage.daemon = True
    storage.start()
    storage.join()

if __name__ == "__main__":
    main()
