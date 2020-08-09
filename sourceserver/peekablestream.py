class PeekableStream:
	def __init__(self, iterator):
		self.iterator = iter(iterator)
		self._fill()

	def _fill(self):
		try:
			self.next = next(self.iterator)
		except StopIteration:
			self.next = None

	def moveNext(self):
		ret = self.next
		self._fill()
		return ret