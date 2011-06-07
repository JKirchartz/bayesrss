import logging

from bayesrss.models import *
from bayesrss.fetcher import *

class FeedInfo:
    def __init__(self, items, link, fetch_function, fetchtime):
        self.items = items
        self.link = link
        self.fetch_function = fetch_function
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
        
    def get_dictionary(self, feedkey):
        feed_info = self.get_items(feedkey)
        logging.info("buildtime="+str(self.buildtime) + " fetchtime="+str(feed_info.fetchtime))
        
        if self.buildtime is None or self.buildtime < feed_info.fetchtime:
            logging.info("Rebuilding item dictionary")
            self.buildtime = datetime.now()
            for key, value in feed_info.itemstore.items():
                if value.isStale():
                    del feed_info.itemstore[key]
            classifier = self.classifier(feedkey)
            for it in feed_info.items:
                if not feed_info.itemstore.has_key(it.hash()):
                    feed_info.itemstore[it.hash()] = ItemClassification(it, classifier.spamprob(it.tokens()), it.pub_datetime)
        else:
            logging.info("Returned prebuilt item dictionary")
        return feed_info.itemstore
    
    def get_item(self, feed_key, item_key):
        return self.get_items(feed_key).itemstore[item_key]
    
    def get_items(self, key):
        if self.feedstore.has_key(key):
            logging.info("get_items: Feed was found in feedstore")
            feed_info = self.feedstore[key]
            if self.isRecent(feed_info.fetchtime):
                logging.info("get_items: Returning items from cache")
            else:
                logging.info("get_items: Fetched new items")
                feed_info.items = feed_info.fetch_function(feed_info.link)
                feed_info.fetchtime = datetime.now()
            return feed_info
            
        feed = Feed.get(key)
        if feed.is_seek_mined:
            logging.info("Found a seek feed: " + feed.title)
            feed_item = FeedInfo(fetch_seek_items(feed.link), feed.link, fetch_seek_items, datetime.now())
        else:
            logging.info("Found a NON-seek feed: " + feed.title)
            feed_item = FeedInfo(fetch_items(feed.link), feed.link, fetch_items, datetime.now())
        
        self.feedstore[key] = feed_item
        logging.info("get_items: created new FeedInfo")
        return feed_item  
        
    def isRecent(self, time):
        return (time is not None 
            and time + timedelta(hours=2) > datetime.now())
