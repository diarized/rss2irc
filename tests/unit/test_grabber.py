#!/usr/bin/env python

import unittest
import Queue
import grabber

class TestGrabber(unittest.TestCase):
    def setUp(self):
        self.feed_queue = Queue.Queue()
        self.grabber = grabber.Grabber(self.feed_queue)

    def test_clear_tables(self):
        self.grabber.clear_tables('AA')
        feed_name, action = self.grabber.feed_queue.get()
        self.assertEqual(feed_name, 'AA')
        self.assertEqual(action, 'clear_table')

    def test_read_config(self):
        self.grabber.read_config()
        feed_name = self.grabber.feeds[0][0]
        self.assertEqual(feed_name, 'hn')

if __name__ == '__main__':
        unittest.main()
