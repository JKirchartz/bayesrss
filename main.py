import os,sys
import urllib2
from xml.etree import cElementTree as etree
from datetime import datetime, timedelta

from bayesrss.models import *
from spambayes.classifier import Classifier, WordInfo

from google.appengine.dist import use_library
use_library('django', '1.2')

# Google App Engine imports.
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

HIT_COUNTER_KEY = "key"
SPAM_COUNT_KEY = "singleton"
FEED_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'feed.xml')
HTML_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'items.html')

feedItems = {}
itemDict = {}
hitCounter = None
start_time = datetime.now()
fetchTime = None
classifier = Classifier()

class ViewFeedXml(webapp.RequestHandler):
    def get(self):
        hitCounter.countXmlServiceHit(self.request.headers)
        key = self.request.get('key')
        feed = Feed.get(key)
        items = get_cached_items(key)

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(
            template.render(FEED_TEMPLATE_PATH, {"items" : items, "feed" : feed}))

class ViewFeedHtml(webapp.RequestHandler):
    def get(self):
        key = self.request.get('key')
        items = get_cached_items(key)
        
        global itemDict
        itemDict = {}
        for it in items:
            itemDict[str(hash(it))] = [it, classifier.spamprob(it.getTokens())]
            
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(
            template.render(HTML_TEMPLATE_PATH, {"itemDict":itemDict, "count":len(items), "feed":key}))


class EditFeeds(webapp.RequestHandler):
    def get(self):
        key = self.request.get('key')
        feed = Feed.get(key)
        feed.delete()
        self.redirect("/feeds")


class ViewTest(webapp.RequestHandler):
    def get(self):
        import django
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(str(classifier.nspam) + "\n")
        self.response.out.write(str(classifier.nham))

#        items = get_new_items('http://www.abc.net.au/news/syndicate/breakingrss.xml')
#        self.response.out.write(hash(items[0]))

class ViewHits(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        if hitCounter:
            self.response.out.write("Count=" + str(hitCounter.count) + "\n")
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


class ClassifyFeedItems(webapp.RequestHandler):
    def post(self):
        action = self.request.get("action")
        id = self.request.get("id")
        feed = self.request.get("feed")
        
        try:
            item = itemDict[id][0]
        except:
            self.response.out.write("Error\n")
            self.response.out.write(str(itemDict))
            return
            
        tokens = item.getTokens()
        
        classifier.learn(tokens, action=='bad')
        persist_classifier()
        
        self.redirect("/feed/items?key=" + feed)

application = webapp.WSGIApplication(
        [('/feeds', ViewFeeds),
         ('/feed/delete', EditFeeds),
         ('/feed/items', ViewFeedHtml),
         ('/feed/xml', ViewFeedXml),
         ('/feed/classify', ClassifyFeedItems),
         ('/hits', ViewHits),
         ('/test', ViewTest)],
        debug=True)

def main():        
    load_hitcounter()
    load_classifier()
    
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


def get_new_items(key, url):
    hitCounter.countFetchFeedHit()
    xml = urllib2.urlopen(url).read()
    items = []
    tree = etree.fromstring(xml)
    for node in tree.find("channel").findall("item"):
        item = Item(parent = get_feed_key(),
                    title = node.find("title").text,
                    description = node.find("description").text,
                    link = node.find("link").text)
        item.pubdate = node.find("pubDate").text
        items.append(item)
    if key:
        feedItems[key] = items
    return items

def get_cached_items(key):
    global fetchTime
    if feedItems.has_key(key) and fetched_recently():
        return feedItems[key]
    feed = Feed.get(key)
    fetchTime = datetime.now()
    return get_new_items(key, feed.link)

def fetched_recently():
    return (fetchTime is None 
        or fetchTime + timedelta(hours=2) < datetime.now())
    
def get_feed_key():
    return db.Key.from_path("Feed", "all")

if __name__ == '__main__':
  main()