import os,sys
import urllib2
import logging
from xml.etree import cElementTree as etree
from datetime import datetime, timedelta
from operator import attrgetter

from bayesrss.models import *
from bayesrss.itemstore import ItemStore
from spambayes.classifier import Classifier, WordInfo

from google.appengine.dist import use_library
use_library('django', '1.2')

# Google App Engine imports.
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

SPAM_THRESHOLD = 0.95
HAM_THRESHOLD = 0.1
HIT_COUNTER_KEY = "key"
SPAM_COUNT_KEY = "singleton"
FEED_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'feed.xml')
HTML_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'items.html')

itemstore = None
hitCounter = None
start_time = datetime.now()
classifier = Classifier()

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
        item_dict = itemstore.getDictionary(key)
        item_list = item_dict.values()
        item_list.sort(key=attrgetter('pub_time'))
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
        self.response.out.write(str(classifier.nspam) + "\n")
        self.response.out.write(str(classifier.nham))

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
        classify(self.request, self.response, False)
        
class ClassifyFeedItems(webapp.RequestHandler):
    def post(self):
        classify(self.request, self.response, True)

def classify(request, response, learn):
    action = request.get("action")
    id = request.get("id")
    feed = request.get("feed")
    isSpam = action=='spam'
    logging.info("Classifying. id="+id+" feed="+feed+" action="+action+" learn="+str(learn))
    try:
        value = itemstore.getItem(id)
    except:
        response.out.write("No item found with ID=" + id + "\n")
        response.out.write("Items:\n" + itemstore.getDictionary(feed))
        return
    if learn:
        classifier.learn(value.item.getTokens(), isSpam)
    else:
        classifier.unlearn(value.item.getTokens(), value.spam)
    persist_classifier()
    value.probability = classifier.spamprob(value.item.getTokens())
    logging.info("prob="+str(value.probability))
    value.classified = learn
    value.spam = isSpam
    response.out.write(value.probability)


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
    load_hitcounter()
    load_classifier()
    
    global itemstore
    itemstore = ItemStore(hitCounter, classifier)
    
    run_wsgi_app(application)
    #    items = {}
    #    while True:
    #        sys.sleep(30)
    #        new_items = get_new_items('http://www.abc.net.au/news/syndicate/breakingrss.xml')


def load_classifier():
    counts = SpamCounts.get_by_key_name(SPAM_COUNT_KEY)
    if counts:
        classifier.nham = counts.nham
        classifier.nspam = counts.nspam
    
    wordInfos = WordInfoEntity.all()
    for info in wordInfos:
        w = WordInfo()
        w.spamcount = info.spamcount
        w.hamcount = info.hamcount
        classifier.wordinfo[info.word] = w

def persist_classifier():
    counts = SpamCounts(key_name=SPAM_COUNT_KEY, nham=classifier.nham, nspam=classifier.nspam)
    entities = [counts]
    for word, info in classifier.wordinfo.items():
        entities.append(WordInfoEntity(key_name=word, 
            word=word, 
            spamcount=info.spamcount, 
            hamcount=info.hamcount))
    db.put(entities)
    
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
