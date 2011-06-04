import urllib2
from xml.etree import cElementTree as etree

from email.utils import parsedate

from bayesrss.models import *

def fetch_items(key):
    feed = Feed.get(key)
    #self.hitCounter.countFetchFeedHit()
    xml = urllib2.urlopen(feed.link).read()                           
    items = []
    tree = etree.fromstring(xml)
    for node in tree.find("channel").findall("item"):
        item = Item(title = node.find("title").text,
                    description = node.find("description").text,
                    link = node.find("link").text)
        guid = node.find("guid")
        if guid is not None:
            item.guid = guid.text
        item.pubdate = node.find("pubDate").text
        tupl = parsedate(item.pubdate)
        item.pub_datetime = datetime(*tupl[:6])
        items.append(item)
    return items
    
def fetch_seek_items():
    items_and_pay = {}
    step = 2000
    for i in range(50000, 120000, step):
        salary_range = str(i) + "-" + str(i + step)
        link = "http://rss.seek.com.au/JobSearch?catlocation=1004&catindustry=6281&catoccupation=6287&Keywords=java&salary=" + salary_range
        items = fetch_items(link)
        for it in items:
            if items_and_pay.has_key(it.guid):
                items_and_pay[it.guid].maximum = i + step
            else:
                it.minimum = i
                it.maximum = i + step
                items_and_pay[it.guid] = it
    return items_and_pay.values()
