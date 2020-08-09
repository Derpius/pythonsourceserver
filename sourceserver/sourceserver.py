import socket
import struct
import re
import time
import bz2
from sourceserver.peekablestream import PeekableStream

class SourceError(Exception):
	'''Errors regarding source engine servers, automatically closes the socket when raised'''
	def __init__(self, server, message):
		self.message = "Source Server Error @ " + server.ip + ":" + str(server.port) + " | " + message
		super().__init__(self.message)
		server.close()
		

class SourceServer():
	'''
	Represents a source engine server, and implements functions to abstract requests.\n
	connectionString should be in the form ipv4:port
	'''
	
	def __init__(self, connectionString: str):
		self.MAX_RETRIES = 5
		self.TIME_UNTIL_RETRY = float(3)
		self.isClosed = False

		if not self._validConString(connectionString): raise ValueError("Connection string invalid")

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.setblocking(0)
		self.ip, self.port = connectionString.split(":")
		self.port = int(self.port)

		self.refreshInfo()
		self._log("Connected successfully")

	def _log(self, *args):
		print("Source Server @ ", self.ip, ":", self.port, " | ", *args, sep="")

	def _validConString(self, conString: str) -> bool:
		'''Validates a connection string'''
		pat = re.compile(r"^(?:(?:[0-9]|[0-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[0-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]):(?:[0-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[0-5][0-9][0-9][0-9][0-9]|6[0-4][0-9][0-9][0-9]|65[0-4][0-9][0-9]|655[0-2][0-9]|6553[0-5])$")
		if re.match(pat, conString): return True
		return False

	def close(self):
		if self.isClosed: self._log("Connection to server already closed"); return
		self._log("Closing connection to server.")
		self.socket.close()
		self.isClosed = True
	
	def _response(self) -> bytes:
		'''Listens for a response from server, raises SourceError if max retries is hit'''
		retries = 0
		startTime = time.time()
		while True:
			try: return self.socket.recv(4096)
			except socket.error:
				if time.time() - startTime > self.TIME_UNTIL_RETRY * (1 - retries / (self.MAX_RETRIES + 1)):
					if retries >= self.MAX_RETRIES: raise SourceError(self, "Connection failed after max retries (" + str(self.MAX_RETRIES) + ")")
					retries += 1
					startTime = time.time()

	def _request(self, request: bytes) -> bytes:
		'''Makes a UDP request and returns response as bytes'''
		if self.isClosed: raise SourceError(self, "Request attempt made on closed socket")
		self.socket.sendto(request, (self.ip, self.port))
		return self._response()
	
	def _packetSplit(self, packet: bytes) -> bool:
		'''Checks whether a packet is split or not, returns true if so'''
		header = self._scanInt(PeekableStream(packet[0:4]), 32)
		if header == -1: return False
		if header == -2: return True
		raise SourceError(self, "Invalid packet header")

	def _processSplitPacket(self, splitPacket: bytes) -> bytes:
		'''Orders, concatenates, and decompresses the payloads of a split packet'''
		if not self._packetSplit(splitPacket): raise SourceError(self, "Attempted to process singular packet as split")
		# Define split packet attributes
		packetID = self._scanInt(PeekableStream(splitPacket[4:8]), 32)
		totalPackets = splitPacket[8]
		compressed = packetID < 0
		sizeAttrPresent = not (self.info["protocol"] == 7 and self.info["id"] in (215, 17550, 17700, 240))

		# Define empty array to order the packets into
		packets = [None] * totalPackets

		# Retrieve packets from socket and order into packets list
		packets[splitPacket[9]] = splitPacket
		for _ in range(totalPackets - 1):
			packet = self._response()
			if not self._packetSplit(packet): raise SourceError(self, "Expected split packet from server, got singular")
			elif self._scanInt(PeekableStream(packet[4:8]), 32) != packetID: raise SourceError(self, "Expected split packet with same ID, got different")
			packets[packet[9]] = packet
		
		# Extract and join payloads and compression attribute if present
		payload = bytes()
		for packet in packets:
			payload += packet[(12 if sizeAttrPresent else 10):]

		# If compressed, get compression data, remove from payload, and decompress
		if compressed:
			compHeader = PeekableStream(payload)
			compSize = self._scanInt(compHeader, 32)
			payload = bz2.decompress(payload[64:])
			if len(payload) != compSize: raise SourceError(self, "Decompressed payload size does not match packet attribute")
		
		return payload
	
	def _scanString(self, chars: PeekableStream) -> str:
		'''Scans a string until null char'''
		ret = bytes()
		while chars.next != 0x00:
			c = chars.moveNext()
			if c is None:
				raise SourceError(self, "A string ran off the end of the response")
			ret += b"%c" % c
		chars.moveNext()
		ret = str(ret, encoding="utf-8")
		return ret

	def _scanInt(self, chars: PeekableStream, bits: int, signed: bool = True) -> int:
		'''Scans an integer of length bits'''
		if bits % 8 != 0: raise ValueError("bits is not a multiple of 8")
		byteString = bytes()
		for _ in range(int(bits / 8)): byteString += b"%c" % chars.moveNext()
		return int.from_bytes(byteString, "little", signed=signed)

	def _scanFloat(self, chars: PeekableStream, bits: int) -> float:
		'''Scans a float of length bits'''
		if bits % 8 != 0: raise ValueError("bits is not a multiple of 8")
		byteString = bytes()
		for _ in range(int(bits / 8)): byteString += b"%c" % chars.moveNext()
		return struct.unpack("<f", byteString)[0]
	
	def _tokeniseInfo(self, inf: bytes) -> dict:
		'''Tokenises info response into usable dictionary'''
		tokens = {
			"protocol": "byte",
			"name": "str", "map": "str", "folder": "str", "game": "str",
			"id": "short",
			"players": "byte", "max_players": "byte", "bots": "byte",
			"server_type": "byte", "environment": "byte", "visibility": "byte", "VAC": "byte", "version": "str",
			"EDF": "byte"
		}

		chars = PeekableStream(inf)
		for name, typ in tokens.items():
			if typ == "byte":
				tokens[name] = chars.moveNext()
			elif typ == "str":
				tokens[name] = self._scanString(chars)
			elif typ == "short":
				tokens[name] = self._scanInt(chars, 16)
			
			if name == "game" and tokens[name] == "The Ship": raise SourceError(self, "'The Ship' servers not currently supported due to different response params, sorry.")
			#elif name == "server_type" and b"%c" % tokens[name] == b"p": raise SourceError(self, "SourceTV proxies not supported.")
			# looks like the code could work with proxies so I've commented out the line that raises an error, untested though
		
		if tokens["EDF"] & 0x80: tokens.update({ "port": self._scanInt(chars, 16) })
		if tokens["EDF"] & 0x10: tokens.update({ "steam_id": self._scanInt(chars, 64, False) })
		if tokens["EDF"] & 0x40:
			tokens.update({ "sourceTV_port": self._scanInt(chars, 16) })
			tokens.update({ "sourceTV_name": self._scanString(chars) })
		if tokens["EDF"] & 0x20: tokens.update({ "keywords": self._scanString(chars) })
		if tokens["EDF"] & 0x01:
			tokens.update({ "game_id": self._scanInt(chars, 64, False) })
			tokens["id"] = 16777215 & tokens["game_id"]
		
		return tokens

	def _tokenisePlayers(self, plrs: bytes) -> tuple:
		'''Tokenises players response into usable array'''
		chars = PeekableStream(plrs)
		player = []
		while chars.next is not None:
			player.append(chars.moveNext())
			player.append(self._scanString(chars))
			player.append(self._scanInt(chars, 32))
			player.append(self._scanFloat(chars, 32))

			yield tuple(player)
			player = []
	
	def _tokeniseRules(self, rules: bytes) -> dict:
		rulesDict = {}
		chars = PeekableStream(rules)
		for _ in range(self._scanInt(chars, 16)):
			rulesDict.update({ self._scanString(chars): self._scanString(chars) })
		
		return rulesDict
	
	def refreshInfo(self):
		'''Gets the server's information and assigns it to self.info'''
		response = self._request(bytes.fromhex("FF FF FF FF 54 53 6F 75 72 63 65 20 45 6E 67 69 6E 65 20 51 75 65 72 79 00"))
		if self._packetSplit(response): response = self._processSplitPacket(response)
		if len(response) < 23 or response[4] != 0x49: raise SourceError(self, "Info response header invalid")

		# Tokenise and return info
		tokens = self._tokeniseInfo(response[5:])
		self.info = tokens
	
	def getPlayers(self) -> tuple:
		'''
		Gets a list of all players on the server\n
		returns (count: int, players: tuple)\n
		If server is running CS:GO and has disabled returning players, connection times out\n
		If server is running CS:GO and has been set to only return max players and server uptime, returns (max players: int, server uptime: float)
		'''

		if self.info["game"] == "Counter-Strike: Global Offensive": self._log("Warning, server is running CS:GO, expect connection timeout if set to not show players")

		# Send challenge request
		challengeResponse = self._request(bytes.fromhex("FF FF FF FF 55 FF FF FF FF"))
		if len(challengeResponse) != 9 or challengeResponse[4] != 0x41: raise SourceError(self, "Challenge response header invalid")

		# Get player list
		response = self._request(bytes.fromhex("FF FF FF FF 55") + challengeResponse[5:])
		if self._packetSplit(response): response = self._processSplitPacket(response)
		if len(response) < 6 or response[4] != 0x44: raise SourceError(self, "Players response header invalid")
		if self.info["game"] == "Counter-Strike: Global Offensive" and len(response) == 9:
			self._log("Warning, CS:GO server has only returned max players and server uptime")
			return response[5], self._scanFloat(PeekableStream(response[6:]), 32)
		
		# Tokenise and return players
		players = tuple(self._tokenisePlayers(response[6:]))
		return len(players), players
	
	def getRules(self) -> dict:
		'''
		Gets a list of all rules on the server\n
		returns rules as a dictionary of name: value pairs
		'''

		# Check if the game the server is running is CS:GO, if so, log message and return
		if self.info["game"] == "Counter-Strike: Global Offensive": self._log("CS:GO servers don't support rules requests"); return

		# Send challenge request
		challengeResponse =    self._request(bytes.fromhex("FF FF FF FF 56 FF FF FF FF"))
		if len(challengeResponse) != 9 or challengeResponse[4] != 0x41: raise SourceError(self, "Challenge response header invalid")

		# Get rules list
		response = self._request(bytes.fromhex("FF FF FF FF 56") + challengeResponse[5:])
		if self._packetSplit(response): response = self._processSplitPacket(response)
		if len(response) < 7 or response[4] != 0x45: raise SourceError(self, "Rules response header invalid")

		# Tokenise and return rules
		return self._tokeniseRules(response[5:])