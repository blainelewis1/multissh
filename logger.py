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
	Simple class to log to a log file
"""

class Log:

	log_file = "/home/blaine1/multissh/log.txt"

	@staticmethod
	def log(msg):
		f = open(Log.log_file,'a')
		f.write(str(msg) + "\n")
		f.flush()
		f.close()