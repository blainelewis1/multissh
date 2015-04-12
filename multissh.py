#!/usr/bin/python2 -u
#Please note -u, this opens stdin/stdout in binary mode

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

from launcher import Launcher
from logger import Log
import traceback
import sys


def main():

	launcher = Launcher(sys.argv)
	obj = launcher.launch()
	
	Log.log(sys.argv)

	try:
		obj.poll()
	except BaseException as e:

		#This is here for debugging purposes
		if isinstance(e, Exception):
			Log.log(e)
			my_log = open(Log.log_file, 'a')
			traceback.print_exc(file=my_log)

		obj.cleanup()

		sys.exit(0)
	

#This block will only be run once upon starting
if __name__ == '__main__':
	#this block can be used if we are profiling
	#It would be useful to conglomerate the files
	#cProfile.run("main()", str(time.time()))
	
	main()
