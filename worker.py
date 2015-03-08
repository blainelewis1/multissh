#!/usr/bin/python3.3

import sys
import select
import os
from header import Header
import launcher as launch
from logger import Log


#   Record the time between polls and assume it along 
#   with the incoming is throughput in order to create
#   a form of weighted round robin

#TODO: special header to start multi on opposing end
#TODO: special header to tell multi to open another worker
#TODO: create the worker on the other side (keep it outside the worker class)
#TODO: What if we get a deadlock while waiting for the first worker to create a multiplexer?


#ALTERNATE thing

#set an arg saying we be the first worker to be opened


class Worker:
	WRITE_PATH = "/home/blaine1/C496/WRITE_"
	READ_PATH = "/home/blaine1/C496/READ_"
	
	@staticmethod
	def get_write_path(ID):
		return Worker.WRITE_PATH + str(ID) + ".fifo"

	@staticmethod
	def get_read_path(ID):
		return Worker.READ_PATH + str(ID) + ".fifo"

	def __init__(self, ID, opposing_out, opposing_in):

		self.ID = str(ID)

		self.opposing_out = opposing_out
		self.opposing_in = opposing_in

		self.open_fifos()

	def open_fifos(self):

		write_path = Worker.get_write_path(self.ID)
		read_path = Worker.get_read_path(self.ID)

		try:
			os.mkfifo(write_path)
		except FileExistsError:
			pass

		try:
			os.mkfifo(read_path)
		except FileExistsError:
			pass


		#CAUTION this will deadlock as the read or write
		#side actually blocks until the other end is opened
		self.multiplexer_in = open(write_path, "wb")
		self.multiplexer_out = open(read_path, "rb")

	def delete_fifos(self):
		write_path = Worker.get_write_path(self.ID)
		read_path = Worker.get_read_path(self.ID)

		try:
			os.unlink(write_path)
		except FileNotFoundError:
			pass
		try:
			os.unlink(read_path)
		except FileNotFoundError:
			pass

	def send_to_opposing(self, header):
		self.opposing_in.write(header.to_bytes())

		#Log.log("To opposing: ")
		#Log.log(header.to_bytes())

		if header.size != 0:
			data = self.multiplexer_out.read(header.size)
			Log.log("worker to opposing: " + str(data))
			self.opposing_in.write(data)
			
		self.opposing_in.flush()

	def send_to_multiplexer(self, header):

		self.multiplexer_in.write(header.to_bytes())

		#Log.log("To multiplexer: ")
		#Log.log(header.to_bytes())

		if header.size != 0:
			data = self.opposing_out.read(header.size)
			Log.log("worker to multiplexer: " + str(data))
			self.multiplexer_in.write(data)

		self.multiplexer_in.flush()

	def cleanup(self):
		self.opposing_out.close()
		self.delete_fifos()

	def poll(self):

		#TODO: will we ever need to poll on POLLOUT?


		poll = select.poll()
		poll.register(self.multiplexer_out, select.POLLIN)
		poll.register(self.opposing_out, select.POLLIN)

		while(True):

			vals = poll.poll()

			#Log.log(vals)			

			for fd, event in vals:
				if(fd == self.multiplexer_out.fileno()):
					if(event & select.POLLIN):
						header = self.handle_header(self.multiplexer_out.readline())
						if header:
							self.send_to_opposing(header)
					elif(event & (select.POLLHUP | select.POLLERR)):
						#TODO: what happens if an error occurs
						self.delete_fifos()
						sys.exit(0)
						
				elif(fd == self.opposing_out.fileno()):
					if(event & select.POLLIN):
						header = self.handle_header(self.opposing_out.readline())
						if header:
							self.send_to_multiplexer(header)
					elif(event & (select.POLLHUP | select.POLLERR)):
						#TODO: what happens if an error occurs
						self.delete_fifos()
						sys.exit(0)
						
	def handle_header(self, line):
		if not line:
			sys.exit(0)

		header = Header(line)

		if(not header.valid):
			return None

		return header