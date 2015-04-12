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


#TODO: I removed all non-blocking IO due to failing to deal with partial writes properly.
#In order to deal with failed writes I should 


import sys
import select
import os
import fcntl

from logger import Log
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

		self.opposing_write_queue = []
		self.multiplexer_write_queue = []

		fl = fcntl.fcntl(opposing_out, fcntl.F_GETFL)
		#fcntl.fcntl(opposing_out, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		fl = fcntl.fcntl(opposing_in, fcntl.F_GETFL)
		#fcntl.fcntl(opposing_in, fcntl.F_SETFL, fl | os.O_NONBLOCK)		

		self.poller = select.poll()		

		self.poller.register(self.opposing_out, select.POLLIN)

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
		
		self.multiplexer_in = open(write_path, "wb", 0)
		self.multiplexer_out = open(read_path, "rb", 0)

		fl = fcntl.fcntl(self.multiplexer_in, fcntl.F_GETFL)
		#fcntl.fcntl(self.multiplexer_in, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		fl = fcntl.fcntl(self.multiplexer_out, fcntl.F_GETFL)
		#fcntl.fcntl(self.multiplexer_out, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		self.poller.register(self.multiplexer_out, select.POLLIN)

	#Removes the fifos on delete
	def delete_fifos(self):
		write_path = Worker.get_write_path(self.ID)
		read_path = Worker.get_read_path(self.ID)
		"""
		try:
			os.unlink(write_path)
		except OSError:
			pass
		try:
			os.unlink(read_path)
		except OSError:
			pass
	"""

	def add_to_opposing_write_queue(self, header):

		data = header.to_bytes()

		if header.size != 0:
			data += self.multiplexer_out.read(header.size)

		self.opposing_write_queue.append(data)
		self.write_opposing()
		

	def write_opposing(self):

		while(len(self.opposing_write_queue) > 0):
			try:

				self.opposing_in.write(self.opposing_write_queue[0])
				self.opposing_in.flush()
				del self.opposing_write_queue[0]

			except IOError as e:
				if e.errno == 11:
					self.poller.register(self.opposing_in, select.POLLOUT)
					return
				else:
					raise e


		try:
			if not self.multi_open:
				self.delete_fifos()
				Log.log("Shutting down. multi closed finished in queue")
				sys.exit(0)

			self.poller.unregister(self.opposing_in)
		except KeyError:
			pass

	#Reads from the opposing worker and sends to the multiplexer
	def add_to_multiplexer_write_queue(self, header):

		
		data = header.to_bytes()

		if header.size != 0:
			data += self.opposing_out.read(header.size)


		self.multiplexer_write_queue.append(data)
		self.write_multiplexer()

	def write_multiplexer(self):

		while(len(self.multiplexer_write_queue) > 0):

			temp = str(self.multiplexer_write_queue[0][:20])
						
			try:

				self.multiplexer_in.write(self.multiplexer_write_queue[0])
				self.multiplexer_in.flush()
				del self.multiplexer_write_queue[0]
			except IOError as e:

				if e.errno == 11:

					self.poller.register(self.multiplexer_in, select.POLLOUT)
					return
				else:
					raise

		try:

			if not self.multi_open:
				self.delete_fifos()
				Log.log("Shutting down. multiplexer closed")
				sys.exit(0)

			self.poller.unregister(self.multiplexer_in)
		except KeyError:
			pass
		

	#Cleans up all the resources
	def cleanup(self):
		self.opposing_out.close()
		#self.delete_fifos()

	#This is essentially a main loop
	#It will continually read from the opposing worker
	#and the multiplexer until one of them closes in which 
	#case it will exit
	def poll(self):
		self.multi_open = True
		self.opposing_open = True

		while(True):
			vals = self.poller.poll()

			for fd, event in vals:
				if(fd == self.multiplexer_out.fileno()):
					if(event & select.POLLIN):

						header = self.handle_header(self.multiplexer_out.readline())
						#header = self.handle_header(self.multiplexer_out.read(Header.HEADER_SIZE))
						if header:
							self.add_to_opposing_write_queue(header)

					elif(event & (select.POLLHUP | select.POLLERR)):
						self.multi_open = False
						if len(self.opposing_write_queue) == 0:

							Log.log("Shutting down. Pollhup multi none in queue")

							sys.exit(0)
						self.poller.unregister(self.multiplexer_out)

				elif(fd == self.opposing_out.fileno()):
					if(event & select.POLLIN):

						#header = self.handle_header(self.opposing_out.read(Header.HEADER_SIZE))
						header = self.handle_header(self.opposing_out.readline())
						if header:
							self.add_to_multiplexer_write_queue(header)

					elif(event & (select.POLLHUP | select.POLLERR)):
						self.poller.unregister(self.opposing_out)
						self.opposing_open = False
						if len(self.multiplexer_write_queue) == 0:
							self.delete_fifos()
							Log.log("Shutting down. Pollhup opposing none in queue")
							sys.exit(0)

				elif fd == self.opposing_in.fileno() and event & select.POLLOUT:
					self.write_opposing()

				elif fd == self.multiplexer_in.fileno() and event & select.POLLOUT:
					self.write_multiplexer()
						

	#Verifies and extracts the header as well as handles special
	#Headers
	def handle_header(self, line):
		if not line:
			Log.log("Shutting down. Unknown")
			sys.exit(0)

		header = Header(line)

		if(not header.valid):

			return None

		return header