import urllib2
import logging
from xml.etree import cElementTree as etree
from datetime import datetime
from email.utils import parsedate

#from bayesrss.models import *

class Item:
    def __init__(self, title, description, link):
        self.title = title
        self.description = description
        self.link = link
        
def fetch_items(link):
    #self.hitCounter.countFetchFeedHit()
    xml = urllib2.urlopen(link).read()                           
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
        
def fetch_seek_items(link):
    start = datetime.now()
    items_and_pay = {}
    step = 5000
    for i in range(60000, 120000, step):
        salary_range = str(i) + "-" + str(i + step)
        link = link + "&salary=" + salary_range
        logging.info("Fetching for pay range $" + str(i) + " to $" + str(i + step))
        items = fetch_items(link)
        logging.info("Found " + str(len(items)) + " items")
        for it in items:
            if items_and_pay.has_key(it.guid):
                items_and_pay[it.guid].maximum = i + step
            else:
                it.minimum = i
                it.maximum = i + step
                items_and_pay[it.guid] = it
    logging.info("Found " + str(len(items_and_pay)) + ", took " + str(datetime.now() - start))
    return items_and_pay.values()
