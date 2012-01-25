import sys
import urllib2
import logging
import BeautifulSoup
from xml.etree import cElementTree as etree
from datetime import datetime
from email.utils import parsedate

#import gae_doctests
from google.appengine.api import urlfetch

from models import *
		
def fetch_items(link):
	#self.hitCounter.countFetchFeedHit()
	xml = urllib2.urlopen(link).read()							 
	return parse_feed_xml(xml)
	
def parse_feed_xml(xml):
	items = []
	tree = etree.fromstring(xml)
	for node in tree.find("channel").findall("item"):
		item = Item(title = node.find("title").text,
					description = node.find("description").text,
					link = node.find("link").text,
					guid=safe_get_element(node, "guid"))
		item.pubdate = safe_get_element(node, "pubDate")
		if item.pubdate is not None:
			tupl = parsedate(item.pubdate)
			item.pub_datetime = datetime(*tupl[:6])
		items.append(item)
	return items

def parse_seek_html(html):
	soup = BeautifulSoup.BeautifulSoup(html)
	resultset = soup.findAll('ol', attrs={'class':'search-results saved-jobs'})
	if not resultset:
		return []
	results = resultset[0].findAll('dl', attrs={'class':'savedjobs-details'})
	return [parse_seek_job(job) for job in results] 
		
def parse_seek_job(job_soup):
	"""
	>>> soup = BeautifulSoup.BeautifulSoup('<dt><a href=\"http://www.seek.com.au\">Text</a></dt>')
	>>> parse_seek_job(soup)
	{'item': <dt><a href="http://www.seek.com.au">Text</a></dt>, 'guid': u'http://www.seek.com.au'}
	"""
	guid = job_soup.find('dt').find('a')['href']
	return {'item':job_soup, 'guid':guid}

def safe_get_element(node, element):
	el = node.find(element)
	if el is not None:
		return el.text
	else:
		return None
		
def fetch_seek_items(link_prefix):
	start = datetime.now()
	items_and_pay = {}
		
	logging.info("Fetching seek link: " + link_prefix)
	step = 5000
	rpcs = [make_rpc(link_prefix, salary, step, items_and_pay) for salary in range(50000, 200000, step)]
	for rpc in rpcs:
		rpc.wait()
	
	logging.info("Found " + str(len(items_and_pay)) + ", took " + str(datetime.now() - start))
	return [SeekItem(it['item'], min(it['salary']), max(it['salary'])) for it in items_and_pay.values()]

def _callback(rpc, min, max, items_and_pay):
	#logging.info("fetch_seek_items: Doing callback for " + str(min) + " - " + str(max))
	try:
		content = rpc.get_result().content
	except urlfetch.DownloadError:
		logging.error(sys.exc_info()[0])
		return
	items = parse_seek_html(content)
	logging.info("Found " + str(len(items)) + " items for range $" + str(min) + " to $" + str(max))
	for it in items: 
		it['salary'] = []
		insert_item(items_and_pay, it, min, max)

def insert_item(items_and_pay, item, minimum, maximum):
	"""
	>>> dict = {}
	>>> insert_item(dict, {'item':  'A', 'guid': 'B', 'salary':[]}, 1, 2)
	>>> dict
	{'B': {'salary': [1, 2], 'item': 'A', 'guid': 'B'}}
	
	>>> dict = {'B':{'item':'A', 'guid':  'B', 'salary': [1, 2]}}
	>>> insert_item(dict, {'item':'A', 'guid':'B', 'salary' : []}, 3, 4)
	>>> dict
	{'B': {'salary': [1, 2, 3, 4], 'item': 'A', 'guid': 'B'}}
	"""
	value = items_and_pay.get(item['guid'], item)
	value['salary'].extend([minimum, maximum])
	items_and_pay[item['guid']] = value
	
def make_rpc(link_prefix, salary, step, items_and_pay):
	rpc = urlfetch.create_rpc(deadline=10)
	rpc.callback = lambda: _callback(rpc, salary, salary + step, items_and_pay)
	urlfetch.make_fetch_call(rpc, link_prefix + "&salary=" + str(salary) + "-" + str(salary + step))
	return rpc

def get_callback(rpc, min, max, items_and_pay):
	#logging.info("fetch_seek_items: Getting callback for " + str(min) + " - " + str(max))
	return lambda: _callback(rpc, min, max, items_and_pay)

# if __name__ == "__main__":
# 	import doctest
# 	doctest.testmod()