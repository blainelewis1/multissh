#TODO: we could actually make headers more useful and we could 

#Invalid headers set valid to false and return

#TODO: nonblocking io on ALL filehandles

class Header:
	PAIR_DELIMITER = "&"
	KEY_VALUE_DELIMITER = "="
	SEQUENCE_NUMBER = "SEQUENCE"
	SIZE = "SIZE"
	INIT = "INIT"
	CREATE = "CREATE"
	TARGET = "TARGET"

	def __init__(self, header=None):
		self.size = 0
		self.sequence_number = 0
		self.valid = True
		self.create = 0
		self.init = False
		self.target = False

		if(header == None):
			return

		header = header.decode("UTF-8").strip()

		tokens = header.split(Header.PAIR_DELIMITER)

		for token in tokens:
			key_value_tokens = token.split(Header.KEY_VALUE_DELIMITER)
			if(len(key_value_tokens) != 2):
				self.valid = False
				return

			key,value = key_value_tokens
			if(key == Header.SEQUENCE_NUMBER):
				self.sequence_number = int(value)
			elif(key == Header.SIZE):
				self.size = int(value)
			elif(key == Header.INIT):
				self.init = value == "True"
			elif(key == Header.CREATE):
				self.create = int(value)
			elif(key == Header.TARGET):
				self.target = (value == "True")
			else:
				self.valid = False
				return

	def join_pair(self, x, y):
		return x + Header.KEY_VALUE_DELIMITER + y

	def to_string(self):
		pairs = []
		if(self.size != 0):
			pairs.append(self.join_pair(Header.SIZE, str(self.size)))
		if(self.sequence_number != 0):
			pairs.append(self.join_pair(Header.SEQUENCE_NUMBER, str(self.sequence_number)))
		if(self.init):
			pairs.append(self.join_pair(Header.INIT, str(self.init)))
		if(self.create):
			pairs.append(self.join_pair(Header.CREATE, str(self.create)))
		if(self.target):
			pairs.append(self.join_pair(Header.TARGET, str(self.TARGET)))

		return  Header.PAIR_DELIMITER.join(pairs) + "\n"


	def to_bytes(self):
		return bytes(self.to_string(), 'UTF-8')
