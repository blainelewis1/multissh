


class Launcher:
	REMOTE = "--remote"
	WORKER = "--worker"
	INIT = "--init"
	USER = "-l"

	def __init__(self, args):
		Launcher.args = args

		self.parse_args(args)		

	def parse_args(self, args):
		self.remote = Launcher.REMOTE in args
		self.worker = Launcher.WORKER in  args
		self.init = Launcher.INIT in args

		if not (self.remote and self.worker):
			user_index = args.index(USER)
			Launcher.user = args[user_index + 1]
			Launcher.remote_host = args[user_index + 2]
			Launcher.rsync_args = args[user_index + 3:]

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

	def execute(self):
		if self.worker and self.remote:





