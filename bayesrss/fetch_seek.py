
def fetch_seek_items(link_prefix):
	start = datetime.now()
	items = _fetch_seek_html(_create_seek_link(link_prefix, 50000, 160000))
	if not items: return []
	if len(items) <= 3:
		_fetch_items_binary(link_prefix)
	else:
		_fetch_items_linear(link_prefix)
	
def _create_seek_link(link_prefix):
	return link_prefix + "&salary=" + str(salary) + "-" + str(salary + step)
	
def _fetch_seek_html(link):
	html = urllib2.urlopen(link).read()
	return parse_seek_html(html)
	
def _fetch_items_binary(link_prefix, all_items, lower, upper):
	items = _fetch_seek_html(_create_seek_link(link_prefix, lower, _midpoint(lower, upper)))
	
def _create_rpc(link_prefix, lower, upper):
	
	
def _midpoint(lower, upper):
	if (upper - lower) == 5000:
		return None
	else:
		return (lower + upper) / 2
	
def _parse_seek_html(html):
	soup = BeautifulSoup.BeautifulSoup(html)
	resultset = soup.findAll('ol', attrs={'class':'search-results saved-jobs'})
	if not resultset:
		return []
	results = resultset[0].findAll('dl', attrs={'class':'savedjobs-details'})
	return [parse_seek_job(job) for job in results]
	
def _parse_seek_job(job_soup):
	"""
	>>> soup = BeautifulSoup.BeautifulSoup('<dt><a href=\"http://www.seek.com.au\">Text</a></dt>')
	>>> parse_seek_job(soup)
	{'item': <dt><a href="http://www.seek.com.au">Text</a></dt>, 'guid': u'http://www.seek.com.au'}
	"""
	guid = job_soup.find('dt').find('a')['href']
	return {'item':job_soup, 'guid':guid}
	
