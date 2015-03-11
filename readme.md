
This program acts like ssh but over multiple streams, multiplexing and demultiplexing the data


Usage

./launcher -l USER IP EXECUTABLE

Eg.

./launcher -l blaine1 192.168.163.201 ls

Would do ls on my home directory

Or:

rsync -avzh --rsh="./launcher.py" ~/test/ blaine1@192.168.163.201:~/test/

Would sync my directories across machines