import worker
import launcher as launch
import subprocess
import select
import os
from header import Header
import fcntl
from logger import Log
import sys

class Multiplexer:
	INIT_WORKERS = 5
	MAX_READ_SIZE = 2048

	def __init__(self, target_out, target_in, ID=None):

		self.received_packets = dict()

		self.workers = []
		self.target_in = target_in
		self.target_out = target_out
		self.send_index = 0
		self.receive_sequence = 0
		self.send_sequence = 0

		self.poller = select.poll()
		self.poller.register(target_out, select.POLLIN)

		fl = fcntl.fcntl(target_out, fcntl.F_GETFL)
		fcntl.fcntl(target_out, fcntl.F_SETFL, fl | os.O_NONBLOCK)

		#TODO: I could initiate worker[0] separately

		if ID != None:
			self.connect_to_worker(ID)

	def init_multiplexer(self):
		self.create_worker(True)

		for i in range(1, Multiplexer.INIT_WORKERS):
			self.create_worker()

	def create_worker(self, init=False):
		#spawn process

		ID = len(self.workers)

		launcher = launch.Launcher()
		launcher.worker = True
		launcher.ID = ID
		launcher.init = init
		launcher.execute()

		self.connect_to_worker(ID)

		if not init:
			header = Header()
			header.create = ID

			self.workers[0][0].write(header.to_bytes())
			self.workers[0][0].flush()

	def connect_to_worker(self, ID):
		read_path = worker.Worker.get_write_path(ID)
		write_path = worker.Worker.get_read_path(ID)

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
		#So it must be the opposite of the worker
		worker_out = open(read_path, "rb")
		worker_in = open(write_path, "wb")

		self.poller.register(worker_out)
		self.workers.append((worker_in, worker_out))

		Log.log(self.workers)

	def poll(self):
	
		while(True):
			vals = self.poller.poll()

			for fd, event in vals:
				if fd == self.target_out.fileno() and len(self.workers) > 0:
					if(event & select.POLLIN):
						self.send()	
					elif event & (select.POLLHUP | select.POLLERR):
						#TODO: what happens if an error occurs
						sys.exit(0)
				else:
					#This is relatively expensive O(n^2), could use a map
					for i in range(len(self.workers)):
						#pull it off!
						if self.workers[i][1].fileno() == fd:
							header = self.handle_header(self.workers[i][1].readline())
							if header:
								self.receive(i, header)

	def send(self):
		#TODO: this will block almost guaranteed
		data = self.target_out.read(Multiplexer.MAX_READ_SIZE)

		worker = self.workers[self.send_index][0]

		header = Header()
		header.size = len(data)
		header.sequence = self.send_sequence

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

		Log.log(header.to_bytes())

		if not header.valid:
			return None

		if header.create:
			self.connect_to_worker(header.create)
			return None

		return header

	def receive(self, worker_id, header):	
		#TODO: instrument out of order packets


		worker = self.workers[worker_id][1]

		data = worker.read(header.size)

		Log.log(data)

		self.received_packets[header.sequence_number] = data

		self.attempt_receive()


	def attempt_receive(self):
		while True:
			Log.log("attempting")
			data = self.received_packets.get(self.receive_sequence)

			if data:
				self.target_in.write(data)
				self.target_in.flush()
				del self.received_packets[self.receive_sequence]
			else:
				break

			self.receive_sequence += 1

