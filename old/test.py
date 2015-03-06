#!/usr/bin/python

#TODO: do message sizes of 1KB - 16KB inclusive
#TODO: test baseline

import sys
import subprocess

remote_host = sys.argv[1]


def getGlobalArgs(remote_host):
	time = 30
	args = []
	args.append("netperf")
	args.append("-P")
	args.append("0")
	args.append("-I")
	args.append("99,5")
	args.append("-i")
	args.append("12,8")
	args.append("-l")
	args.append(str(time))
	args.append("-H")
	args.append(remote_host)
	args.append("-c")
	args.append("-C")
	return args


def testTimes(filename, remote_host):
	results = open(filename,"w")
	times = [1,2,3,4] + range(5,91,5)
	for time in times:
		args = []
		args.append("netperf")
		args.append("-P")
		args.append("0")
		args.append("-I")
		args.append("99,5")
		args.append("-i")
		args.append("15,9")
		args.append("-l")
		args.append(str(time))
		args.append("-H")
		args.append(remote_host)

		results.write(" ".join(args) + "\n")
		results.flush()
		subprocess.call(args, stdout=results)

	results.close()


def testMessageSizeThroughput(filename, remote_host):
	results = open(filename,"w")

	for i in range(1, 10):
		args = getGlobalArgs(remote_host)
		args.append("--")
		args.append("-m")
		args.append(str(pow(2, i)))

		results.write(" ".join(args) + "\n")
		results.flush()
		subprocess.call(args, stdout=results)

	results.close()

def testMessageSizeLatency(filename, remote_host):
	results = open(filename,"w")

	for i in range(1, 25):
		args = getGlobalArgs(remote_host)
		args.append("-t")
		args.append("TCP_RR")
		args.append("--")
		args.append("-r")
		args.append(str(pow(2, i)))

		results.write(" ".join(args) + "\n")
		results.flush()
		subprocess.call(args, stdout=results)

	results.close()

def testMessageSizeThroughputSendfile(filename, remote_host):
	results = open(filename,"w")

	for i in range(1, 25):
		args = getGlobalArgs(remote_host)
		args.append("-t")
		args.append("TCP_SENDFILE")
		args.append("--")
		args.append("-m")
		args.append(str(pow(2, i)))

		results.write(" ".join(args) + "\n")
		results.flush()
		subprocess.call(args, stdout=results)

	results.close()

def testBaseline(filename, remote_host):
	results = open(filename,"w")
	for test in ["TCP_SENDFILE", "TCP_STREAM", "UDP_STREAM"]:
		args = getGlobalArgs(remote_host)
		args.append("-t")
		args.append(test)


		results.write(" ".join(args) + "\n")
		results.flush()
		subprocess.call(args, stdout=results)
	results.close()

def testCPULimit(filename, remote_host):
	results = open(filename,"w")
	for test in ["TCP_SENDFILE", "TCP_STREAM"]:
		limits = [100] + range(96, 0, -5)
		for limit in limits:
			args = getGlobalArgs(remote_host)
			args.append("-t")
			args.append(test)
			args = ["./cpulimit", "-l", str(limit)] + args


			results.write(" ".join(args) + "\n")
			results.flush()
			subprocess.call(args, stdout=results)
	results.close()



#testMessageSizeThroughput("messageSizeThroughputmore.txt", remote_host)
testMessageSizeLatency("messageSizeLatency2.txt", remote_host)

#testTimes("moretimes.txt", remote_host)

#testCPULimit("cpuLimit.txt", remote_host)
testMessageSizeThroughputSendfile("messageSizeThroughputSendfile.txt", remote_host)


testBaseline("baselines.txt", remote_host)
