import urllib2
import logging
from xml.etree import cElementTree as etree
from email.utils import parsedate

from bayesrss.models import *

class ItemStore:
    def __init__(self, hitCounter, classifier):
        """The last time the itemstore was rebuilt"""
        self.buildtime = None
        
        """A map of feed key to a list of current items being served in that feed """ 
        self.feedstore = dict()
        
        """A map of item to an ItemClassification for that item"""
        #TODO make this multi-feed friendly
        self.itemstore = dict()
        self.hitCounter = hitCounter
        self.classifier = classifier
        
    def getDictionary(self, feedkey):
        items, fetchtime = self.get_items(feedkey)
        logging.info("buildtime="+str(self.buildtime) + " fetchtime="+str(fetchtime))
        
        if self.buildtime is None or self.buildtime < fetchtime:
            logging.info("Rebuilding item dictionary")
            self.buildtime = datetime.now()
            for key, value in self.itemstore.items():
                if value.isStale():
                    del self.itemstore[key]
            classifier = self.classifier()
            for it in items:
                if not self.itemstore.has_key(it.hash()):
                    self.itemstore[it.hash()] = ItemClassification(it, classifier.spamprob(it.getTokens()), it.pub_datetime)
        else:
            logging.info("Returned prebuilt item dictionary")
        return self.itemstore
    
    def getItem(self, key):
        return self.itemstore[key]
            
    def get_new_items(self, url):
        self.hitCounter.countFetchFeedHit()
        xml = urllib2.urlopen(url).read()
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
            logging.info("Feed was found in feedstore")
            items, fetchTime = self.feedstore[key]
            if self.isRecent(fetchTime):
                logging.info("Returning items from cache")
                return self.feedstore[key]
        feed = Feed.get(key)
        items = self.get_new_items(feed.link)
        self.feedstore[key] = items, datetime.now()
        logging.info("Fetched new items")
        return items, datetime.now()      
        
    def isRecent(self, time):
        return (time is not None 
            and time + timedelta(hours=2) > datetime.now())
