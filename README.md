# Python Source Server Query Library
A Python package for communicating with a Source Engine Server over UDP  

I push changes to the master branch whenever I finish a session of working on this. If you want the absolute latest version, download the code and use it manually, otherwise install through pip for the latest version I class as stable enough to use in your own projects.  

### Untested
* Split package payload decompression
* Split package size attribute detection
* CS:GO servers with `host_players_show` set to 1 as I'm currently unable to find a server that uses this
* Getting the players on a server running The Ship when someone is in the process of joining, as it relies on the count returned with the response packet, which may or may not differ from the actual number of players when someone is joining. (This descrepancy has not yet been observed on other servers despite the Valve dev wiki stating otherwise)

## Installation
`pip install sourceserver`

## Basic Usage
A [`SourceServer`](https://github.com/Derpius/pythonsourceserver/wiki/SourceServer) object acts as a connection to a Source engine server, with its own socket.  
To instantiate a new `SourceServer` object, simply pass it a connection string in the form `ipv4:port`, the object will attempt to get the server's info, and if the connection fails after max retries, raises a `SourceError`.  
Note, all errors that are expected are raised as `SourceError`, which marks the server as closed, but does not actually close the socket so the connection can be re-established.  
The information regarding a server is retrieved each time you access the `.info` property, and is a dictionary in the form `"info_type": "value"`.  

A [`MasterServer`](https://github.com/Derpius/pythonsourceserver/wiki/MasterServer) object lets you query the Steam master servers, see [the wiki](https://github.com/Derpius/pythonsourceserver/wiki) for details

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

## Discord Bot
https://github.com/Derpius/pythonsourceserverdiscordbot

## License
GNU General Public License v3.0
