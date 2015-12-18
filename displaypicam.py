# displayPiCam
# -*- coding: iso-8859-15 -*-
# Displays pictur-stream from PiCamera hoepfully via X11 forwarding

from __future__ import print_function, division

##### External dependencies: picamera, pygame
##### Module internal dependencies:
##### Python internal dependencies:

##### TODO:
#####       -


__author__ = 'Michael Harig <webaffe@michaelharig.de>'
__version__ = '0.1'
__license__ = '''(c) 2014-2015 all rights reserved'''


import pygame as pg
import picamera as pc


camera = pc.PiCamera()
