from google.appengine.ext import db

class Item(db.Model):
    title = db.StringProperty(required=True)
    description = db.StringProperty(required=True, multiline=True)
    link = db.StringProperty(required=True)
    pubdate = db.StringProperty()
    guid = db.StringProperty()

    def getTokens(self):
        return self.title.split() + self.description.split()

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
