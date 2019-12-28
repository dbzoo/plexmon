#!/usr/bin/python
from plexapi.myplex import MyPlexAccount
account = MyPlexAccount('<user name>','<password>')
plex = account.resource('<plex server name>'').connect()
print plex._token
