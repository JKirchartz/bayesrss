import os,sys
import urllib2,urllib,urlparse,cgi
import logging
from xml.etree import cElementTree as etree
from datetime import datetime, timedelta
from operator import attrgetter

from bayesrss.models import *
from bayesrss.itemstore import ItemStore
from bayesrss.classification import *

from google.appengine.dist import use_library
use_library('django', '1.2')

# Google App Engine imports.
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

SPAM_THRESHOLD = 0.9
HAM_THRESHOLD = 0.15
HIT_COUNTER_KEY = "key"
SPAM_COUNT_KEY = "singleton"
HTML_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'items.html')

itemstore = None
hitCounter = None
start_time = datetime.now()
classifier = None

class ViewXmlFeedHam(webapp.RequestHandler):
	def get(self):
		do_filtered_xml(self.request, self.response, True, maxProb=HAM_THRESHOLD)
		
class ViewXmlFeedSpam(webapp.RequestHandler):
	def get(self):
		do_filtered_xml(self.request, self.response, True, minProb=SPAM_THRESHOLD)
	
class ViewXmlFeedUnknown(webapp.RequestHandler):
	def get(self):
		do_filtered_xml(self.request, self.response, True, HAM_THRESHOLD, SPAM_THRESHOLD)

class ViewXmlFeedAll(webapp.RequestHandler):
	def get(self):
		do_filtered_xml(self.request, self.response, False)
		
def do_filtered_xml(request, response, do_filter, minProb=0, maxProb=1):
	hitCounter.countXmlServiceHit(request.headers)
	key = request.get('key')
	feed = Feed.get(key)
	items = itemstore.get_items(key).items
	
	filtered = []
	if do_filter:
		classifier = get_classifier(key)
		for i in items:
			spam_prob = classifier.spamprob(i.tokens())
			if minProb < spam_prob and spam_prob < maxProb:
				filtered.append(i)
		logging.info("Returning filtered xml: " + str(len(filtered)))
	else:
		filtered += items
		logging.info("Returning unfiltered xml: " + str(len(filtered)))
		
	response.headers['Content-Type'] = 'text/xml'
	response.out.write(
		template.render(path('feed.xml'), {"items":filtered, "feed":feed, "request":request}))
		
def path(filename):
	return os.path.join(os.path.dirname(__file__), filename)
	
	
class ViewFeedHtml(webapp.RequestHandler):	  
	def get(self):
		key = self.request.get('key')
		item_dict = itemstore.get_dictionary(key)
		item_list = item_dict.values()
		item_list.sort(key=attrgetter('pub_time'), reverse=True)
		self.response.headers['Content-Type'] = 'text/html'
		self.response.out.write(
			template.render(HTML_TEMPLATE_PATH, {"item_list":item_list, "count":len(item_list), "feed":key}))

class CleanFeedCache(webapp.RequestHandler):
	def get(self):
		key = self.request.get('key')
		feed_info = itemstore.get_feed_info(key)
		feed_info.fetchtime = None
		self.response.out.write("All good")
	
class CacheFeedHandler(webapp.RequestHandler):
	def get(self):
		key = self.request.get('key')
		feed_info = itemstore.get_feed_info(key)
		feed_info.fetchtime = None
		itemstore.get_items(key)
		
class EditFeeds(webapp.RequestHandler):
	def get(self):
		Feed.get(self.request.get('key')).delete()
		self.redirect("/feeds")


