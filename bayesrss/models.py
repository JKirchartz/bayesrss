import re
import logging
from datetime import datetime, timedelta

from BeautifulSoup import BeautifulStoneSoup
from google.appengine.ext import db
from jhash import jhash

from bayesrss.safewords import safewords

splitter = re.compile("[\W]")
	
class Item():
	def __init__(self, title, description, link, guid):
		self.title = title
		self.description = description
		self.link = link
		self.guid = guid
		self._tokens = None
		self._hash = None
		
	def tokens(self):
		return self._do_tokens([self.title, self.description])
		
	def _do_tokens(self, strings):
		if self._tokens is None:
			toks = reduce(lambda toks, str: toks + splitter.split(str.lower()), strings, [])
			split = filter(None, toks)
			#logging.info("Pre-cleaned tokens: " + str(split))
			self._tokens = list(set(split) - safewords)
			#logging.info("safewords reduced from " + str(len(split)) + " to " + str(len(self._tokens)))
		return self._tokens
		
	def hash(self):
		if self._hash is None:
			self._hash = str(jhash(self.title + self.description))
		return self._hash

class SeekItem(Item):
	def __init__(self, item, minimum, maximum):
		self.raw_title = item.title
		self.title = item.title + '	 [$' + str(minimum) + ' - $' + str(maximum) + ']'
		self.link = item.link
		self.pub_datetime = datetime.now()
		self._tokens = None
		self._hash = None
		#TODO strip html tags
		self.raw_description = item.description
		self.description = "<html><body>" + item.description + "</body></html>"
		
	def tokens(self):
		return self._do_tokens([self.raw_title, self.raw_description])
		
	def hash(self):
		if self._hash is None:
			#Use raw title because the pay details will occaisonally be incorrect, and worse: change
			self._hash = str(jhash(self.raw_title + self.description))
		return self._hash

			
#Import down here because circular dependancy between fetcher and us
from bayesrss.fetcher import *

class Feed(db.Model):
	title = db.StringProperty()
	description = db.StringProperty(multiline=True)
	link = db.StringProperty()
	
	is_aggregated = db.BooleanProperty()
	is_deduplicated = db.BooleanProperty()
	is_filtered = db.BooleanProperty()
	is_seek_mined = db.BooleanProperty()
	
	def fetch_items(self):
		if self.is_seek_mined:
			return fetch_seek_items(self.link)
		else:
			return fetch_items(self.link)										
			
class Hit(db.Model):
	headers = db.StringProperty()
	xmlServiceHitCount = db.IntegerProperty(default=0)
	fetchFeedCount = db.IntegerProperty(default=0)
	since = db.DateTimeProperty(auto_now_add=True)
	
	def countXmlServiceHit(self, headers):
		self.xmlServiceHitCount += 1
		#self.headers = str(headers)
		#self.put()
		
	def countFetchFeedHit(self):
		self.fetchFeedCount += 1
		#self.put()
	
class WordInfoEntity(db.Model):
	word = db.StringProperty()
	spamcount = db.IntegerProperty()
	hamcount = db.IntegerProperty()
	
class SpamCounts(db.Model):
	nham = db.IntegerProperty()
	nspam = db.IntegerProperty()
	
class ItemClassification(object):	
	def __init__(self, item, probability, pub_time):
		self.item = item
		self.probability = probability
		self.spam = False
		self.classified = False
		self.pub_time = pub_time
	
	def isStale(self):
		return self.pub_time + timedelta(days=1) < datetime.now()

