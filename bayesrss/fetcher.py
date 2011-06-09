import urllib2
import logging
from xml.etree import cElementTree as etree
from datetime import datetime
from email.utils import parsedate

from bayesrss.models import *

from google.appengine.api import urlfetch

#class Item:
#    def __init__(self, title, description, link):
#        self.title = title
#        self.description = description
#        self.link = link
        
def fetch_items(link):
    #self.hitCounter.countFetchFeedHit()
    xml = urllib2.urlopen(link).read()                           
    return parse_feed_xml(xml)
    
def parse_feed_xml(xml):
    items = []
    tree = etree.fromstring(xml)
    for node in tree.find("channel").findall("item"):
        item = Item(title = node.find("title").text,
                    description = node.find("description").text,
                    link = node.find("link").text)
        item.guid = safe_get_element(node, "guid")
        item.pubdate = safe_get_element(node, "pubDate")
        if item.pubdate is not None:
            tupl = parsedate(item.pubdate)
            item.pub_datetime = datetime(*tupl[:6])
        items.append(item)
    return items
    
def safe_get_element(node, element):
    el = node.find(element)
    if el is not None:
        return el.text
    else:
        return None
        
def fetch_seek_items(link_prefix):
    start = datetime.now()
    items_and_pay = {}
    def callback(rpc, min, max):
        xml = rpc.get_result().content
        items = parse_feed_xml(xml)
        logging.info("Found " + str(len(items)) + " items for range $" + str(min) + " to $" + str(max))
        for it in items:
            if it.title == 'Unfortunately SEEK could not generate this feed':
                continue
            if items_and_pay.has_key(it.guid):
                items_and_pay[it.guid].mins.append(min)
                items_and_pay[it.guid].maxs.append(max)
            else:
                it.mins = [min]
                it.maxs = [max]
                items_and_pay[it.guid] = it
    
    rpcs = []
    step = 5000
    for i in range(60000, 120000, step):
        salary_range = str(i) + "-" + str(i + step)
        link = link_prefix + "&salary=" + salary_range
        rpc = urlfetch.create_rpc()
        rpc.callback = lambda: callback(rpc, i, i + step)
        urlfetch.make_fetch_call(rpc, link)
        rpcs.append(rpc)
    for rpc in rpcs:
        rpc.wait()
    
    logging.info("Found " + str(len(items_and_pay)) + ", took " + str(datetime.now() - start))
    items = items_and_pay.values()
    seek_items = []
    for it in items:
        it.minimum = min(it.mins)
        it.maximum = max(it.maxs)
        seek_it = SeekItem(it)
        seek_items.append(seek_it)
    return seek_items

