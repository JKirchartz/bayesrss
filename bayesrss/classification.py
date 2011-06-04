import logging

from bayesrss.models import *

from spambayes.classifier import Classifier, WordInfo

from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import memcache

SPAM_COUNT_KEY = "singleton"
CLASSIFIER_KEY = "classifier"

def do_persist(feed_key):
    logging.info("Starting persist")
    dirty_key = "classifier_dity_" + feed_key
    dirty = memcache.get(dirty_key)
    if dirty is None or dirty:
        logging.info("Classifier is dirty")
        memcache.set(dirty_key, False)
        classifier = get_classifier(feed_key)
        feed_key_obj = db.Key.from_path('Feed', feed_key)
        counts = SpamCounts(
            parent=feed_key_obj, 
            key_name=SPAM_COUNT_KEY, 
            nham=classifier.nham, 
            nspam=classifier.nspam)
        entities = [counts]
        for word in classifier.dirty:
            info = classifier.wordinfo[word]
            entities.append(WordInfoEntity(
                parent=feed_key_obj,
                key_name=feed_key + "_" + word, 
                word=word, 
                spamcount=info.spamcount, 
                hamcount=info.hamcount))
        classifier.clean()
        db.put(entities)
        _do_memchache_set(classifier)
        logging.info("Persisted " + str(len(entities)) + " of " + str(len(classifier.wordinfo.keys())) + " entities")
        
def get_classifier(feed_key):
    logging.info("Getting classifier for feed: " + feed_key)
    classifier_key = "classifier_" + feed_key
    classifier = memcache.get(classifier_key)
    
    if classifier is None:
        classifier = Classifier(classifier_key)
        logging.info("New classifier: " + str(classifier.key))
        counts = SpamCounts.get_by_key_name(SPAM_COUNT_KEY)
        if counts:
            classifier.nham = counts.nham
            classifier.nspam = counts.nspam
        
        wordInfos = db.GqlQuery("SELECT * FROM WordInfoEntity WHERE ANCESTOR IS :1", feed_key)
        for info in wordInfos:
            w = WordInfo()
            w.spamcount = info.spamcount
            w.hamcount = info.hamcount
            classifier.wordinfo[info.word] = w
        memcache.add(classifier.key, classifier)
    return classifier
    
def _do_memchache_set(classifier):
    memcache.set(classifier.key, classifier)
    
def persist_classifier(classifier, feed_key):
    memcache.set("classifier_dirty_" + feed_key, True)
    _do_memchache_set(classifier)
    deferred.defer(do_persist, feed_key, _countdown=180)
