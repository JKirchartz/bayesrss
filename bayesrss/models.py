import re
import logging
from datetime import datetime, timedelta

from BeautifulSoup import BeautifulStoneSoup
from google.appengine.ext import db
from jhash import jhash

from bayesrss.safewords import safewords

splitter = re.compile("[\W]")
    
class Item():
#    title = db.StringProperty(required=True)
#    description = db.StringProperty(required=True, multiline=True)
#    link = db.StringProperty(required=True)
#    pubdate = db.StringProperty()
#    pub_datetime = db.DateTimeProperty()
#    guid = db.StringProperty()
    
    def __init__(self, title, description, link):
        self.title = title
        self.description = description
        self.link = link
        self._tokens = None
        self._hash = None
        
    def tokens(self):
        return self._do_tokens([self.title, self.description])
        
    def _do_tokens(self, strings):
        if self._tokens is None:
            toks = []
            for s in strings:
                toks += splitter.split(s.lower())
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
    def __init__(self, item):
        self.raw_title = item.title
        self.title = item.title + '  [$' + str(item.minimum) + ' - $' + str(item.maximum) + ']'
        self.link = item.link
        self.pub_datetime = item.pub_datetime
        self._tokens = None
        self._hash = None
        
        soup = BeautifulStoneSoup(item.description, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        summary = soup.find('div', attrs={'id':'rssDes'})
        date = soup.find('div', attrs={'id':'rssListedDate'})
        salary = soup.find('div', attrs={'id':'rssSalary'})
        
        self.raw_description = unicode(summary.contents[1])
        self.description = "<html><body>" + unicode(date) + unicode(summary) + unicode(salary) + "</body></html>"

    def tokens(self):
        return self._do_tokens([self.raw_title, self.raw_description])
            
#class SeekItem(Item):
#    def get_tokens(self):
#        if not hasattr(self, 'tokens'):
#            pass
#        return None
            
class Feed(db.Model):
    title = db.StringProperty()
    description = db.StringProperty(multiline=True)
    link = db.StringProperty()
    
    is_aggregated = db.BooleanProperty()
    is_deduplicated = db.BooleanProperty()
    is_filtered = db.BooleanProperty()
    is_seek_mined = db.BooleanProperty()
    
class Hit(db.Model):
    headers = db.StringProperty()
    xmlServiceHitCount = db.IntegerProperty(default=0)
    fetchFeedCount = db.IntegerProperty(default=0)
    since = db.DateTimeProperty(auto_now_add=True)
    
    def countXmlServiceHit(self, headers):
        self.xmlServiceHitCount += 1
        self.headers = str(headers)
        self.put()
        
    def countFetchFeedHit(self):
        self.fetchFeedCount += 1
        self.put()
    
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

