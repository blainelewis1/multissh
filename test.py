



class Test:
	test = "hello"
	def __init__(self):
		pass
	def setTest(self, val):
		Test.test = val
	def printTest(self):
		print(Test.test)

test1 = Test()
test1.printTest()

test2 = Test()

test2.setTest("yo yo")
test2.printTest()
test1.printTest()

test3 = Test()
test3.printTest()