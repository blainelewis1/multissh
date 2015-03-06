#!/usr/bin/python3.3

from header import Header 
import worker 
import launcher 

import os




def test_header():
	header = Header()
	assert(header.size == 0)
	assert(header.sequence_number == 0)

	header.size = 10
	header.sequence_number = 23

	assert(header.to_string() == "SIZE=10&SEQUENCE=23\n")
#   pipes LOCAL_WORKER ---- pipes ---- pipes ---- REMOTE_WORKER  pipes

def test_worker():
	LEFT_WORKER_WRITE = "test_write.fifo"
	LEFT_WORKER_READ = "test_read.fifo"

	try:
		os.mkfifo(LEFT_WORKER_READ)
	except FileExistsError:
		pass
	try:
		os.mkfifo(LEFT_WORKER_WRITE)
	except FileExistsError:
		pass



	pid = os.fork()
	if pid == 0:
		left_read = open(LEFT_WORKER_READ, "r")
		left_write = open(LEFT_WORKER_WRITE, "w")
		
		left_worker = worker.Worker(1, left_read, left_write)
		
		left_worker.poll()
	else:
		pid = os.fork()
		if pid == 0:
			right_write = open(LEFT_WORKER_READ, "w")
			right_read = open(LEFT_WORKER_WRITE, "r")

			right_worker = worker.Worker(2, right_read, right_write)
			
			right_worker.poll()
		else:
				#these will be fifos..
			left_multi_write = worker.Worker.get_read_path(str(1))
			left_multi_read = worker.Worker.get_write_path(str(1))

			try:
				os.mkfifo(left_multi_write)
			except FileExistsError:
				pass

			try:
				os.mkfifo(left_multi_read)
			except FileExistsError:
				pass

			right_multi_write = worker.Worker.get_read_path(str(2))
			right_multi_read = worker.Worker.get_write_path(str(2))


			try:
				os.mkfifo(right_multi_write)
			except FileExistsError:
				pass

			try:
				os.mkfifo(right_multi_read)
			except FileExistsError:
				pass


			left_multi_read = open(left_multi_read, "r")
			left_multi_write = open(left_multi_write, "w")
			right_multi_read = open(right_multi_read, "r")
			right_multi_write = open(right_multi_write, "w")


			string = "helloworld\n"

			header = Header()
			header.sequence_number = 1
			header.size = len(string)


			left_multi_write.write(header.to_string() + string)
			left_multi_write.flush()

			assert(right_multi_read.readline() == header.to_string())
			assert(right_multi_read.readline() == string)

			right_multi_write.write(header.to_string() + string)
			right_multi_write.flush()

			assert(left_multi_read.readline() == header.to_string())
			assert(left_multi_read.readline() == string)
			
			os.unlink(LEFT_WORKER_WRITE)
			os.unlink(LEFT_WORKER_READ)

def test_launcher():
	
	args = launcher.Launcher.EXECUTABLE_PATH
	launchme = launcher.Launcher(args)
	print(launchme.launch())


test_header()
test_worker()
test_launcher()