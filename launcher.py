#!/usr/bin/python2 -u
import traceback
import shlex
import sys
import worker
import multiplexer
import subprocess
from logger import Log
import time


""" 
	This file acts as the starting point for the application
	It handles command line arguments as well spawning new 
	workers or multiplexers. 



"""



def main():

	launcher = Launcher(sys.argv)
	obj = launcher.launch()
	try:
		obj.poll()
	except Exception as e:
		#Log.log(e)
		#my_log = open(Log.log_file, 'a')
		#traceback.print_exc(file=my_log)
		obj.cleanup()

	
	

class Launcher:
	
	#A path to the application
	EXECUTABLE_PATH = "/home/blaine1/C496/launcher.py"


	#The different argumets the application can take
	REMOTE = "--remote"
	WORKER = "--worker"
	ID_STRING = "-id"
	INIT = "--init"
	USER = "-l"
	REMOTE_IP = "--host"
	RSYNC_ARGS = "--rsync"


	#A launcher can be constructed with either 
	def __init__(self, args=None,launch=None):
		self.remote = False
		self.worker = False
		self.init = False

		if launch:
			self.user_val = launch.user_val
			self.remote_ip_val = launch.remote_ip_val
			self.rsync_args_val = launch.rsync_args_val

		elif args:
			self.apply_args(args)


	#Given a list of arguments this parses them and applies them 
	#To this instance of launcher

	def apply_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		
		#TODO: This is a fragile way to take arguments..
		self.remote_ip_val = args[args.index(Launcher.USER) + 2]
		self.rsync_args_val = args[args.index(Launcher.USER) + 3:]		
		self.user_val = args[args.index(Launcher.USER) + 1]


		if(Launcher.ID_STRING in args):
			self.ID = int(args[args.index(Launcher.ID_STRING) + 1])


	#This function takes the paramaters parserd from the command line
	#And creates a new object based on them, be it a worker or multiplexer
	#It also attaches the different IO needed

	#It returns the object created
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



	#This creates the target for example rysnc or ls on the remote side
	def open_remote_target(self):
		
		target = subprocess.Popen(shlex.split(" ".join(self.rsync_args_val)), stdout=subprocess.PIPE, stdin=subprocess.PIPE)

		return (target.stdout, target.stdin)


	#From here we can create a new remote worker which is a special case
	#And requires some manual argument construction
	#It returns the stdout and stdin to the new worker
	def execute_remote_worker(self):
		args = "ssh " + self.remote_ip_val 
		args += " " + self.USER +" " + self.user_val 
		args += " " + self.construct_args(True)
		
		worker = subprocess.Popen(shlex.split(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		
		return (worker.stdout, worker.stdin)

	#This takes the various arguments and constructs a string
	#That can be used to launch a new instance
	#If remote is True then it simply adds a remote flag in as well
	def construct_args(self, remote=False):
		args = Launcher.EXECUTABLE_PATH
		if self.init:
			args += " " + Launcher.INIT
		if self.worker: 
			args += " " + Launcher.WORKER + " " + Launcher.ID_STRING + " " + str(self.ID)
		if self.remote or remote:
			args += " " + Launcher.REMOTE
		
		args += " " + Launcher.USER + " " + str(self.user_val)
		args += " " + str(self.remote_ip_val)
		args += " " + " ".join(self.rsync_args_val)

		return args

	#Remote multiplexers are a special case because they are created
	#After the first worker is sent
	#We manually construct it's args
	def execute_remote_multiplexer(self):
		args = Launcher.EXECUTABLE_PATH + " " 
		args = Launcher.REMOTE + " " 
		args += Launcher.ID_STRING + " "  
		args += str(self.ID) + " "
		
		args +=  Launcher.USER + " " + str(self.user_val) + " "
		args +=  str(self.remote_ip_val) + " "
		args += " ".join(self.rsync_args_val)

		subprocess.Popen(shlex.split(args))


	#This function takes all the parameters and constructs a new 
	#Set of arguments in order
	#To fork off a new process
	def execute(self):


		args = self.construct_args()

		subprocess.Popen(shlex.split(args))


#This block will only be run once upon starting
if __name__ == '__main__':
	#this block can be used if we are profiling
	#cProfile.run("main()", str(time.time()))
	
	main()