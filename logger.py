
class Log:
	@staticmethod
	def log(msg):
		f = open('/home/blaine1/C496/log.txt','a')
		f.write(str(msg) + "\n")
		f.flush()
		f.close()