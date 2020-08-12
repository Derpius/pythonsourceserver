import socket
import re
import time
from sourceserver.peekablestream import PeekableStream
from sourceserver.exceptions import MasterError

class MasterServer(object):
	'''
	Represents the Steam master servers as a single object, and implements functions to abstract requests.\n
	Note, requests to Steam master servers are heavily rate limited, so use filters and wait about 2 minutes between queries.
	'''

	def __init__(self):
		# Define region codes
		self.US_EAST_COAST     = 0x00
		self.US_WEST_COAST     = 0x01
		self.SOUTH_AMERICA     = 0x02
		self.EUROPE            = 0x03
		self.ASIA              = 0x04
		self.AUSTRALIA         = 0x05
		self.MIDDLE_EAST       = 0x06
		self.AFRICA            = 0x07
		self.REST_OF_THE_WORLD = 0xFF # Note, this actually selects EVERY REGION

		# Define valid filters and their types
		self.FILTERS = {
			"gamedir":       "str",
			"map":           "str",
			"appid":         "int",
			"napp":          "int",
			"gametype":      "tuple",
			"gamedata":      "tuple",
			"gamedataor":    "tuple",
			"name_match":    "str",
			"version_match": "str",
			"gameaddr":      "str"
		}
		# The boolean filters in the actual query behave strangely,
		# so this dict defines false/true (to match index to bool numerical value) pairs for each so the string builder knows what to do
		self.BOOLEAN_FILTERS = {
			"dedicated":          ("\\nor\\1\\dedicated\\1", "\\dedicated\\1"),
			"secure":             ("\\nor\\1\\secure\\1", "\\secure\\1"),
			"linux":              ("\\nor\\1\\linux\\1", "\\linux\\1"),
			"password":           ("\\password\\0", "\\nor\\1\\password\\0"),
			"empty":              ("\\empty\\1", "\\noplayers\\1"),
			"full":               ("\\full\\1", "\\nor\\1\\full\\1"),
			"proxy":              ("\\nor\\1\\proxy\\1", "\\proxy\\1"),
			"whitelisted":        ("\\nor\\1\\white\\1", "\\white\\1"),
			"collapse_addr_hash": ("\\nor\\1\\collapse_addr_hash\\1", "\\collapse_addr_hash\\1")
		}

		# Define connection retry params
		self.MAX_RETRIES = 5
		self.TIME_UNTIL_RETRY = float(3)
		self.RATE_LIMIT = 300 # seconds to wait before trying to query again if failed

		# Max ips to read before stopping
		# (this is due to a hard cap on the number of servers the master server will return before timing out the connection)
		self.QUERY_CAP = 10

		# Init socket
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.setblocking(0)

		# Set socket connection
		self.socket.connect((socket.gethostbyname("hl2master.steampowered.com"), 27011))

	def _log(self, *args):
		print("Steam Master Server Server | ", *args, sep="")

	def _response(self) -> bytes:
		'''Listens for a response from server, raises MasterError if max retries is hit'''
		retries = 0
		startTime = time.time()
		while True:
			try:
				return self.socket.recv(4096)
			except socket.error:
				if time.time() - startTime > self.TIME_UNTIL_RETRY * (1 - retries / (self.MAX_RETRIES + 1)):
					if retries >= self.MAX_RETRIES: raise MasterError("Connection failed after max retries (" + str(self.MAX_RETRIES) + ")")
					retries += 1
					startTime = time.time()

	def _request(self, request: bytes) -> bytes:
		'''Makes a UDP request and returns response as bytes'''
		self.socket.sendall(request)
		return self._response()

	def _scanInt(self, chars: PeekableStream, bits: int, signed: bool = True, bigEndian = False) -> int:
		'''Scans an integer of length bits'''
		if bits % 8 != 0: raise ValueError("bits is not a multiple of 8")
		byteString = bytes()
		for _ in range(int(bits / 8)): byteString += b"%c" % chars.moveNext()
		return int.from_bytes(byteString, ("big" if bigEndian else "little"), signed=signed)
	
	def _tokeniseIPs(self, response: bytes) -> str:
		chars = PeekableStream(response)

		while chars.next is not None:
			conStr = ""
			conStr += str(chars.moveNext()) + "." + str(chars.moveNext()) + "." + str(chars.moveNext()) + "." + str(chars.moveNext()) + ":"
			conStr += str(self._scanInt(chars, 16, False, True))
			yield conStr
		
	def _getIPs(self, header: bytes, seed: str, filters: str) -> list:
		request = header + seed.encode("utf-8") + b"\x00" + filters.encode("utf-8") + b"\x00"

		response = self._request(request)
		return list(self._tokeniseIPs(response[6:]))
	
	def _validateAndBuildFilters(self, filters: dict) -> str:
		'''Validates a filter dict and builds a filter string from it'''
		filterString = ""

		for key, val in filters.items():
			if key in ("nor", "nand"):
				if type(val).__name__ != "dict": raise ValueError("Nor/Nand filter value is not a set of filters")
				filterString += "\\%s\\%d" % (key, len(val))
				filterString += self._validateAndBuildFilters(val)
				continue
			
			if key in self.BOOLEAN_FILTERS:
				if type(val).__name__ != "bool": raise ValueError("Boolean filter value not a boolean")
				filterString += self.BOOLEAN_FILTERS[key][int(val)]
				continue

			if key not in self.FILTERS.keys() or type(val).__name__ != self.FILTERS[key]:
				raise ValueError("Filter '" + key + "' is invalid or has an invalid value")
			filterString += "\\%s\\%d" % (key, str(val))
		
		return filterString

	def query(self, region: int, filters: dict = {}) -> list:
		'''
		Queries the master server with the specified filters\n
		See the GitHub for documentation on how to use filters
		'''
		# Handle filters
		filterString = self._validateAndBuildFilters(filters) # This raises error if the filter dict is invalid

		# Handle rate limiting on initial connection
		while True:
			try: ipList = self._getIPs(b"\x31%c" % region, "0.0.0.0:0", filterString); break
			except MasterError:
				self._log("Unable to perform initial connection (likely rate limiting), waiting " + str(self.RATE_LIMIT) + " seconds before retrying")
				time.sleep(self.RATE_LIMIT)
		
		# Request IPs until either terminating IP or max queries (to prevent rate limiting mid query)
		queriesSent = 1
		yield ipList[:-1]

		while ipList[-1] != "0.0.0.0:0" and queriesSent < self.QUERY_CAP:
			ipList = self._getIPs(b"\x31%c" % region, ipList[-1], filterString)
			queriesSent += 1
			yield ipList[:-1]
