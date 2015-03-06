#!/usr/bin/python3.3
import fcntl

import subprocess
import os
import sys
import select
import shlex
import argparse
import random

LOCAL = 0
REMOTE = 1

CONTROL = 0
WORKER = 1

READ_AMOUNT = 4096

NUM_CONNECTIONS = 1
LOG_FILE = "/home/blaine1/C496/log.txt"
RECEIVER_EXECUTABLE = "/home/blaine1/C496/multissh.py"

def main():


    sys.stderr = open(LOG_FILE, "w")


    #logargs = open("/home/blaine1/C496/logargs.txt", "a")
    #logargs.write(" ".join(sys.argv) + "\n")
    #logargs.close()

    location = LOCAL
    processType = CONTROL

    if("--worker" in sys.argv):
        processType = WORKER
        sys.argv.remove("--worker")
    if("--remote" in sys.argv):
        location = REMOTE
        sys.argv.remove("--remote")




    connection = None
    opts = " ".join(sys.argv)

    try:


        #make connection information work.,,ssh 
        if processType == CONTROL:

            connection = ControlConnection(location, opts)
        
        elif processType == WORKER:
            worker_idIndex = sys.argv.index("-worker_id")
            worker_id = int(sys.argv[worker_idIndex + 1])
            sys.argv.pop(worker_idIndex)
            sys.argv.pop(worker_idIndex)  

            connection = WorkerConnection(location, worker_id, opts)

    except BrokenPipeError as e:
        print(e)

    connection.start_poll()


# control connectionsconnects us to the final executable and beggining executable
# it has a list of workers that send and receive data
# They also connect to each other
#TODO: poll on writes too in case of errors

"""
    The control connections have two primary functions

    1:  It maintains a list of all open worker threads and reads from them sequentially IN order   
        and pushes their results to the target
    2:  It uses the same list to send data to the other sworker_ide
    3:  Handles input from the other control for things such as creating new workers or closing old ones

    TODO: should it send the read order?
    We might get a race condition of sorts where we need to resync when a new worker is added

"""


