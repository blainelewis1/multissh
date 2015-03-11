

rm *.fifo log.txt
killall launcher.py
scp -r * 192.168.163.208:/home/blaine1/C496/.
