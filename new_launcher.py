#!/usr/bin/python3.3

import sys
import multiplexer
import worker


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

	def __init__(self, args):
		Launcher.args = args

		self.parse_args(args)		

	def parse_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		if not (self.remote and self.worker):
			user_index = args.index(Launcher.USER)
			Launcher.user = args[user_index + 1]
			Launcher.remote_host = args[user_index + 2]
			Launcher.rsync_args = args[user_index + 3:]
		else:
			Launcher.user = args[args.index(USER) + 1]
			Launcher.remote_host = args[args.index(REMOTE_HOST) + 1]
			Launcher.rsync_args = args[args.index(RSYNC_ARGS) + 1]

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
			obj = create_local_worker()
		else:
			#this is a default one....
			obj = multiplexer.Multiplexer(sys.stdin.buffer, sys.stdout.buffer)
			obj.init_multiplexer()

		return obj

	def execute_worker(self):
		if self.worker and self.remote:
			args = ["ssh", Launcher.remote_host] + self.construct_args()
			subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)



	def construct_args(self):
		args = []
		if self.remote:
			args.append(Launcher.REMOTE)

		if self.worker:
			args.append(Launcher.WORKER)

		args.append(Launcher.USER)
		args.append(Launcher.user)

		args.append(Launcher.RSYNC_ARGS)
		args.append(Launcher.rsync_args)

		return args


if __name__ == '__main__':
	main()