#!/usr/bin/python3.3

import sys
import multiplexer
import worker
import subprocess

def main():
	launcher = Launcher(sys.argv)
	
	obj = launcher.launch()
	try:
		obj.poll()
	except:
		obj.cleanup()

class Launcher:
	REMOTE = "--remote"
	WORKER = "--worker"
	INIT = "--init"
	USER = "-l"
	REMOTE_HOST = "--remote_host"
	RSYNC_ARGS = "--rsync_args"
	EXECUTABLE_PATH = "/home/blaine1/C496/launcher.py"
	user = ""
	rsync_args = ""
	remote_host = ""

	def __init__(self, args=None):		
		print(args)
		self.remote = False
		self.worker = False
		if args:
			self.parse_args(args)		

	def parse_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		if not (self.remote and self.worker):
			user_index = args.index(Launcher.USER)
			self.user = args[user_index + 1]
			self.remote_host = args[user_index + 2]
			self.rsync_args = args[user_index + 3:]
		else:
			self.user = args[args.index(USER) + 1]
			self.remote_host = args[args.index(REMOTE_HOST) + 1]
			self.rsync_args = args[args.index(RSYNC_ARGS) + 1]

		print(self.user)

	def launch(self):
		obj = None

		if self.init:
			launch_remote_multiplexer()
		
		if self.remote:
			if self.worker:
				obj = create_remote_worker()
			else:
				obj = create_remote_multiplexer()

		elif self.worker:
			launcher = Launcher()
			launcher.remote = True
			launcher.worker = True
			worker_in, worker_out = launcher.execute()
			obj = worker.Worker()
		else:
			#this is a default one....
			obj = multiplexer.Multiplexer(sys.stdin.buffer, sys.stdout.buffer)
			obj.init_multiplexer()

		return obj


	def execute(self):
		if self.worker and self.remote:
			args = ["ssh", self.remote_host] + self.construct_args()
			subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		elif self.worker:
			args = self.construct_args()
			subprocess.Popen(args)

	def construct_args(self):
		args = []
		args.append(Launcher.EXECUTABLE_PATH)
		if self.remote:
			args.append(Launcher.REMOTE)

		if self.worker:
			args.append(Launcher.WORKER)

		args.append(Launcher.USER)
		args.append(self.user)

		args.append(Launcher.RSYNC_ARGS)
		args.append(self.rsync_args)

		return args


if __name__ == '__main__':
	main()