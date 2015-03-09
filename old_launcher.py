#!/usr/bin/python3.3

import shlex
import sys
import worker
import multiplexer
import subprocess
from logger import Log



def main():
	Log.log(sys.argv)
	launcher = Launcher(sys.argv)
	obj = launcher.launch()
	try:
		obj.poll()
	except:
		obj.cleanup()
	
	

#TODO: pass ssh stuff over
class Launcher:

	original_args = None

	REMOTE = "--remote"
	WORKER = "--worker"
	EXECUTABLE_PATH = "/home/blaine1/C496/launcher.py"
	ID_STRING = "-id"
	INIT = "--init"
	USER = "-l"
	REMOTE_IP = "--host"
	RSYNC_ARGS = "--rsync"
	#'-l', 'blaine1',
	#'192.168.163.199'
	#'rsync', '--server', '--sender', '-vlogDtprze.iLsf', '.', '~/test/'


	def __init__(self, args=None):
		self.remote = False
		self.worker = False
		self.init = False


		if not Launcher.original_args:
			Launcher.original_args = args

		if args:
			self.apply_args(args)

	def apply_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		print(args)
		#TODO: super fragile
		if not (self.remote and self.worker):
			#in this case we need to extract rsync args
			Launcher.remote_ip = args[args.index(Launcher.USER) + 2]
			Launcher.rsync_args = args[args.index(Launcher.USER) + 3:]


		#TODO: these are inefficient
		if Launcher.USER in args:
			Launcher.user = args[args.index(Launcher.USER) + 1]

			print(Launcher.user)

		if(Launcher.ID_STRING in args):
			self.ID = int(args[args.index(Launcher.ID_STRING) + 1])

	def launch(self):
		obj = None
		if self.remote:
			if self.worker:
				if self.init:
					self.execute_remote_multiplexer()

				obj = worker.Worker(self.ID, sys.stdin.buffer, sys.stdout.buffer)
			else:
				target_out, target_in  = self.open_remote_target()
				obj = multiplexer.Multiplexer(target_out, target_in, self.ID)				
				
		else:
			if self.worker:
				#do the ssh thinger
				worker_out, worker_in = self.execute_remote_worker()
				obj = worker.Worker(self.ID, worker_out, worker_in)
			else:
				#this is a local multiplexer
				obj = multiplexer.Multiplexer(sys.stdin.buffer, sys.stdout.buffer)
				obj.init_multiplexer()

		return obj

	def open_remote_target(self):
		#TODO: these are mocks atm
		return (open("/home/blaine1/C496/test/test.in", "rb"), open("/home/blaine1/C496/test/test.out", "wb"))

	def execute_remote_worker(self):
		args = ["ssh"] + self.construct_args()
		

		worker = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		
		return (worker.stdout, worker.stdin)

	def construct_args(self):
		#TODO: executable path is a poor way to do that
		args = Launcher.EXECUTABLE_PATH
		if self.init:
			args += " " + Launcher.INIT
		if self.worker: 
			args += " " + Launcher.WORKER + " " + Launcher.ID_STRING + " " + str(self.ID)
		if self.remote:
			args += " " + Launcher.REMOTE
		args += " " + Launcher.USER + " " + str(Launcher.user)
		args += " " + Launcher.REMOTE_IP + " " + str(Launcher.remote_ip)
		args += " " + Launcher.RSYNC_ARGS + " " + str(Launcher.rsync_args)

		return args


	def execute_remote_multiplexer(self):
		args = Launcher.EXECUTABLE_PATH + " " + Launcher.REMOTE + " " + Launcher.ID_STRING + " "  + str(self.ID)

		subprocess.Popen(shlex.split(args))

	def execute(self):

		args = self.construct_args()

		subprocess.Popen(shlex.split(args))
		if self.worker:
			#worker.Workers are executed AND launched from the local side 
			#TODO: from here we actually need to launch two things. Remote and launch
			pass
		else:
			#multiplexer.Multiplexers are only executed from the remote side and 
			pass




if __name__ == '__main__':
	main()