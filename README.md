# Python Source Server Query Library
A Python package for communicating with a Source Engine Server over UDP  
This is currently a work in progess, but performs all 3 non depreciated queries on standard source servers.  
### Known problems/limitations I'm working on:
* Doesn't support The Ship servers as the response packets are different
* Goldensource servers will cause unknown (possibly uncaught) errors

### Untested
* Split package payload decompression
* Split package size attribute detection
* CS:GO servers with `host_players_show` set to 1 as I am currently unable to find a server that uses this

## Installation
`pip install sourceserver`

## Usage
A `SourceServer` object acts as a connection to a Source engine server, with its own socket.  
To instantiate a new `SourceServer` object, simply pass it a connection string in the form `ipv4:port`, the object will attempt to get the server's info, and if the connection fails after max retries, raises a `SourceError`.  

The information regarding a server is stored in `SourceServer.info` and is a dictionary in the form `"info_type": "value"`, you can refresh this info by calling `SourceServer.refreshInfo()`.  

### Methods Overview:
| Method | Use |
|--------|-------------|
| `SourceServer.refreshInfo()` | Updates the source server's info variable |
| `SourceServer.getPlayers()` | Returns a tuple containing each player on the server, and the count<br>(see below) |
| `SourceServer.getRules()` | Returns the server rules as a dictionary of `name: value` pairs |

The `.getPlayers()` method returns (count, players), where count is the count specified in the response packet (can be different from actual number of players returned, see note at https://developer.valvesoftware.com/wiki/Server_queries#Response_Format_2), and players is a tuple of tuples, where each tuple represents a player and is in the format `(index: int, name: str, score: int, duration: float)`.  

Also, it appears that if a player is in the process of joining, they will still be in the players tuple with valid information, but their name will be blank. This may mean that the note on the valve dev website is incorrect, as the player is counted as joined still.

## Example
```python
>>> from sourceserver.sourceserver import SourceServer
>>> srv = SourceServer("89.35.29.5:27085")
>>> print(srv.info["game"]) 
Trouble in Terrorist Town
>>> count, players = srv.getPlayers()
>>> print(count) 
28
>>> print(players[0]) 
(0, 'lakerprime', 0, 6148.7333984375)
```

## License
GNU General Public License v3.0