#!/usr/bin/python3.3

import sys
import worker
import multiplexer


if __name__ == '__main__':
	main()

def main():
	launcher = Launcher(sys.args)
	launcher.launch().poll()

class Launcher:

	original_args = None

	REMOTE = "--remote"
	WORKER = "--worker"
	EXECUTABLE_PATH = "/home/blaine1/C496/launcher.py"

	def __init__(self, args=None):
		self.remote = False
		self.worker = False

		if not Launcher.original_args:
			Launcher.original_args = args

		if args:
			self.apply_args(args)

	def apply_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args

		if(self.worker):
			self.id = int(args[args.index(Launcher.ID) + 1])

	def launch(self):
		obj = None
		if self.remote:
			if self.worker:
				obj = worker.Worker(self.id, sys.stdin, sys.stdout)
			else:
				#multiplexer.Multiplexer
				target_out, target_in  = self.open_remote_target()
				obj = multiplexer.Multiplexer(target_out, target_in)				
				
		else:
			if self.worker:
				#do the ssh thinger
				worker_out, worker_in = execute_remote_worker(self.id)
				obj = worker.Worker(self.id, worker_out, worker_in)
			else:
				#this is a local multiplexer
				obj = multiplexer.Multiplexer(sys.stdin, sys.stdout)
				obj.init_multiplexer()

		return obj

	def open_remote_target(self):
		#TODO: these are mocks atm
		return (open("test.in", "r"), open("test.out", "w"))

	def execute_remote_worker(self):
		args = ""
		worker = subprocess.Popen(shlex.split, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		return 


	def construct_args(self):
		#TODO: executable path is a poor way to do that
		args = Launcher.EXECUTABLE_PATH

	def execute_remote_multiplexer(self):

		pass

	def launch_worker(self):
		pass

	def execute(self):
		args = self.construct_args()
		subprocess.Popen(shlex.split(args), stdout=subprocess.PIPE,stdin=subprocess.PIPE)
		if self.worker:
			#worker.Workers are executed AND launched from the local side 
			#TODO: from here we actually need to launch two things. Remote and launch

			pass
		else:
			#multiplexer.Multiplexers are only executed from the remote side and 
			pass