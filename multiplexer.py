import select
import os
import fcntl
import sys


import worker
import launcher
from header import Header
from logger import Log


"""
	The multiplexer has a list of workers and listens on 
	all of them for new incoming data

	It also listens on target_out for data to send along the workers

	There is a multiplexer on both the host and remote computer

"""

#TODO: we could remove instances of header.valid and just assume validity
#TODO: there's actually a bug with large files where we fail to receive the last packet occassionally



class Multiplexer:
	#These paramaters control the maximum send size as well as
	#The number of streams to use
	INIT_WORKERS = 3
	MAX_READ_SIZE = 4096


	#We initiate a ton of member variables
	#As well as preparing the workers to send along
	def __init__(self, target_out, target_in, ID=None, launch=None):

		self.default_launcher = launch

		self.workers = []

		self.target_in = target_in
		self.target_out = target_out

		#Determines the next worker to send from
		self.send_index = 0

		#Determines order of packets
		self.receive_sequence = 0
		self.send_sequence = 0

		#Dictionary of packets received so we can send them in order
		self.received_packets = dict()


		self.poller = select.poll()


		self.poller.register(target_out, select.POLLIN)
		self.poller.register(target_in, select.POLLOUT)


		#We don't want to block when reading or writing from the target
		fl = fcntl.fcntl(target_out, fcntl.F_GETFL)
		fcntl.fcntl(target_out, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		fl = fcntl.fcntl(target_in, fcntl.F_GETFL)
		fcntl.fcntl(target_in, fcntl.F_SETFL, fl | os.O_NONBLOCK)


		#In this case it's the remote multiplexer and we need to init the workers
		if ID != None:
			for i in range(Multiplexer.INIT_WORKERS):
				self.connect_to_worker(i)

	#From here we init the local multiplexer by creating the workers required
	def init_multiplexer(self):
		#Start one worker which will create a multiplexer on the other side
		self.create_worker(True)

		for i in range(1, Multiplexer.INIT_WORKERS):
			self.create_worker()

	#Creates a worker with the id being it's index in the list of workers
	def create_worker(self, init=False):
		ID = len(self.workers)


		launch = launcher.Launcher(launch=self.default_launcher)
		launch.worker = True
		launch.ID = ID
		launch.init = init
		launch.execute()

		self.connect_to_worker(ID)

	#Connects to a worker by creating the named pipes
	#And adds it to the poller object so we can poll input from it
	def connect_to_worker(self, ID):
		read_path = worker.Worker.get_write_path(ID)
		write_path = worker.Worker.get_read_path(ID)

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
		#So it must be the opposite of the worker
		worker_out = open(read_path, "rb")
		worker_in = open(write_path, "wb")


		self.poller.register(worker_out)
		self.workers.append((worker_in, worker_out))


	#This is essentially a main loop
	#It will continually read from the workers
	#and the target until the target or a worker closes in which
	#case it will exit
	def poll(self):
	
		while(True):

			vals = self.poller.poll()

			for fd, event in vals:
				if fd == self.target_out.fileno():
					if(event & select.POLLIN):

						data = self.target_out.read(Multiplexer.MAX_READ_SIZE)

						if data:
							self.send(data)

					elif event & (select.POLLHUP | select.POLLERR):
						sys.exit(0)

				elif fd == self.target_in.fileno():
					self.attempt_send_to_target()

				else:
					#This is expensive O(n^2), could use a map instead, but with 5 workers
					#It's really not worth it
					for i in range(len(self.workers)):
						if self.workers[i][1].fileno() == fd:

							if event & select.POLLIN:
								header = self.handle_header(self.workers[i][1].readline())
								if header:
									self.receive(i, header)

							else:
								sys.exit(0)	

	#Cleaup all of our resources
	def cleanup(self):
		self.target_in.close()
		self.target_out.close()


	#Chooses a worker to send the given data along with a header and then sends it
	def send(self, data):

		worker = self.workers[self.send_index][0]

		header = Header()
		header.size = len(data)
		header.sequence_number = self.send_sequence

		worker.write(header.to_bytes())
		worker.write(data)
		worker.flush()

		#Increment the sequence number and the send_index to send along another worker
		self.send_index = (1 + self.send_index) % len(self.workers)
		self.send_sequence = self.send_sequence + 1



	#Given text it converts it to a readable header and returns it or None
	#In case the header was invalid
	def handle_header(self, line):
		if not line:
			sys.exit(0)

		header = Header(line)


		if not header.valid:
			return None

		if header.create:
			return None

		return header


	#Given a worker and a header we receive the data from the worker, then try to send 
	#it to the target
	def receive(self, worker_id, header):	
		worker = self.workers[worker_id][1]

		data = worker.read(header.size)

		self.received_packets[header.sequence_number] = data

		self.attempt_send_to_target()


	#This method attempts to send data to the target, if we have in-order data to send 
	#TODO: It's also really confusing and could use refactoring (can't wrap my head around the logic atm)
	#TODO: instrument out of order packets (calls to attempt_send_to_target where if 
	#data isn't passed a single time)
	def attempt_send_to_target(self):
		
		while True:

			#Check if the next sequence number is in the map, if it is send it and try the next one
			#Otherwise we exit

			#If the buffer to target_in is full then we need to wait, in which case we 
			#Add target_in to the polling object until we can send

			data = self.received_packets.get(self.receive_sequence)

			if data:
				try:
					self.target_in.write(data)
				except IOError as e:
					if e.errno == 11:
						self.poller.register(self.target_in, select.POLLOUT)
						return

				self.target_in.flush()
				del self.received_packets[self.receive_sequence]

			else:
				try:
					self.poller.unregister(self.target_in)
				except KeyError: 
					pass
				break

			self.receive_sequence += 1
