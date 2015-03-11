
"""
	Simple class to log to a log file
"""

class Log:

	log_file = "/home/blaine1/C496/log.txt"

	@staticmethod
	def log(msg):
		f = open(Log.log_file,'a')
		f.write(str(msg) + "\n")
		f.flush()
		f.close()