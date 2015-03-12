"""
This file is part of multissh.

multissh is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

multissh is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with multissh.  If not, see <http://www.gnu.org/licenses/>.
"""



import sys
import select
import os

from header import Header


"""
	
	Workers receive data from the multiplexer via
	a named pipe and send it to their opposing worker

	They also receive data from their opposing worker
	to send to their multiplexer (via their named pipe)

	Future work:

	Record the time between polls and assume it along 
	with the incoming is throughput in order to create
	a form of weighted round robin

"""


class Worker:
	#Constants as to where to put the named fifo

	#TODO: this would be better if it were in the temp folder
	#as well as given a more unique identifier

	WRITE_PATH = "/tmp/WRITE_"
	READ_PATH = "/tmp/READ_"
	

	#Methods to get these paths for a specific ID
	@staticmethod
	def get_write_path(ID):
		return Worker.WRITE_PATH + str(ID) + ".fifo"

	@staticmethod
	def get_read_path(ID):
		return Worker.READ_PATH + str(ID) + ".fifo"


	#Workers take a writable and readable file in order to connect
	#To the other end of the worker

	def __init__(self, ID, opposing_out, opposing_in):

		self.ID = str(ID)

		self.opposing_out = opposing_out
		self.opposing_in = opposing_in

		self.open_fifos()

	#This method opens the named pipes in order to communicate with the
	#multiplexer
	#NOTE: this method is vulnerable to a deadlock as noted within the 
	#method body

	def open_fifos(self):

		write_path = Worker.get_write_path(self.ID)
		read_path = Worker.get_read_path(self.ID)


		#If the fifo was made already it will error
		#TODO: this might be a performance hit
		try:
			os.mkfifo(write_path)
		except OSError:
			pass

		try:
			os.mkfifo(read_path)
		except OSError:
			pass


		#CAUTION this will deadlock as the read or write
		#side actually blocks until the other end is opened
		#Therefore the multiplexer must open the read side first

		self.multiplexer_in = open(write_path, "wb")
		self.multiplexer_out = open(read_path, "rb")

	#Removes the fifos on delete
	def delete_fifos(self):
		write_path = Worker.get_write_path(self.ID)
		read_path = Worker.get_read_path(self.ID)

		try:
			os.unlink(write_path)
		except OSError:
			pass
		try:
			os.unlink(read_path)
		except OSError:
			pass

	#Reads from the multiplexer and sends to the opposing worker
	def send_to_opposing(self, header):
		self.opposing_in.write(header.to_bytes())

		if header.size != 0:
			data = self.multiplexer_out.read(header.size)
			self.opposing_in.write(data)
			
		self.opposing_in.flush()

	#Reads from the opposing worker and sends to the multiplexer
	def send_to_multiplexer(self, header):

		self.multiplexer_in.write(header.to_bytes())

		if header.size != 0:
			data = self.opposing_out.read(header.size)
			self.multiplexer_in.write(data)

		self.multiplexer_in.flush()

	#Cleans up all the resources
	def cleanup(self):
		self.opposing_out.close()
		self.delete_fifos()


	#This is essentially a main loop
	#It will continually read from the opposing worker
	#and the multiplexer until one of them closes in which 
	#case it will exit
	def poll(self):

		poll = select.poll()
		poll.register(self.multiplexer_out, select.POLLIN)
		poll.register(self.opposing_out, select.POLLIN)


		while(True):

			vals = poll.poll()


			for fd, event in vals:
				if(fd == self.multiplexer_out.fileno()):
					if(event & select.POLLIN):

						header = self.handle_header(self.multiplexer_out.readline())
						if header:
							self.send_to_opposing(header)

					elif(event & (select.POLLHUP | select.POLLERR)):
						self.delete_fifos()
						sys.exit(0)

				elif(fd == self.opposing_out.fileno()):
					if(event & select.POLLIN):

						header = self.handle_header(self.opposing_out.readline())
						if header:
							self.send_to_multiplexer(header)

					elif(event & (select.POLLHUP | select.POLLERR)):
						self.delete_fifos()
						sys.exit(0)
						

	#Verifies and extracts the header as well as handles special
	#Headers
	def handle_header(self, line):
		if not line:
			sys.exit(0)

		header = Header(line)

		if(not header.valid):
			return None

		return header