class SourceError(Exception):
	'''Errors regarding source engine servers'''
	def __init__(self, server, message):
		self.message = "Source Server Error @ " + server._ip + ":" + str(server._port) + " | " + message
		super().__init__(self.message)

class MasterError(Exception):
	'''Errors regarding steam master servers'''
	def __init__(self, message):
		self.message = "Steam Master Server Error | " + message
		super().__init__(self.message)