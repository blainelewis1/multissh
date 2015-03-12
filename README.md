
This program acts like ssh but over multiple streams, multiplexing and demultiplexing the data


Usage

./multissh.py -l USER IP EXECUTABLE

Eg.

./multissh.py -l blaine1 192.168.163.201 ls

Would do ls on my home directory

Or:

rsync -avzh --rsh="./multissh.py" ~/test/ blaine1@192.168.163.201:~/test/

Would sync my directories across machines

In order to make it work on your computer(s) you'll need to change the EXECUTABLE_PATH found in launcher.py

See LICENSE for copyright information
