#!/usr/bin/python
#import logging
#logging.basicConfig(level=logging.DEBUG)
import plexapi
from plexapi.server import PlexServer
from plexapi.utils import download
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import requests
import signal

os.environ["SDL_FBDEV"] = "/dev/fb0"

baseurl = 'http://plex.local:32400'
token = '<your token>'

screen_w = 800
screen_h = 480
white = pygame.Color(255,255,255)
yellow = pygame.Color(255,255,0)
grey = pygame.Color(192,192,192)
plex = PlexServer(baseurl,token,requests.Session())

def human_time(n):
    n = n // 1000
    r = []
    for b in (3600,60,1):
        d, n = divmod (n, b)
        r.append(d)
    h,m,s = r
    if h:
        return "%d:%02d:%02d" % (h,m,s)
    return "%d:%02d" % (m,s)

class ScrollText(object):
    def __init__(self, surface, text, xpos,ypos, color=yellow, size=48):
        self.surface = surface
        self.x = xpos
        self.y = ypos
        self.color = color
        self.size = size
        # initialize
        self.position = 0
        self.font = pygame.font.SysFont("courier", self.size, bold=True)
        self.setText(text)
    
    def setText(self, text):
        self.text = text
        self.text_surface = self.font.render(text, True, self.color)
        self.width = self.text_surface.get_width()        
        self.needScroll = self.width > screen_w        
        if self.needScroll:
            self.text = self.text + " "*5
            
    def update(self):        
        self.surface.blit(self.text_surface, 
            (self.x, self.y), 
            (self.position, 0, self.surface.get_width(), self.size)
        )
        if not self.needScroll:
            return
        
        self.text = self.text[1:] + self.text[0]
        self.text_surface = self.font.render(self.text , True, self.color)

        if self.position < len(self.text):
            self.position += 1
        else:
            self.position = 0

class MediaInfo(object):
    def __init__(self, surface, client, xpos,ypos, color=grey, size=48):
        self.surface = surface
        self.x = xpos
        self.y = ypos
        self.color = color
        self.size = size
        media = client.media[0]
        self.font = pygame.font.SysFont("courier", size, bold=True)
        self.spheres = (
            self.getSurface(str(media.audioCodec)),
            self.getSurface(str(media.bitrate)+" kbps"),
            self.getSurface("plays: "+str(client.viewCount))
            )
        
    def getSurface(self, text):
        return self.font.render(text, True, self.color)
            
    def update(self):
        offset = 0
        for s in self.spheres:
            self.surface.blit(s, (self.x, self.y + offset), 
                              (0,0, self.surface.get_width(), self.size)
            )
            offset += self.size


class TimeCounter(object):
    def __init__(self, surface, time, elapsed, xpos,ypos, color=yellow, size=48):
        self.surface = surface
        self.x = xpos
        self.y = ypos
        self.color = color
        self.size = size
        self.font = pygame.font.SysFont("courier", size, bold=True)
        self.time = time
        self.elapsed = elapsed
    
    def update(self):        
        text = "%s / %s" % (human_time(self.elapsed),human_time(self.time))
        self.text_surface = self.font.render(text, True, self.color)
        self.elapsed += 1000  # We know we are updated once a second
        if self.elapsed > self.time:
            self.elapsed = self.time
        self.surface.blit(self.text_surface, 
            (self.x, self.y), 
            (0, 0, self.surface.get_width(), self.size)
        )
            
class Image(object):
    def __init__(self, surface, client, x, y):
        if client.parentThumb: # Album
            thumb = client.parentThumb
        elif client.grandparentThumb: # Artist
            thumb = client.grandparentThumb
        else:
            self.thumbImg = None
            return

        w = screen_h - y
        url = plex.transcodeImage(thumb,height=w,width=w)
        filePath = download(url,token,filename='thumb.jpg')
        picture = pygame.image.load(filePath)
        self.thumbImg = pygame.transform.scale(picture,(w,w))
        self.surface = surface
        self.pos = (x,y)
        
    def update(self):
        if self.thumbImg:
            self.surface.blit(self.thumbImg, self.pos)

class Monitor(object):

    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(0)
        self.surface = pygame.display.set_mode((screen_w, screen_h))
        self.stopped()

    def isAlexa(self,sessionKey):
        for client in plex.sessions():
            if client.sessionKey == sessionKey:
                if client.players[0].device == 'Alexa':
                    return client
        return None

    def stopped(self):
        self.spheres = (
            ScrollText(self.surface, "Plex Song Monitor", 0, 0),
            ScrollText(self.surface, "Nothing is currently being played", 0, 100, white, 40),
        )        
        self.currentSession = 0

    def check(self, data):
        typ = data.get('type')
        if typ == 'playing' and "PlaySessionStateNotification" in data:
            playing = data["PlaySessionStateNotification"][0]
            thisSession = int(playing['sessionKey'])
            state = playing['state']

            if state == 'playing':
                if thisSession == self.currentSession:
                    return
                client = self.isAlexa(thisSession)
                if client:
                    elapsed = playing.get('viewOffset',0)
                    album = client.album()
                    album_str = album.title
                    if album.year:
                        album_str += ' (%s)' % album.year
                    self.spheres = (
                        ScrollText(self.surface, client.title, 0, 0, white, 64),
                        ScrollText(self.surface, client.artist().title, 0, 64),
                        ScrollText(self.surface, album_str, 0, 112),
                        MediaInfo(self.surface, client, 300, 220),
                        TimeCounter(self.surface, client.duration, elapsed, 0, 160),
                        Image(self.surface, client, 0, 220)
                    )                                            
                    self.currentSession = thisSession

            elif state == 'stopped' and thisSession == self.currentSession:
                self.stopped()

    def run(self):
        ffs = plex.startAlertListener(self.check)
        try:
            self.update()
        finally:
            ffs.stop()

    def update(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(1) # 1 fps
            self.surface.fill((0, 0, 0, 255))
            for thing in self.spheres:
                thing.update()
            pygame.display.flip()

def handler(signum, frame):
        pass

def main():
    signal.signal(signal.SIGHUP, handler)
    try:
        Monitor().run()
    except KeyboardInterrupt:
        print('shutting down')

if __name__ == '__main__':
    main()
