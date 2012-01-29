import logging

from bayesrss.models import *

class FeedInfo:
	def __init__(self, key, items, feed, fetchtime):
		self.key = key
		self.items = items
		self.feed = feed
		self.fetchtime = fetchtime
		self.buildtime = None
		self.itemstore = {}
		
class ItemStore:
	def __init__(self, hitCounter, classifier):		   
		"""A map of feed key to a FeedInfo """ 
		self.feedstore = dict()
		
		"""A map of item to an ItemClassification for that item"""
		self.hitCounter = hitCounter
		self.classifier_factory = classifier
		
	def get_dictionary(self, feedkey):
		feed_info = self.get_items(feedkey)
		logging.info("buildtime=%s, fetchtime=%s", feed_info.buildtime, feed_info.fetchtime)
		
		if feed_info.buildtime is None or feed_info.buildtime < feed_info.fetchtime:
			logging.info("Rebuilding item dictionary")
			feed_info.buildtime = datetime.now()
			for key, value in feed_info.itemstore.items():
				if value.isStale():
					del feed_info.itemstore[key]
					logging.info("deleting item " + value.item.title)
			classifier = self.classifier_factory(feedkey)
			for it in feed_info.items:
				if not feed_info.itemstore.has_key(it.hash()):
					feed_info.itemstore[it.hash()] = ItemClassification(it, classifier.spamprob(it.tokens()), it.pub_datetime)
		else:
			logging.info("Returning prebuilt item dictionary")
		return feed_info.itemstore
	
	def get_item(self, feed_key, item_key):
		return self.get_items(feed_key).itemstore[item_key]
		
	def get_feed_infos(self):
		return [self.get_feed_info(feed.key(), feed) for feed in Feed.all()]
		
	def get_feed_info(self, key, feed=None):
		info = self.feedstore.get(key)	
		if info is None:
			if not feed: feed = Feed.get(key)
			if feed is None: logging.error("Couldn't find feed with key " + key)
			info = FeedInfo(key, [], feed, None)
			self.feedstore[key] = info
			logging.info("New FeedInfo created")
		else:
			logging.info("FeedInfo found in cache")
		return info
			
	def get_items(self, key):
		feed_info = self.get_feed_info(key)
		if self.isRecent(feed_info.fetchtime):
			logging.info("Returning items from cache")
		else:
			logging.info("Fetching new items")
			#reload the feed - in case i'm playing with it in the db
			feed_info.feed = Feed.get(key)
			feed_info.items = feed_info.feed.fetch_items(feed_info.items)
			feed_info.fetchtime = datetime.now()
		return feed_info
		
	def isRecent(self, time):
		return (time is not None 
			and time + timedelta(hours=130) > datetime.now())
