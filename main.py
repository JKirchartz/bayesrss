import os,sys
import urllib2
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

SPAM_THRESHOLD = 0.95
HAM_THRESHOLD = 0.1
HIT_COUNTER_KEY = "key"
SPAM_COUNT_KEY = "singleton"
FEED_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'feed.xml')
HTML_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'items.html')

itemstore = None
hitCounter = None
start_time = datetime.now()
classifier = None

class ViewXmlFeedHam(webapp.RequestHandler):
    def get(self):
        do_filtered_xml(self.request, self.response, 0, HAM_THRESHOLD)
        
class ViewXmlFeedSpam(webapp.RequestHandler):
    def get(self):
        do_filtered_xml(self.request, self.response, SPAM_THRESHOLD, 1)
    
class ViewXmlFeedUnknown(webapp.RequestHandler):
    def get(self):
        do_filtered_xml(self.request, self.response, HAM_THRESHOLD, SPAM_THRESHOLD)

class ViewXmlFeedAll(webapp.RequestHandler):
    def get(self):
        do_filtered_xml(self.request, self.response, 0, 1)
        
def do_filtered_xml(request, response, minProb, maxProb):
    hitCounter.countXmlServiceHit(request.headers)
    key = request.get('key')
    feed = Feed.get(key)
    items, time = itemstore.get_items(key)
    
    filtered = []
    classifier = get_classifier(feed)
    for i in items:
        spam_prob = classifier.spamprob(i.getTokens())
        if minProb < spam_prob and spam_prob < maxProb:
            filtered.append(i)
            
    response.headers['Content-Type'] = 'text/xml'
    response.out.write(
        template.render(FEED_TEMPLATE_PATH, {"items":filtered, "feed":feed}))
        

class ViewFeedHtml(webapp.RequestHandler):    
    def get(self):
        key = self.request.get('key')
        item_dict = itemstore.get_dictionary(key)
        item_list = item_dict.values()
        item_list.sort(key=attrgetter('pub_time'), reverse=True)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
            template.render(HTML_TEMPLATE_PATH, {"item_list":item_list, "count":len(item_list), "feed":key}))
        
class EditFeeds(webapp.RequestHandler):
    def get(self):
        Feed.get(self.request.get('key')).delete()
        self.redirect("/feeds")


class ViewTest(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(str(get_classifier(feed).nspam) + "\n")
        self.response.out.write(str(get_classifier(feed).nham))

#        items = get_new_items('http://www.abc.net.au/news/syndicate/breakingrss.xml')
#        self.response.out.write(hash(items[0]))

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
        path = os.path.join(os.path.dirname(__file__), 'feeds.html')
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(template.render(path, {"feeds" : feeds}))

    def post(self):
        link = self.request.get('link')
        feed = Feed(parent = get_feed_key(),
                    link = link)
        get_feed_details(feed)
        feed.put()
        self.redirect("/feeds")

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
        classifier.learn(value.item.getTokens(), isSpam)
    else:
        classifier.unlearn(value.item.getTokens(), value.spam)
    persist_classifier(classifier, feed_key)
    value.probability = classifier.spamprob(value.item.getTokens())
    logging.info("prob="+str(value.probability))
    value.classified = learn
    value.spam = isSpam
    handler.response.out.write(value.probability)


application = webapp.WSGIApplication(
        [('/feeds', ViewFeeds),
         ('/feed/delete', EditFeeds),
         ('/feed/items', ViewFeedHtml),
         ('/feed/xml', ViewXmlFeedAll),
         ('/feed/xml/spam', ViewXmlFeedSpam),
         ('/feed/xml/ham', ViewXmlFeedHam),
         ('/feed/xml/unknown', ViewXmlFeedUnknown),
         ('/feed/classify', ClassifyFeedItems),
         ('/feed/unclassify', UnClassifyItem),
         ('/feed/hits', ViewHits),
         ('/feed/test', ViewTest)],
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

def do_stuff():
    feed = Feed.get('aghiYXllc3Jzc3IXCxIERmVlZCIDYWxsDAsSBEZlZWQYAQw')
    wordInfos = db.GqlQuery("SELECT * FROM WordInfoEntity WHERE ANCESTOR IS :1", feed.key())
    for info in wordInfos:
        logging.info(str(info.word))
    #wordInfos = WordInfoEntity.all()
    #entities = []
    #for info in wordInfos:
    #    entities.append(WordInfoEntity(
    #        parent=feed.key(),
    #        key_name=str(feed.key()) + "_" + info.word, 
    #        word=info.word, 
    #        spamcount=info.spamcount, 
    #        hamcount=info.hamcount))
    #db.put(entities)
    #logging.info("Length: " + str(count) + " of " + str(all)) 
                
def load_hitcounter():
    global hitCounter
    hitCounter = Hit.get_or_insert(HIT_COUNTER_KEY)

def get_feed_details(feed):
    xml = urllib2.urlopen(feed.link).read()
    tree = etree.fromstring(xml)
    channel = tree.find("channel")

    if channel:
        feed.title = channel.find("title").text
        feed.description = channel.find("description").text

    
def get_feed_key():
    return db.Key.from_path("Feed", "all")

if __name__ == '__main__':
    main()
