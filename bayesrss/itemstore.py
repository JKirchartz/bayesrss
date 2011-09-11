import logging

from bayesrss.models import *

class FeedInfo:
    def __init__(self, items, feed, fetchtime):
        self.items = items
        self.feed = feed
        self.fetchtime = fetchtime
        self.buildtime = None
        self.itemstore = {}
        
class ItemStore:
    def __init__(self, hitCounter, classifier):        
        """A map of feed key to a list of current items being served in that feed """ 
        self.feedstore = dict()
        
        """A map of item to an ItemClassification for that item"""
        self.hitCounter = hitCounter
        self.classifier_factory = classifier
        
    def get_dictionary(self, feedkey):
        feed_info = self.get_items(feedkey)
        logging.info("get_dictionary: buildtime="+str(feed_info.buildtime) + " fetchtime="+str(feed_info.fetchtime))
        
        if feed_info.buildtime is None or feed_info.buildtime < feed_info.fetchtime:
            logging.info("get_dictionary: Rebuilding item dictionary")
            feed_info.buildtime = datetime.now()
            for key, value in feed_info.itemstore.items():
                if value.isStale():
                    del feed_info.itemstore[key]
                    logging.info("get_dictionary: deleting item " + value.item.title)
            classifier = self.classifier_factory(feedkey)
            for it in feed_info.items:
                if not feed_info.itemstore.has_key(it.hash()):
                    feed_info.itemstore[it.hash()] = ItemClassification(it, classifier.spamprob(it.tokens()), it.pub_datetime)
        else:
            logging.info("get_dictionary: Returned prebuilt item dictionary")
        return feed_info.itemstore
    
    def get_item(self, feed_key, item_key):
        return self.get_items(feed_key).itemstore[item_key]
        
    def get_feed_info(self, key):
        if self.feedstore.has_key(key):
            return self.feedstore[key]
        else:
            return None
            
    def get_items(self, key):
        feed_info = self.get_feed_info(key)
        if feed_info is not None:
            logging.info("get_items: Feed was found in feedstore")
            if self.isRecent(feed_info.fetchtime):
                logging.info("get_items: Returning items from cache")
            else:
                logging.info("get_items: Fetched new items")
                feed = Feed.get(key)
                feed_info.feed = feed
                feed_info.items = feed_info.feed.fetch_items()
                feed_info.fetchtime = datetime.now()
            return feed_info
        else:   
            feed = Feed.get(key)
            feed_item = FeedInfo(feed.fetch_items(), feed, datetime.now())            
            self.feedstore[key] = feed_item
            logging.info("get_items: created new FeedInfo")
            return feed_item
        
    def isRecent(self, time):
        return (time is not None 
            and time + timedelta(hours=2) > datetime.now())
