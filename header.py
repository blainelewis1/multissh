from logger import Log


"""
	Headers allow us to set parameters via an object
	As well as read a header into an object
	It can then be written as either bytes
	Or as a string via the given methods

"""

class Header:
	#Different constants to create the header	
	PAIR_DELIMITER = "&"
	KEY_VALUE_DELIMITER = "="
	SEQUENCE_NUMBER = "SEQ"
	SIZE = "S"
	CREATE = "C"
	TARGET = "T"
	FILL = "F"

	#Only used for constant sized headers
	HEADER_SIZE = 32

	#Passing in a string parses it and fills the fields
	def __init__(self, header_string=None):
		#Default fields
		self.size = 0
		self.sequence_number = -1
		self.valid = True
		self.create = 0
		self.target = False


		#No string provided, default parameters
		if(header_string == None):
			return

		header_string = header.decode("UTF-8").strip()

		tokens = header_string.split(Header.PAIR_DELIMITER)

		#parse the strings
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
			elif(key == Header.CREATE):
				self.create = int(value)
			elif key == Header.FILL:
				pass
			else:
				self.valid = False
				return

	#Takes a key value pair and joins them using the delimiter
	def join_pair(self, key, value):
		return key + Header.KEY_VALUE_DELIMITER + value

	#Converts the header to a string
	def to_string(self):		
		pairs = []
		if(self.size != 0):
			pairs.append(self.join_pair(Header.SIZE, str(self.size)))
		if(self.sequence_number != -1):
			pairs.append(self.join_pair(Header.SEQUENCE_NUMBER, str(self.sequence_number)))
		if(self.create):
			pairs.append(self.join_pair(Header.CREATE, str(self.create)))
		if(self.target):
			pairs.append(self.join_pair(Header.TARGET, str(self.TARGET)))


		string = Header.PAIR_DELIMITER.join(pairs)

		#These lines can be unocmmented in order to "fill" the header
		#And thereby create constant sized headers

		#string += Header.PAIR_DELIMITER
		#string += self.join_pair(Header.FILL, "X"*(Header.HEADER_SIZE - len(string)-3))
		
		string += "\n"

		return string

	#Converst the header to bytes
	def to_bytes(self):
		return bytes(self.to_string())
