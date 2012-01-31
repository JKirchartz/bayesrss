from time import mktime, gmtime
import logging
from datetime import datetime

class BrisbaneFormatter(logging.Formatter):
	def _bris_converter(self, seconds):
		gmt = seconds if seconds else gmtime
		bris = seconds + 10 * 60 * 60
		return datetime.fromtimestamp(bris).timetuple()
		
	converter = _bris_converter
	
def set_log_format():
	format = '%(asctime)s  %(levelname)s\t%(filename)s:%(lineno)d %(funcName)s]\t%(message)s'
	logging.getLogger().handlers[0].setFormatter(BrisbaneFormatter(format))
	