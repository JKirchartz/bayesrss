import urllib2
import logging
from xml.etree import cElementTree as etree
from email.utils import parsedate

from bayesrss.models import *

class FeedInfo:
    def __init__(self, items, fetchtime):
        self.items = items
        self.fetchtime = fetchtime
        self.itemstore = {}
        
class ItemStore:
    def __init__(self, hitCounter, classifier):
        """The last time the itemstore was rebuilt"""
        self.buildtime = None
        
        """A map of feed key to a list of current items being served in that feed """ 
        self.feedstore = dict()
        
        """A map of item to an ItemClassification for that item"""
        self.hitCounter = hitCounter
        self.classifier = classifier
        
    def getDictionary(self, feedkey):
        feed_info = self.get_items(feedkey)
        logging.info("buildtime="+str(self.buildtime) + " fetchtime="+str(feed_info.fetchtime))
        
        if self.buildtime is None or self.buildtime < feed_info.fetchtime:
            logging.info("Rebuilding item dictionary")
            self.buildtime = datetime.now()
            for key, value in feed_info.itemstore.items():
                if value.isStale():
                    del feed_info.itemstore[key]
            classifier = self.classifier()
            for it in feed_info.items:
                if not feed_info.itemstore.has_key(it.hash()):
                    feed_info.itemstore[it.hash()] = ItemClassification(it, classifier.spamprob(it.getTokens()), it.pub_datetime)
        else:
            logging.info("Returned prebuilt item dictionary")
        return feed_info.itemstore
    
    def getItem(self, key):
        return self.itemstore[key]
            
    def get_new_items(self, key):
        feed = Feed.get(key)
        self.hitCounter.countFetchFeedHit()
        xml = urllib2.urlopen(feed.link).read()
        items = []
        tree = etree.fromstring(xml)
        for node in tree.find("channel").findall("item"):
            item = Item(title = node.find("title").text,
                        description = node.find("description").text,
                        link = node.find("link").text)
            item.pubdate = node.find("pubDate").text
            tupl = parsedate(item.pubdate)
            item.pub_datetime = datetime(*tupl[:6])
            items.append(item)
        return items
    
    def get_items(self, key):
        if self.feedstore.has_key(key):
            logging.info("get_items: Feed was found in feedstore")
            feed_info = self.feedstore[key]
            if self.isRecent(feed_info.fetchtime):
                logging.info("get_items: Returning items from cache")
            else:
                logging.info("get_items: Fetched new items")
                feed_info.items = self.get_new_items(key)
                feed_info.fetchtime = datetime.now()
            return feed_info
        feed_item = FeedInfo(self.get_new_items(key), datetime.now())
        self.feedstore[key] = feed_item
        logging.info("get_items: created new FeedInfo")
        return feed_item  
        
    def isRecent(self, time):
        return (time is not None 
            and time + timedelta(hours=2) > datetime.now())
