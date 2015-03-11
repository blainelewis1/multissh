import worker
import launcher
import subprocess
import select
import os
from header import Header
import fcntl
from logger import Log
import sys

class Multiplexer:
	INIT_WORKERS = 3
	MAX_READ_SIZE = 4096

	def __init__(self, target_out, target_in, ID=None, launch=None):

		self.received_packets = dict()
		self.default_launcher = launch
		self.workers = []
		self.target_in = target_in
		self.target_out = target_out
		self.send_index = 0
		self.receive_sequence = 0
		self.send_sequence = 0
		self.writable = False
		self.poller = select.poll()
		self.poller.register(target_out, select.POLLIN)
		self.poller.register(target_in, select.POLLOUT)

		fl = fcntl.fcntl(target_out, fcntl.F_GETFL)
		fcntl.fcntl(target_out, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		fl = fcntl.fcntl(target_in, fcntl.F_GETFL)
		fcntl.fcntl(target_in, fcntl.F_SETFL, fl | os.O_NONBLOCK)


		if ID != None:
			for i in range(Multiplexer.INIT_WORKERS):
				self.connect_to_worker(i)

	def init_multiplexer(self):
		self.create_worker(True)

		for i in range(1, Multiplexer.INIT_WORKERS):
			self.create_worker()

	def create_worker(self, init=False):
		#spawn process

		ID = len(self.workers)


		launch = launcher.Launcher(launch=self.default_launcher)
		launch.worker = True
		launch.ID = ID
		launch.init = init
		launch.execute()

		self.connect_to_worker(ID)

		# if not init:
		# 	header = Header()
		# 	header.create = ID

		# 	self.workers[0][0].write(header.to_bytes())
		# 	self.workers[0][0].flush()

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
				elif fd == self.target_in.fileno() and self.writable:
					self.attempt_receive()

				else:
					#This is relatively expensive O(n^2), could use a map
					for i in range(len(self.workers)):
						#pull it off!
						if self.workers[i][1].fileno() == fd:

							if event & select.POLLIN:
								header = self.handle_header(self.workers[i][1].readline())
								if header:
									self.receive(i, header)
							else:
								sys.exit(0)

	def cleanup(self):
		self.target_in.close()
		self.target_out.close()

	def send(self, data):
		#TODO: this will block almost guaranteed

		worker = self.workers[self.send_index][0]

		header = Header()
		header.size = len(data)
		header.sequence_number = self.send_sequence

		worker.write(header.to_bytes())
		worker.write(data)
		worker.flush()

		#TODO: weight this
		self.send_index = (1 + self.send_index) % len(self.workers)
		self.send_sequence = self.send_sequence + 1


	def handle_header(self, line):
		if not line:
			sys.exit(0)

		header = Header(line)


		if not header.valid:
			return None

		if header.create:
			#self.connect_to_worker(header.create)
			return None

		return header

	def receive(self, worker_id, header):	
		#TODO: instrument out of order packets
		worker = self.workers[worker_id][1]

		data = worker.read(header.size)

		self.received_packets[header.sequence_number] = data

		self.attempt_receive()


	def attempt_receive(self):
		while True:
			data = self.received_packets.get(self.receive_sequence)

			if data:
				try:
					self.target_in.write(data)
				except IOError as e:
					if e.errno == 11:
						Log.log("would block")
						self.writable = True
						return

				self.target_in.flush()
				del self.received_packets[self.receive_sequence]

			else:
				self.writable = False
				break

			self.receive_sequence += 1
