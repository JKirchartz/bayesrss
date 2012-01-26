import logging

from bayesrss.models import *

from spambayes.classifier import Classifier, WordInfo

from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import memcache

SPAM_COUNT_KEY = "singleton"
CLASSIFIER_KEY = "classifier"

def do_persist(feed_key):
    logging.info("Starting persist of classifier")
    dirty_key = "classifier_dirty_" + feed_key
    logging.info(dirty_key)
    dirty = memcache.get(dirty_key)
    if dirty is None or dirty:
        logging.info("Classifier is dirty. feed %s", feed_key)
        memcache.set(dirty_key, False)
        classifier = get_classifier(feed_key)
        feed = Feed.get(feed_key)
        counts = SpamCounts(
            parent=feed, 
            key_name=SPAM_COUNT_KEY, 
            nham=classifier.nham, 
            nspam=classifier.nspam)
        entities = [counts]
        for word in classifier.dirty:
            #Unlearning can leave stale entries in the dirty set
            if classifier.wordinfo.has_key(word):
                info = classifier.wordinfo[word]
                entities.append(WordInfoEntity(
                    parent=feed,
                    key_name=feed_key + "_" + word, 
                    word=word, 
                    spamcount=info.spamcount, 
                    hamcount=info.hamcount))
        classifier.clean()
        db.put(entities)
        _do_memchache_set(classifier)
        logging.info("Persisted %s of %s entities", len(entities), len(classifier.wordinfo.keys()) + 1)
        
def get_classifier(feed_key):
    logging.info("Getting classifier for feed " + feed_key)
    classifier_key = "classifier_" + feed_key
    classifier = memcache.get(classifier_key)
    
    if classifier is None:
        classifier = Classifier(classifier_key)
        logging.info("Reloading classifier " + str(classifier.key))
        counts = SpamCounts.get_by_key_name(SPAM_COUNT_KEY) 
        if counts:
            classifier.nham = counts.nham
            classifier.nspam = counts.nspam
        
        wordInfos = db.GqlQuery("SELECT * FROM WordInfoEntity WHERE ANCESTOR IS :1", feed_key)
        count = 0
        max_sc = max_hc = 0
        for info in wordInfos:
            w = WordInfo()
            max_sc = max(max_sc, info.spamcount)
            max_hc = max(max_hc, info.hamcount)
            w.spamcount = info.spamcount
            w.hamcount = info.hamcount
            classifier.wordinfo[info.word] = w
            count += 1
        if max_sc > classifier.nspam:
            classifier.nspam = max_sc
        if max_hc > classifier.nham:
            classifier.nham = max_hc
        logging.info("Max spamcount = %s, with nspam = %s", max_sc, classifier.nspam)
        logging.info("Max hamcount = %s with nham = %s", max_hc, classifier.nham)
        logging.info("Loaded %s entities", count)
        memcache.add(classifier.key, classifier)
    return classifier
    
def _do_memchache_set(classifier):
    memcache.set(classifier.key, classifier)
    
def persist_classifier(classifier, feed_key):
    memcache.set("classifier_dirty_" + feed_key, True)
    _do_memchache_set(classifier)
    deferred.defer(do_persist, feed_key, _countdown=180)
