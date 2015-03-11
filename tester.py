#!/usr/bin/python2

"""
	This file is used to run experiments
"""	

import time
import subprocess

RUNS = 10

results = open("rsync_baseline.out", "w")

command = "rsync -a blaine1@cold07:~/test/ ~/test/"
args = shlex.split(command)

cleanup = "rm -rf ~/test"
cleanup_args = shlex.split(cleanup)

for i in range(RUNS):

	start = time.time()

	subprocess.call(args)

	end = time.time()

	results.write(str(end-start) + "\n")

	subprocess.call(cleanup_args)


