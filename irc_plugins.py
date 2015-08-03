import ConfigParser
import pprint
import grabber

def list(arg=None):
    cp = ConfigParser.ConfigParser()
    cp.read(grabber.CONFIG_FILE)
    feeds = cp.items('feeds')
    return pprint.pformat(feeds).replace('\n', ' ')

def search(arg):
    return "Searched for {}".format(arg)