class ViewTest(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
#		 self.response.out.write(str(get_classifier(feed).nspam) + "\n")
#		 self.response.out.write(str(get_classifier(feed).nham))

		self.response.out.write(dir(urlparse))
#		 items = get_new_items('http://www.abc.net.au/news/syndicate/breakingrss.xml')
#		 self.response.out.write(hash(items[0]))

class ViewHits(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		if hitCounter:
			self.response.out.write("XmlCount=" + str(hitCounter.xmlServiceHitCount) + "\n")
			self.response.out.write("FetchCount=" + str(hitCounter.fetchFeedCount) + "\n")
			self.response.out.write("Uptime=" + str(datetime.now() - start_time) + "\n\n")
			if hitCounter.headers:
				self.response.out.write("Headers=" + hitCounter.headers)
		else:
			self.response.out.write("No hits")


class ViewFeeds(webapp.RequestHandler):
	def get(self):
		feeds = db.GqlQuery("SELECT * FROM Feed WHERE ANCESTOR IS :1", get_feed_key())
		self.response.headers['Content-Type'] = 'text/html'
		self.response.out.write(template.render(path("feeds.html"), {"feeds" : feeds}))

	def post(self):
		link = self.request.get('link')
		feed = Feed(parent = get_feed_key(),
					link = link)
		get_feed_details(feed)
		feed.put()
		self.redirect("/feeds")

class ViewSeekFeeds(webapp.RequestHandler):
	def get(self):
		feeds = db.GqlQuery("SELECT * FROM Feed WHERE ANCESTOR IS :1", get_feed_key())
		self.response.headers['Content-Type'] = 'text/html'
		self.response.out.write(template.render(path("seek.html"), {"feeds" : feeds, "request":self.request}))

	def post(self):
		link = self.request.get('link')
		if link.find('salary') >= 0:
			logging.info('Stripping salary param from: ' + link)
			split = urlparse.urlsplit(link)
			params = dict(cgi.parse_qsl(split.query))
			del params['salary']
			link = split.scheme + "://" + split.netloc + split.path + '?' + urllib.urlencode(params)
			logging.info('Finished stripping: ' + link)
		feed = Feed(parent = get_feed_key(),
					link = link)
		get_feed_details(feed)
		feed.put()
		self.redirect("/feeds/seek")
		
class UnClassifyItem(webapp.RequestHandler):
	def post(self):
		classify(self, False)
		
class ClassifyFeedItems(webapp.RequestHandler):
	def post(self):
		classify(self, True)

def classify(handler, learn):
	action = handler.request.get("action")
	id = handler.request.get("id")
	feed_key = handler.request.get("feed")
	isSpam = action == 'spam'
	logging.info("Classifying. id="+id+" feed="+feed_key+" action="+action+" learn="+str(learn))
	try:
		value = itemstore.get_item(feed_key, id)
	except:
		logging.error("No item found with ID=" + id + "\n")
		logging.error("Items:\n" + str(itemstore.get_dictionary(feed_key)))
		logging.error(sys.exc_info())
		handler.error(500)
		return
		
	classifier = get_classifier(feed_key)
	if learn:
		classifier.learn(value.item.tokens(), isSpam)
	else:
		classifier.unlearn(value.item.tokens(), value.spam)
	persist_classifier(classifier, feed_key)
	value.probability = classifier.spamprob(value.item.tokens())
	logging.info("SPAM" if isSpam else "HAM")
	logging.info(value.item.tokens())
	logging.info("prob="+str(value.probability))
	value.classified = learn
	value.spam = isSpam
	handler.response.out.write(value.probability)


application = webapp.WSGIApplication(
		[('/feeds', ViewFeeds),
		 ('/feeds/seek', ViewSeekFeeds),
		 ('/feed/delete', EditFeeds),
		 ('/feed/items', ViewFeedHtml),
		 ('/feed/xml', ViewXmlFeedAll),
		 ('/feed/xml/spam', ViewXmlFeedSpam),
		 ('/feed/xml/ham', ViewXmlFeedHam),
		 ('/feed/xml/unknown', ViewXmlFeedUnknown),
		 ('/feed/classify', ClassifyFeedItems),
		 ('/feed/unclassify', UnClassifyItem),
		 ('/feed/hits', ViewHits),
		 ('/feed/test', ViewTest),
		 ('/feed/clean', CleanFeedCache),
		 ('/feed/cache', CacheFeedHandler)],
		debug=True)

def main():
	global itemstore
	if itemstore is None:
		logging.info("RELOADING MAIN")
		load_hitcounter()
		#get_classifier()
		itemstore = ItemStore(hitCounter, get_classifier)
	#do_stuff()
	run_wsgi_app(application)

def make_seek_feeds():
	feeds = Feed.all()
	for f in feeds:
		logging.info("Looking at feed " + f.title)
		logging.info(f.link)
		if f.link.startswith("http://rss.seek.com.au"):
			logging.info("Found a seek feed")
			f.is_seek_mined = True
			f.link = f.link.lstrip()
			f.put()
			
def do_stuff():
	feed = Feed.get('aghiYXllc3Jzc3IXCxIERmVlZCIDYWxsDAsSBEZlZWQYAQw')
	logging.info("Loaded feed " + str(feed))
	#wordInfos = db.GqlQuery("SELECT * FROM WordInfoEntity WHERE ANCESTOR IS :1", feed.key())
	#for info in wordInfos:
	#	 logging.info(str(info.word))
	count = 0
	wordInfos = WordInfoEntity.all()
	for w in wordInfos:
		count += 1
	logging.info("Loaded " + str(count) + " word infos")
	entities = []
	for info in wordInfos:
		if not info.parent == feed:
			entities.append(WordInfoEntity(
				parent=feed,
				key_name=str(feed.key()) + "_" + info.word, 
				word=info.word, 
				spamcount=info.spamcount, 
				hamcount=info.hamcount))
	logging.info("Only " + str(len(entities)) + "being persisted")
	o = []
	count = 0
	for e in entities:
		o.append(e)
		count += 1
		if count > 100:
			db.put(o)
			count = 0
			o.clear()
	db.put(o)
	#db.put(entities)
	logging.info("Length: " + str(count) + " of " + str(all)) 
				
def load_hitcounter():
	global hitCounter
	hitCounter = Hit.get_or_insert(HIT_COUNTER_KEY)

def get_feed_details(feed):
	#TODO fix detail fetch
	if feed.link.startswith("http://www.seek.com.au"):
		logging.info("Found a seek feed")
		feed.is_seek_mined = True
		feed.title = 'Untitled Seek Feed'
		feed.description = 'Unable to fetch feed description'
	else:
		xml = urllib2.urlopen(feed.link).read()
		tree = etree.fromstring(xml)
		channel = tree.find("channel")

		if channel:
			feed.title = "bayesrss: " + channel.find("title").text
			feed.description = channel.find("description").text

	
def get_feed_key():
	return db.Key.from_path("Feed", "all")

if __name__ == '__main__':
	main()
