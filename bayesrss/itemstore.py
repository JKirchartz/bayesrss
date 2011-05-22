import urllib2
import logging
from xml.etree import cElementTree as etree

from bayesrss.models import *

class ItemStore():
    """The last time the itemstore was rebuilt"""
    buildtime = None
    
    """A map of feed key to a list of current items being served in that feed """ 
    feedstore = {}
    
    """A map of item to an ItemClassification for that item"""
    #TODO make this multi-feed friendly
    itemstore = {}

    hitCounter = None
    classifier = None
    
    def __init__(self, hitCounter, classifier):
        self.hitCounter = hitCounter
        self.classifier = classifier
        
    def getDictionary(self, feedkey):
        items, fetchtime = self.get_items(feedkey)
        logging.info("buildtime="+str(self.buildtime)+" fetchtime="+str(fetchtime))
        if self.buildtime is None or buildtime < fetchtime:
            self.buildtime = datetime.now()
            for key, value in self.itemstore.items():
                if value.isStale():
                    del self.itemstore[key]
            for it in items:
                if not self.itemstore.has_key(it.hash()):
                    self.itemstore[it.hash()] = ItemClassification(it, self.classifier.spamprob(it.getTokens()), fetchtime)
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
            items.append(item)
        return items
    
    def get_items(self, key):
        if self.feedstore.has_key(key):
            items, fetchTime = self.feedstore[key]
            if self.isRecent(fetchTime):
                return self.feedstore[key]
        feed = Feed.get(key)
        items = self.get_new_items(feed.link)
        self.feedstore[key] = items, datetime.now()
        return items, datetime.now()      
        
    def isRecent(self, time):
        return (time is not None 
            and time + timedelta(hours=2) > datetime.now())
