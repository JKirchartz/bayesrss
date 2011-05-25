import logging

from bayesrss.models import *

from spambayes.classifier import Classifier, WordInfo

from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import memcache

SPAM_COUNT_KEY = "singleton"
CLASSIFIER_KEY = "classifier"

def do_persist():
    logging.info("Starting persist")
    #This is both non-atomic and volatile - but the worst case is an unnecessary save
    dirty = memcache.get("classifier_dirty")
    memcache.set("classifier_dirty", False)
    if dirty is None or dirty:
        logging.info("Classifier is dirty")
        classifier = get_classifier()
        counts = SpamCounts(key_name=SPAM_COUNT_KEY, nham=classifier.nham, nspam=classifier.nspam)
        entities = [counts]
        for word, info in classifier.wordinfo.items():
            entities.append(WordInfoEntity(key_name=word, 
                word=word, 
                spamcount=info.spamcount, 
                hamcount=info.hamcount))
        db.put(entities)
        
def get_classifier():
    classifier = memcache.get(CLASSIFIER_KEY)
    
    if classifier is None:
        classifier = Classifier()
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
        memcache.add(CLASSIFIER_KEY, classifier)
    return classifier
    
def persist_classifier():
    memcache.set("classifier_dirty", True)
    deferred.defer(do_persist, _countdown=30)