class ControlConnection:

    def __init__(self, mode, opts):

        self.__mode = mode
        self.__workers = []
        self.__poll = select.poll()
        self.__log = open(LOG_FILE, "w")
        self.__worker_readable = dict()
        self.__opts = ""#TODO: replace me opts
        self.__send_index = 0
        self.__read_index = 0


        #register the different inputs to pull
        if self.__mode == REMOTE:

            test_out = "cat /home/blaine1/C496/test_in.txt"
            target_out_sub = subprocess.Popen(shlex.split(test_out), stdout=subprocess.PIPE)            


            test_in = "cat"
            test_in_file = open("/home/blaine1/C496/test_out.txt")
            
            target_in_sub = subprocess.Popen(shlex.split(test_in), stdout=test_in_file, stdin=subprocess.PIPE)            
            

            self.__target_out = target_out_sub.stdout
            self.__target_in = target_in_sub.stdout

            #self.__target_out = self.__target_out.buffer
            #self.__target_in = self.__target_in.buffer

            #the control is through stdin/out because ssh
            self.__control_in = sys.stdout.buffer
            self.__control_out = sys.stdin.buffer

            # self.__control_in.write(bytes("Hello world\n", 'UTF-8'))
            # self.__control_in.flush()

        elif self.__mode == LOCAL:

            args = "ssh 192.168.163.213 \""+ RECEIVER_EXECUTABLE + " --remote \""#--opts " + self.__opts + "\""

            #initiate the control on the other sworker_ide
            
            self.__control = subprocess.Popen(shlex.split(args), stdout=subprocess.PIPE, stdin=subprocess.PIPE)           
            self.__control_in = self.__control.stdin
            self.__control_out = self.__control.stdout

            #establish connections to the original rsync call redirected
            self.__target_in = sys.stdout.buffer
            self.__target_out = sys.stdin.buffer

            #create all the workers
            for i in range(NUM_CONNECTIONS):
                self.create_worker(i)

            self.__num_workers = NUM_CONNECTIONS





        self.__poll.register(self.__control_out, select.POLLIN)
        self.__poll.register(self.__target_out, select.POLLIN)

    def create_worker(self, worker_id):

        #TODO: the command line args really don't work...
        #args = "ssh 192.168.163.177 \""+ RECEIVER_EXECUTABLE + " -worker_id " + str(worker_id) + "-z -mode " + str(REMOTE) + " -connection " + str(CONTROL) + "\""


        args = RECEIVER_EXECUTABLE + " -worker_id " + str(worker_id) + " --worker --local " #--opts \"" + self.__opts + "\""
        worker = subprocess.Popen(shlex.split(args), stdout=subprocess.PIPE, stdin=subprocess.PIPE)

        self.__workers.append((worker_id, worker.stdin, worker.stdout))

        self.__control_in.write(bytes("create " + str(worker_id) + "\n", 'UTF-8'))
        self.__control_in.flush()


        self.__worker_readable[worker_id] = False

        #begin polling for data
        self.__poll.register(worker.stdout, select.POLLIN)

    def register_worker(self, worker_id):

        #TODO: change these file paths
        #We read from where the worker writes
        write_name = "/home/blaine1/C496/worker_write_" + str(worker_id) + ".fifo"
        read_name = "/home/blaine1/C496/worker_read_" + str(worker_id) + ".fifo"

        #TODO: what if we don't have permission to mkfifo
        try:
            os.mkfifo(write_name)
        except:
            pass
        try:
            os.mkfifo(read_name)
        except:
            pass

        self.__log.write("Registering worker\n")
        self.__log.flush()

        worker_out = open(write_name, "rb")
        worker_in = open(read_name, "wb")

        fd = worker_out.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.__worker_readable[worker_id] = False

        self.__workers.append((worker_id, worker_in, worker_out))

        self.__poll.register(worker_out, select.POLLIN)


    def start_poll(self):
        #POLL forever

        while(True):
            polled = self.__poll.poll()
            #nothing to do
            #what to do if it's a sighup?

            for fd, event in polled:
                #inputs are either from rsync or the other master
                #TODO: remove and to give better synchronization scheme
                if fd == self.__control_out.fileno():
                    if event & select.POLLIN:
                        #handle the input from other controller
                        self.parse_control(self.__control_out.readline())

                    elif event & (select.POLLHUP | select.POLLERR | select.POLLNVAL):
                        self.__log.write("received pollhup, exiting\n")
                        self.__log.close()
                        sys.exit(0)
                elif fd == self.__target_out.fileno() and len(self.__workers) == NUM_CONNECTIONS:
                    if event & select.POLLIN:
                        self.send_data()
                    elif event & select.POLLHUP:
                        self.__log.write("received pollhup, exiting\n")
                        self.__log.flush()
                        sys.exit(0)
                    elif event & select.POLLERR:
                        self.__log.write("received pollerr\n")
                        self.__log.flush()
                    elif event & select.POLLNVAL:
                        self.__log.write("received pollnval\n")
                        self.__log.flush()

                elif len(self.__workers) == NUM_CONNECTIONS:
                    #it came from a worker pipe so we need to check the order and see where it fits
                    for worker in self.__workers:
                        if worker[2].fileno() == fd:
                            if(event & select.POLLIN):
                                #set worker to readable
                                self.__worker_readable[worker[0]] = True
                                self.read_data()
                            elif event & (select.POLLERR | select.POLLNVAL):
                                self.__log.write("worker error\n")
                                self.__log.flush()
                            elif event & select.POLLHUP:
                                self.__log.write("worker pollhupped" + str(self.__mode) +"\n")
                                self.__log.flush()
                                #worker[2].close()
                                #del self.__worker[2]
                                self.__num_workers -= 1
                                sys.exit(0)

    def read_data(self):
        #buffer whuke waiting?
        self.__log.write("REAding...\n")
        self.__log.flush()

        #Check if we can read in order, if we can do so
        while(self.__worker_readable[self.__read_index]):

            #TODO: setting to not readable seems slightly wasteful, we can only do one circle for every poll
            
            data = self.__workers[self.__read_index][2].read(READ_AMOUNT)
            
            #read returns empty string upon EOF
            data = self.__workers[self.__read_index][2].read(READ_AMOUNT)

            #TODO: is this the proper thing to do. Will it pollhup?
            if(data == ""):
                self.__target_out.close()
                return

            self.__log.write(str(data))
            self.__log.flush()

            self.__target_in.write(data)
            self.__target_in.flush()

            self.__worker_readable[self.__read_index] = False

            self.__read_index = self.__read_index % len(self.__workers)

    def send_data(self):

        #what are we sending on? 
        #TODO: failed writes

        #read returns empty string upon EOF
        data = self.__target_out.read(READ_AMOUNT)

        #TODO: is this the proper thing to do. Will it pollhup?
        if(data == ""):
            self.__target_out.close()
            return


        #self.__log.write("sending "+str(READ_AMOUNT)+"\n")

        self.__log.write(str(data))
        self.__log.write(str(self.__workers[self.__send_index]))
        self.__log.flush()

        sys.stderr.write("I am a " + str(self.__mode) + "\n")

        self.__workers[self.__send_index][1].write(data)
        self.__workers[self.__send_index][1].flush()
        
        self.__send_index = self.__send_index % len(self.__workers)

    def parse_control(self, command):

        tokens = command.decode("UTF-8").split()

        self.__log.write(str(tokens))
        self.__log.flush()

        if len(tokens) == 1:
            pass
        elif tokens[0] == "create":
            if self.__mode == REMOTE:
                self.register_worker(int(tokens[1]))




