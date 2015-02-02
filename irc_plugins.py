import ConfigParser

def list(arg=None):
    cp = ConfigParser.ConfigParser()
    cp.read(CONFIG_FILE)
    feeds = cp.items('feeds')
    return feeds.replace('\n', ' ')

