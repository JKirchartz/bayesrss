import re
import logging
from datetime import datetime, timedelta

from google.appengine.ext import db
from jhash import jhash

from bayesrss.safewords import safewords

splitter = re.compile("[\W]")
    
class Item(db.Model):
    title = db.StringProperty(required=True)
    description = db.StringProperty(required=True, multiline=True)
    link = db.StringProperty(required=True)
    pubdate = db.StringProperty()
    pub_datetime = db.DateTimeProperty()
    guid = db.StringProperty()
 
    def getTokens(self):
        if not hasattr(self, 'tokens'):
            split = filter(None, splitter.split(self.title) + splitter.split(self.description))
            self.tokens = list(set(split) - safewords)
            logging.info("safewords reduced from " + str(len(split)) + " to " + str(len(self.tokens)))
        return self.tokens
        
    def hash(self):
        return str(jhash(self.title + self.description))

class Feed(db.Model):
    title = db.StringProperty()
    description = db.StringProperty(multiline=True)
    link = db.StringProperty()

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

