import sys
import urllib2
import logging
import BeautifulSoup
from xml.etree import cElementTree as etree
from datetime import datetime
from email.utils import parsedate

# import gae_doctests
#sys.path.append('/usr/local/google_appengine')
from google.appengine.api import urlfetch

from models import *

#class Item:
#	 def __init__(self, title, description, link):
#		 self.title = title
#		 self.description = description
#		 self.link = link
		
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
	anchor = create_seek_link(job_soup)
	location = create_seek_location(job_soup)
	body = create_seek_body(job_soup)
	return Item(title=str(anchor.contents[0]), link=anchor['href'], 
				description=location + body,
				guid=anchor['href'])
	
def create_seek_link(job):
	anchor = job.find('dt').find('a')
	anchor['href'] = 'http://www.seek.com.au' + anchor['href']
	return anchor
	
def create_seek_location(job):
	location_parts = job.find('dd', attrs={'class':'loc-salary'})
	location_parts = filter(lambda x: x != '\n', location_parts)
	location = reduce(lambda x, y: str(x) + '<br>' + str(y), location_parts)
	return inline(location.replace('span>', 'small>'), True)
	
def create_seek_body(job):
	body_list = job.find('ul')
	body_para = job.find('p')
	body_para['style'] = 'margin: 0px'
	#'standard' ads have just a <p>, 'StandOuts' have a <ul> and a <p>
	if body_list: 
		body_list['style'] = 'margin: 0px 0px 10px 0px; padding-left: 20px;'
		body = body_list.prettify() + body_para.prettify()
	else: body = body_para.prettify()
	return inline(body, False)
	
def inline(html, left):
	style = '<div style=\"display: inline-block; vertical-align: top;'
	if left: style += 'padding: 10px 10px 10px 0px; width: 125px;'
	else: style += 'padding: 10px 0px 10px 0px; max-width: 515px'
	return style + '\">' + html + '</div>'

def safe_get_element(node, element):
	el = node.find(element)
	if el is not None:
		return el.text
	else:
		return None
		
def fetch_seek_items(link_prefix):
	start = datetime.now()
	items_and_pay = {}
		
	logging.info("fetch_seek_items: Fetching seek link: " + link_prefix)
	step = 5000
	rpcs = [make_rpc(link_prefix, salary, step, items_and_pay) for salary in range(50000, 160000, step)]
	for rpc in rpcs:
		rpc.wait()
	
	logging.info("Found " + str(len(items_and_pay)) + ", took " + str(datetime.now() - start))
	return [SeekItem(it, min(it.salary_range), max(it.salary_range)) for it in items_and_pay.values()]

def _callback(rpc, min, max, items_and_pay):
	#logging.info("fetch_seek_items: Doing callback for " + str(min) + " - " + str(max))
	try:
		content = rpc.get_result().content
	except urlfetch.DownloadError:
		logging.error(sys.exc_info()[0])
		return
	items = parse_seek_html(content)
	logging.info("fetch_seek_items: Found " + str(len(items)) + " items for range $" + str(min) + " to $" + str(max))
	for it in items: 
		it.salary_range = []
		insert_item(items_and_pay, it, min, max)

def insert_item(items_and_pay, item, minimum, maximum):
	"""
	>>> class expando(object): pass
	>>> item = expando()
	>>> item.limits = 0,0
	>>> item.guid = 'guid'
	>>> dict = {}
	>>> insert_item(dict, item, 1, 2)
	>>> dict
	{'guid':expando}
	"""
	value = items_and_pay.get(item.guid, item)
	value.salary_range.extend([minimum, maximum])
	items_and_pay[item.guid] = value
	
def make_rpc(link_prefix, salary, step, items_and_pay):
	rpc = urlfetch.create_rpc(deadline=10)
	rpc.callback = lambda: _callback(rpc, salary, salary + step, items_and_pay)
	urlfetch.make_fetch_call(rpc, link_prefix + "&salary=" + str(salary) + "-" + str(salary + step))
	return rpc

def get_callback(rpc, min, max, items_and_pay):
	#logging.info("fetch_seek_items: Getting callback for " + str(min) + " - " + str(max))
	return lambda: callback(rpc, min, max, items_and_pay)

# if __name__ == "__main__":
# 	import doctest
# 	doctest.testmod()