import os, re
import logging

from google.appengine.ext.webapp import template

regex_tags = re.compile('<.+>|[\n]')

def parse_seek_item(job_soup):
	link, title = create_seek_link(job_soup)
	if (title.startswith('<span')): logging.info(job_soup.prettify())
	location, raw_location = create_seek_location(job_soup)
	p, ul, raw_body = create_seek_body(job_soup)
	description = template.render(path('seek_div.xml'), {'location':location, 'p':p, 'ul':ul})
	guid = link.split('/')[-1]
	return title, link, description, raw_location + raw_body, guid 
			
def create_seek_link(job):
	anchor = job.find('dt').find('a')
	return 'http://www.seek.com.au' + anchor['href'], contents(anchor.contents[0])
	
def create_seek_location(job):
	location = job.find('dd', attrs={'class':'loc-salary'})
	return contents(location, '<br>').replace('span>', 'small>'), strip_html_tags(location)

def create_seek_body(job):
	body_list = job.find('ul')
	body_para = job.find('p')
	#'standard' ads have just a <p>, 'StandOuts' have a <ul> and a <p>
	if body_list:
		raw = strip_html_tags(body_list) + ' ' + strip_html_tags(body_para)
		return body_para.renderContents(), body_list.renderContents(), raw
	else: 
		return body_para.renderContents(), None, strip_html_tags(body_para)
		
def contents(soup, sep=''):
	filtered = filter(lambda x: x != '\n', soup)
	return reduce(lambda x, y: str(x) + sep + str(y), filtered)
	
def strip_html_tags(soup):
	return regex_tags.sub(' ', soup.prettify())
	
def path(filename):
	return os.path.join(os.path.dirname(__file__), filename)
	