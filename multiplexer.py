import worker
import launcher as launch
import subprocess
import select
import os
from header import Header
import fcntl

class Multiplexer:
	INIT_WORKERS = 5
	MAX_READ_SIZE = 2048

	def __init__(self, target_out, target_in, ID=None):
		print(target_in)

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

		if ID:
			print("YOYO")
			self.connect_to_worker(ID)

	def init_multiplexer(self):
		for i in range(Multiplexer.INIT_WORKERS):
			self.create_worker()

		self.send_init_request()


	def send_init_request(self):
		header = Header()
		header.init = True

		self.workers[0][0].write(header.to_bytes())
		self.workers[0][0].flush()

	def create_worker(self):
		#spawn process

		launcher = launch.Launcher()
		launcher.worker = True
		launcher.ID = len(self.workers)
		launcher.execute()

		self.connect_to_worker(len(self.workers))

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

		print(ID)

		self.poller.register(worker_out)
		self.workers.append((worker_in, worker_out))


		print(len(self.workers))

	def poll(self):
		print("polling")
		
		print(self.target_out.fileno())

		while(True):
			vals = self.poller.poll()

			for fd, event in vals:
				#print(len(self.workers))
				if fd == self.target_out.fileno() and len(self.workers) > 0:
					if(event & select.POLLIN):
						print("sending")
						self.send()	
					elif event & (select.POLLHUP | select.POLLERR):
						#TODO: what happens if an error occurs
						sys.exit(0)
				else:
					#This is relatively expensive O(n^2), could use a map
					for i in range(len(self.workers)):
						#pull it off!
						print("receiving")
						if self.workers[i][1].fileno() == fd:
							self.receive(i)

	def send(self):
		#TODO: this will block almost guaranteed
		print("trying to send")
		data = self.target_out.read(Multiplexer.MAX_READ_SIZE)

		print(data)

		worker = self.workers[self.send_index][0]

		header = Header()
		header.size = len(data)
		header.sequence = self.send_sequence

		worker.write(header.to_bytes())
		worker.write(data)
		worker.flush()

		#TODO: weight this
		self.send_index = 1 + self.send_index % len(self.workers)
		self.send_sequence = self.send_sequence + 1


	def receive(self, worker_id):
		worker = worker_id
