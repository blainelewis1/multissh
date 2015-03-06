#!/usr/bin/python3

import time
import subprocess
import sys
import select
import fcntl
import os

write_name = "/home/blaine1/C496/worker_write_.fifo"
read_name = "/home/blaine1/C496/worker_read_.fifo"

#TODO: what if we don't have permission to mkfifo
try:
    os.mkfifo(write_name)
except:
    pass

print("open")

child_id = os.fork()
if child_id == 0:
	#this is the child
	worker_in = open(write_name, "wb")
	
	worker_in.write(bytes("hello world \n", "UTF-8"))
	worker_in.write(bytes("how you doing \n", "UTF-8"))
	worker_in.write(bytes("how you doing \n", "UTF-8"))
	worker_in.write(bytes("how you doing \n", "UTF-8"))
	worker_in.write(bytes("how you doing \n", "UTF-8"))
	worker_in.flush()

	time.sleep(1)

	worker_in.write(bytes("the rest \n", "UTF-8"))
	worker_in.close()
	sys.exit(0)


else:
	worker_out = open(write_name, "rb")


	print('reading')


	fd = worker_out.fileno()
	fl = fcntl.fcntl(fd, fcntl.F_GETFL)
	fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

	poller = select.poll()

	poller.register(fd)

	
	while(True):

		vals = poller.poll()
		print(vals)
		for fd, event in vals:

			print(event)

			if(event & select.POLLIN):
				print(worker_out.read(2048))
			elif(event & select.POLLHUP):
				print("broken")
				sys.exit(0)

