"""
This file is part of multissh.

multissh is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

multissh is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with multissh.  If not, see <http://www.gnu.org/licenses/>.
"""

import shlex
import sys
import subprocess

import worker
import multiplexer
from logger import Log



""" 
	This file acts as the starting point for the application
	It handles command line arguments as well spawning new 
	workers or multiplexers. 

"""

	

class Launcher:
	
	#A path to the application
	EXECUTABLE_PATH = "/home/blaine1/multissh/multissh.py"


	#The different argumets the application can take
	REMOTE_FLAG = "--remote"
	WORKER_FLAG = "--worker"
	ID_FLAG = "-id"
	INIT_FLAG = "--init"
	USER_FLAG = "-l"


	#A launcher can be constructed with either command line args or another launcher
	#If it uses args then it applies them
	#If it uses a launch it takes required fields like
	#Ths remote ip and 
	def __init__(self, args=None,launch=None):
		self.remote = False
		self.worker = False
		self.init = False

		if launch:
			self.user_val = launch.user_val
			self.remote_ip_val = launch.remote_ip_val
			self.target_args = launch.target_args

		elif args:
			self.apply_args(args)


	#Given a list of arguments this parses them and applies them 
	#To this instance of launcher

	def apply_args(self, args):
		self.remote = Launcher.REMOTE_FLAG in args
		self.worker = Launcher.WORKER_FLAG in  args
		self.init = Launcher.INIT_FLAG in args

		
		#TODO: This is a fragile way to take arguments..
		self.remote_ip_val = args[args.index(Launcher.USER_FLAG) + 2]
		self.target_args = args[args.index(Launcher.USER_FLAG) + 3:]		
		self.user_val = args[args.index(Launcher.USER_FLAG) + 1]


		if(Launcher.ID_FLAG in args):
			self.ID = int(args[args.index(Launcher.ID_FLAG) + 1])


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
		
		target = subprocess.Popen(shlex.split(" ".join(self.target_args)), stdout=subprocess.PIPE, stdin=subprocess.PIPE)

		return (target.stdout, target.stdin)


	#From here we can create a new remote worker which is a special case
	#And requires some manual argument construction
	#It returns the stdout and stdin to the new worker
	def execute_remote_worker(self):
		args = "ssh " + self.remote_ip_val 
		args += " " + self.USER_FLAG +" " + self.user_val 
		args += " " + self.construct_args(True)
		
		worker = subprocess.Popen(shlex.split(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		
		return (worker.stdout, worker.stdin)

	#This takes the various arguments and constructs a string
	#That can be used to launch a new instance
	#If remote is True then it simply adds a remote flag in as well
	def construct_args(self, remote=False):
		args = Launcher.EXECUTABLE_PATH
		if self.init:
			args += " " + Launcher.INIT_FLAG
		if self.worker: 
			args += " " + Launcher.WORKER_FLAG + " " + Launcher.ID_FLAG + " " + str(self.ID)
		if self.remote or remote:
			args += " " + Launcher.REMOTE_FLAG
		
		args += " " + Launcher.USER_FLAG + " " + str(self.user_val)
		args += " " + str(self.remote_ip_val)
		args += " " + " ".join(self.target_args)

		return args

	#Remote multiplexers are a special case because they are created
	#After the first worker is sent
	#We manually construct it's args
	def execute_remote_multiplexer(self):
		args = Launcher.EXECUTABLE_PATH + " " 
		args += Launcher.REMOTE_FLAG + " " 
		args += Launcher.ID_FLAG + " "  
		args += str(self.ID) + " "
		
		args +=  Launcher.USER_FLAG + " " + str(self.user_val) + " "
		args +=  str(self.remote_ip_val) + " "
		args += " ".join(self.target_args)

		subprocess.Popen(shlex.split(args))


	#This function takes all the parameters and constructs a new 
	#Set of arguments in order
	#To fork off a new process
	def execute(self):


		args = self.construct_args()

		subprocess.Popen(shlex.split(args))