class WorkerConnection:
    def __init__(self, location, worker_id, opts):
        self.__location = location
        self.__opts = "" #TODO: add opts
        self.__poll = select.poll()
        self.__worker_id = worker_id
        self.__log = open(LOG_FILE + str(worker_id), "w")



        if self.__location == LOCAL:
            #open worker on other end
            args = "ssh 192.168.163.213 \""+ RECEIVER_EXECUTABLE + " --worker --remote -worker_id " + str(worker_id) + "\"" # + self.__opts + "\""

            self.__connection = subprocess.Popen(shlex.split(args), stdout=subprocess.PIPE, stdin=subprocess.PIPE)

            self.__control_in = sys.stdout.buffer
            self.__control_out = sys.stdin.buffer

            self.__worker_in = self.__connection.stdin
            self.__worker_out = self.__connection.stdout

        elif self.__location == REMOTE:

            self.__worker_in = sys.stdout.buffer
            self.__worker_out = sys.stdin.buffer

            self.open_fifos()

        fd = self.__worker_out.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.__poll.register(self.__worker_out, select.POLLIN)
        self.__poll.register(self.__control_out, select.POLLIN)



    def open_fifos(self):
        self.__write_name = "/home/blaine1/C496/worker_write_" + str(self.__worker_id) + ".fifo"
        self.__read_name = "/home/blaine1/C496/worker_read_" + str(self.__worker_id) + ".fifo"


        #TODO: what if we don't have permission to mkfifo
        try:
            os.mkfifo(self.__write_name)
        except:
            pass
        try:
            os.mkfifo(self.__read_name)
        except:
            pass
        

        write_fifo = open(self.__write_name, "w")
        read_fifo = open(self.__read_name, "r")

        self.__control_in = write_fifo
        self.__control_out = read_fifo


    def start_poll(self):
        while(True):
            polled = self.__poll.poll()
            for fd, event in polled:
                
                #If either of our inputs unexpectedly close we need to exit
                if event & select.POLLIN:
                    if fd == self.__control_out.fileno():

                        data = self.__control_out.read(READ_AMOUNT)

                        self.__log.write(data)
                        self.__log.flush()

                        self.__worker_in.write(data)
                        self.__worker_in.flush()
                    elif fd == self.__worker_out.fileno():
                        
                        data = self.__worker_out.read(READ_AMOUNT)

                        self.__log.write(data)
                        self.__log.flush()

                        self.__control_in.write(data)
                        self.__control_in.flush()

                elif event & select.POLLHUP:

                    self.__log.write("The child just POLLHUPed\n")
                    self.__log.flush()

                    #if self.__location == REMOTE:
                        #os.unlink(self.__write_name)
                        #os.unlink(self.__read_name)

                    #sys.exit(0)


if __name__ == '__main__': 
    main()