#!/usr/bin/python2

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


"""
	This file was used to run experiments

	Examples: baseline rsync vs our version
	baseline ssh with ls vs ours
"""	


import time
import subprocess
import shlex

RUNS = 10


baseline_rsync_command = "rsync -a blaine1@cold06:/dev/shm/1g.blob /dev/shm/1g.blob"
baseline_rsync_filename = "rsync_baseline.out"

rsync_3_workers_command = 'rsync -a --rsh="/home/blaine1/multissh.py" blaine1@cold06:/dev/shm/1g.blob /dev/shm/1g.blob'
rsync_3_workers_filename = "rsync_3_workers.out"


ls_ssh_command = "ssh -l blaine1 cold06 ls"
ls_ssh_filename = "ssh_ls.out"

ls_3_workers_command = "./multissh.py -l blaine1 cold06 ls"
ls_3_workers_filename = "3_workers_ls.out"



def test_command(file_name, command):
	results = open(file_name, "a")
	args = shlex.split(command)

	cleanup = "rm -f /dev/shm/1g.blob"
	cleanup_args = shlex.split(cleanup)

	for i in range(RUNS):

		start = time.time()

		subprocess.call(args)

		end = time.time()

		results.write(str(end-start) + "\n")

		subprocess.call(cleanup_args)

test_command(baseline_rsync_filename, baseline_rsync_command)
test_command(rsync_3_workers_filename, rsync_3_workers_command)

#test_command(ls_ssh_filename, ls_ssh_command)
#test_command(ls_3_workers_filename, ls_3_workers_command)


