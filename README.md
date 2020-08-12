# Python Source Server Query Library
A Python package for communicating with a Source Engine Server over UDP  
This is currently a work in progess, but performs all 3 non depreciated queries on standard source servers.  

I push changes to the master branch whenever I finish a session of working on this. If you want the absolute latest version, download the code and use it manually, otherwise install through pip for the latest version I class as stable enough to use.  

### Known problems/limitations I'm working on
* Goldensource servers will cause unknown (possibly uncaught) errors

### New features I'm working on
* Querying master server

### Untested
* Split package payload decompression
* Split package size attribute detection
* CS:GO servers with `host_players_show` set to 1 as I'm currently unable to find a server that uses this
* Getting the players on a server running The Ship when someone is in the process of joining, as it relies on the count returned with the response packet, which may or may not differ from the actual number of players when someone is joining. (This descrepancy has not yet been observed on other servers despite the Valve dev wiki stating otherwise)

## Installation
`pip install sourceserver`

## Usage
A `SourceServer` object acts as a connection to a Source engine server, with its own socket.  
To instantiate a new `SourceServer` object, simply pass it a connection string in the form `ipv4:port`, the object will attempt to get the server's info, and if the connection fails after max retries, raises a `SourceError`.  
Note, all errors that are expected are raised as `SourceError`, which marks the server as closed, but does not actually close the socket so the connection can be re-established.

The information regarding a server is retrieved each time you access the `.info` property, and is a dictionary in the form `"info_type": "value"`.  
Any attempts to set the `.info` property will result in an `AttributeError`.

### Methods Overview:
| Method | Use |
|--------|-------------|
| `SourceServer.getPlayers()` | Returns a tuple containing each player on the server, and the count<br>(see below) |
| `SourceServer.getRules()` | Returns the server rules as a dictionary of `name: value` pairs<br>Note, if the server is running CS:GO, this will time out |
| `SourceServer.close()` | Marks the server as closed and prevents further requests from being made until a successful `retry()` call |
| `SourceServer.retry()` | Attempts to re-establish a connection to the server |
| `SourceServer.ping(places=0)` | Times an info request and returns the time taken in miliseconds rounded to `places` |

The `.getPlayers()` method returns (count, players), where count is the count specified in the response packet (can be different from actual number of players returned, see note at https://developer.valvesoftware.com/wiki/Server_queries#Response_Format_2), and players is a tuple of tuples, where each tuple represents a player and is in the format `(index: int, name: str, score: int, duration: float)`, unless the server is running The Ship, in which case they're in the format `(index: int, name: str, score: int, duration: float, deaths: int, money: int)`

Also, it appears that if a player is in the process of joining, they will still be in the players tuple with valid information, but their name will be blank. This may mean that the note on the valve dev website is incorrect, as the player is counted as joined still.

## Example
```python
>>> from sourceserver.sourceserver import SourceServer
>>> srv = SourceServer("89.35.29.5:27085")
Source Server @ 89.35.29.5:27085 | Connecting...
Source Server @ 89.35.29.5:27085 | Successfully established connection to server
>>> print(srv.info["game"]) 
Trouble in Terrorist Town
>>> print(srv.ping()) 
30.0
>>> print(srv.ping(2)) 
27.03
>>> count, players = srv.getPlayers()
>>> print(count)  
6
>>> print(players[0])
(0, 'Nbx3k', 17, 9938.7001953125)
```

## Discord Server
https://discord.gg/aKDNstq

## License
GNU General Public License v3.0
