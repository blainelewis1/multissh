#!/usr/bin/python2 -u

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

	def __init__(self, args=None,launch=None):
		self.remote = False
		self.worker = False
		self.init = False

		if launch:
			self.user_val = launch.user_val
			self.remote_ip_val = launch.remote_ip_val
			self.rsync_args_val = launch.rsync_args_val

		if not Launcher.original_args:
			Launcher.original_args = args

		if args:
			self.apply_args(args)


		print("INIT:" + self.user_val)

	def apply_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		print(args)
		#TODO: super fragile
		#if not (self.remote and self.worker):
		#in this case we need to extract rsync args
		
		self.remote_ip_val = args[args.index(Launcher.USER) + 2]
		self.rsync_args_val = args[args.index(Launcher.USER) + 3:]		
		self.user_val = args[args.index(Launcher.USER) + 1]

		if(Launcher.ID_STRING in args):
			self.ID = int(args[args.index(Launcher.ID_STRING) + 1])



		#Launcher.user_val = self.user_val
		#Launcher.rsync_args_val = self.rsync_args_val
		#Launcher.remote_ip_val = self.remote_ip_val

		#print(Launcher.user_val)

	def launch(self):
		obj = None
		if self.remote:
			if self.worker:
				if self.init:
					self.execute_remote_multiplexer()

				obj = worker.Worker(self.ID, sys.stdin, sys.stdout)
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
				obj = multiplexer.Multiplexer(sys.stdin, sys.stdout, launch=self)
				obj.init_multiplexer()

		return obj

	def open_remote_target(self):
		#TODO: these are mocks atm
		return (open("/home/blaine1/C496/test/test.in", "rb"), open("/home/blaine1/C496/test/test.out", "wb"))

	def execute_remote_worker(self):
		args = "ssh " + self.remote_ip_val + " " + self.USER +" " + self.user_val +" "+ self.construct_args()
		
		print("fork")
		worker = subprocess.Popen(shlex.split(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		
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
		
		args += " " + Launcher.USER + " " + str(self.user_val)
		args += " " + str(self.remote_ip_val)
		args += " " + str(self.rsync_args_val)

		return args


	def execute_remote_multiplexer(self):
		args = Launcher.EXECUTABLE_PATH + " " + Launcher.REMOTE + " " + Launcher.ID_STRING + " "  + str(self.ID)

		print("fork")

		subprocess.Popen(shlex.split(args))

	def execute(self):

		args = self.construct_args()
		print("fork")


		subprocess.Popen(shlex.split(args))


if __name__ == '__main__':
	main()