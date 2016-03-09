# Captures and displays video images
# Dependencies: PyGame >= 1.9
from __future__ import print_function, division, absolute_import

###################################################################
# TODO:
#       - make more OO       IN PROGRESS
#       - split screen to display last/loaded still image side by side with video
#       - distance measuring tool
#               - text input & output in PyGame
#               - make lines with nice whiskers
#               - save & load calibration (only values?)
#       - move video offsets with arrow keys
#       - make it possible to use different video & screenshot resolutions
#           This will be difficult, because the UVC device driver on Linux does not support
#           still image capture :-( (atm. see http://www.ideasonboard.org/uvc/ for current info)
#           (screenshot always in max cam resolution?)
#           current behaviour: screenshot res = vid res
#       - DEBUG: Behaviour on draw calib line is not 100% consistent. Sometimes more than one calibration
#               is invoked, sometimes it does not recognize mouse button up.
###################################################################


__author__ = 'Michael Harig <floss@michaelharig.de>'
__version__ = '0.2'
__license__ = '''GPL v3'''


import os.path as op
import argparse
import sys
import math
from collections import namedtuple
from operator import add, sub

# Python2 & 3 compatibility
try: import configparser
except NameError: import ConfigParser as configparser

# Python2 & 3 compatibility
try: input = raw_input
except NameError: pass

# PyGame >= 1.9 must be installed!
import pygame
import pygame.camera as camera
from pygame.locals import HWSURFACE,DOUBLEBUF,RESIZABLE

# define the mouse "buttons"
( LEFT,
  MIDDLE,
  RIGHT,
  WHEEL_UP,
  WHEEL_DOWN) = range(1,6)


# just make args.device global
DEVICE = ''

INIFILE = '.dc'


# objects that are drawn to foreground or other surface, like lines and text
PGObject = namedtuple('PGobject', ('drawFunction', 'surface', 'parameters'))

# Calibration values
CalibValue = namedtuple('CalibValue', ('pixels', 'worlddim'))

# Measured values
class MeasuredValue(object):
    def __init__(self, _pixels, _result):
        self.pixels = _pixels
        self.result = _result


### main PyGame loop
class PGLoop(object):

    [DRAGGING, DRAWCALIB, DRAWMEASURE, NONE] = range(4)
    def __init__(self, _args, _cfg):
        self.args = _args
        self.cfg = _cfg

        self.state = PGLoop.NONE
        self.measuredValues = []        # list of namedtuples
        self.calibValues = []           # list of namedtuples
        self.WORLDSCALE = _cfg.getfloat('MEASURING', 'worldscale')

        self.calibLines = []
        self.measureLines = []


    def __call__(self):
        # Flags and more
        DRAWCALIB_KEY = False
        DRAWMEASURE_KEY = False
        XOFFSET = 0
        YOFFSET = 0
        DONE = False
        IMGCOUNTER = 1

        # video image
        snapshot = pygame.surface.Surface((self.args.screen.get_width(), self.args.screen.get_height()), 0, self.args.screen)

        # lines & text
        foreground = pygame.surface.Surface((self.args.screen.get_width(), self.args.screen.get_height()))
        foreground.convert()        # for faster blitting
        foreground = foreground.convert_alpha() # faster blitting with transparent color

        while not DONE:
            ### event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    DONE = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        DONE = True
                    elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                        DRAWCALIB_KEY = True
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        DRAWMEASURE_KEY = True
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                        DRAWCALIB_KEY = False
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        DRAWMEASURE_KEY = False
                    elif event.key == pygame.K_DELETE:
                        if not DRAWCALIB_KEY:
                            self.deleteMeasurements()
                        else:
                            self.deleteCalibration()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == RIGHT:    # right mouse button click
                        img = self.args.cam.get_image()
                        img = pygame.transform.flip(img, self.args.flipHorizontal, self.args.flipVertical)
                        snapName = 'snapshot_' + str(IMGCOUNTER) + '.png'
                        while op.exists(snapName):
                            IMGCOUNTER += 1
                            snapName = 'snapshot_' + str(IMGCOUNTER) + '.png'

                        # draw the lines if requested
                        if DRAWCALIB_KEY or DRAWMEASURE_KEY:
                            for o in self.calibLines:
                                o.drawFunction(img, *o.parameters)
                            for o in self.measureLines:
                                o.drawFunction(img, *o.parameters)

                        pygame.image.save(img, snapName)
                        print('Saved snapshot as', snapName)
                        IMGCOUNTER += 1
                    elif event.button == LEFT:
                        if self.state == PGLoop.DRAGGING:
                            self.state = PGLoop.NONE
                        elif self.state == PGLoop.DRAWCALIB:
                            pos = vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET))
                            distance = math.sqrt( (pos[1]-lineOrig[1])**2 + (pos[0]-lineOrig[0])**2 )
                            print('pixels: ', distance)
                            worlddim = None
                            while worlddim == None:
                                d = input('Please enter distance in real world: ')
                                try:
                                    worlddim = float(d)
                                except ValueError:
                                    print('You MUST enter a valid floating point number!')

                            self.calibValues.append(CalibValue(distance, worlddim))
                            self.updateCalibration()
                            self.state = PGLoop.NONE
                            # add line to foreground 'til death
                            line = PGObject(pygame.draw.line, foreground, ((255, 0, 0), lineOrig, pos, 1))
                            self.calibLines.append(line)
                        elif self.state == PGLoop.DRAWMEASURE:
                            pos = vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET))
                            distance = math.sqrt( (pos[1]-lineOrig[1])**2 + (pos[0]-lineOrig[0])**2 )
                            self.measuredValues.append(MeasuredValue(distance, distance * self.WORLDSCALE))
                            print('Measured distance: ', distance * self.WORLDSCALE, ' your unit; average: ',
                                self.getMeasuredValuesAverage())

                            self.state = PGLoop.NONE
                            # add line to foreground 'til death
                            line = PGObject(pygame.draw.line, foreground, ((0, 0, 255), lineOrig, pos, 1))
                            self.measureLines.append(line)
                elif not self.state == PGLoop.DRAGGING and event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
                    pygame.mouse.get_rel()  # init the relative mouse movement
                    if DRAWCALIB_KEY:
                        lineOrig = vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET))
                        self.state = PGLoop.DRAWCALIB
                    elif DRAWMEASURE_KEY:
                        lineOrig = vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET))
                        self.state = PGLoop.DRAWMEASURE
                    elif not self.args.scale:
                        self.state = PGLoop.DRAGGING
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == PGLoop.DRAGGING:
                        XOFFSET, YOFFSET = vectorAdd((XOFFSET, YOFFSET), pygame.mouse.get_rel())
                    elif self.state == PGLoop.DRAWCALIB:
                        # temporary line
                        foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                        pygame.draw.line(foreground, (255, 0, 0), lineOrig, vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET)), 1)
                    elif self.state == PGLoop.DRAWMEASURE:
                        # temporary line
                        foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                        pygame.draw.line(foreground, (0, 0, 255), lineOrig, vectorSub(pygame.mouse.get_pos(), (XOFFSET, YOFFSET)), 1)
                elif event.type == pygame.VIDEORESIZE:
                    self.args.screen = pygame.display.set_mode(event.dict['size'], HWSURFACE|DOUBLEBUF|RESIZABLE)
                    self.args.screen.convert()
                    foreground = pygame.surface.Surface((self.args.screen.get_width(), self.args.screen.get_height()), pygame.SRCALPHA)
                    foreground.convert()
                    foreground = foreground.convert_alpha() # faster blitting with transparent color
                    # calibration is no longer valid:
                    self.deleteCalibration()

            ### video diplay
            # to get fastest possible framerate & no flicker (near) all updating should be
            # made here
            if self.args.cam.query_image():
                img = self.args.cam.get_image()

                if self.args.scale:
                    snapshot = pygame.transform.scale(img, (self.args.screen.get_width(), self.args.screen.get_height()))
                    snapshot = pygame.transform.flip(snapshot, self.args.flipHorizontal, self.args.flipVertical)
                    snapshot.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                    uRect = self.args.screen.blit(snapshot, (0, 0))
                else:
                    img = pygame.transform.flip(img, self.args.flipHorizontal, self.args.flipVertical)
                    img.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                    uRect = self.args.screen.blit(img, (XOFFSET,YOFFSET))
                pygame.display.update(uRect)

                # draw foreground with all objects, as fast as camera framerate
                if self.state != PGLoop.DRAWCALIB and self.state != PGLoop.DRAWMEASURE:
                    erased = []
                    for o in self.calibLines:
                        if o.surface not in erased:
                            o.surface.fill((0,0,0,0))    # erase surface & make it transparent
                            erased.append(o.surface)
                        o.drawFunction(o.surface, *o.parameters)
                    for o in self.measureLines:
                        if o.surface not in erased:
                            o.surface.fill((0,0,0,0))    # erase surface & make it transparent
                            erased.append(o.surface)
                        o.drawFunction(o.surface, *o.parameters)

                # does not work:
                #pygame.display.set_caption(DEVICE + 'with frame rate: {:0.2f} fps'.format(_clock.get_fps()))

        pygame.quit()
        sys.exit()


    def getMeasuredValuesAverage(self):
        if len(self.measuredValues) > 0:
            sum = 0
            for m in self.measuredValues:
                sum += m.result
            return sum / len(self.measuredValues)
        else:
            return 0.0


    def updateMeasuredValues(self):
        '''Iterates over measured distances and calculates arithmetic mean.'''

        sum = 0
        for m in self.measuredValues:
            m.result = m.pixels * self.WORLDSCALE
            sum += m.result
            print('New distance: ', m.result)

        if len(self.measuredValues) > 0:
            print('New average distance:', sum / len(self.measuredValues))


    def updateCalibration(self):
        '''Iterates over calibration levels and calculates arithmetic mean, then updates measured distances.'''
        sum = 0
        for c in self.calibValues:
            if c.pixels > 0:
                sum += c.worlddim / c.pixels

        if sum > 0:
            self.WORLDSCALE = sum / len(self.calibValues)
        else:
            self.WORLDSCALE = 1.0
        print('New scaling: ', self.WORLDSCALE, ' your unit/pixels')
        self.cfg.set('MEASURING', 'worldscale', self.WORLDSCALE)
        with open(INIFILE, 'wb') as fp:
            self.cfg.write(fp)

        self.updateMeasuredValues()


    def deleteMeasurements(self):
        self.measuredValues = []
        self.measureLines = []


    def deleteCalibration(self):
        self.measuredValues = []
        self.calibValues = []
        self.WORLDSCALE = 1.0
        self.measureLines = []
        self.calibLines = []



def vectorAdd(_a, _b):
    return tuple(map(add, _a, _b))


def vectorSub(_a, _b):
    return tuple(map(sub, _a, _b))


def printVideoDevices():
    '''Prints a list of available video devices'''
    camera.init()
    print(camera.list_cameras())


def initCam(_camera='/dev/video0', _res=(640, 480)):
    '''Wants the name of the wanted camera device. Returns the device object and the resolution (w,h)'''

    camera.init()
    cam = camera.Camera(_camera, _res)

    if cam is None:
        raise Exception('Cannot connect to camera. Maybe in use by other program?')

    try:
        cam.start()
    except:
        raise Exception('Cannot connect to camera. Maybe in use by other program?')

    return cam


def initPygame(_windowSize=(640, 480)):
    pygame.init()

    # get display resolution and adjust screen size
    vidinfo = pygame.display.Info()
    w = min(vidinfo.current_w, _windowSize[0])
    h = min(vidinfo.current_h, _windowSize[1])

    screen = pygame.display.set_mode((w, h), HWSURFACE|DOUBLEBUF|RESIZABLE)
    clock = pygame.time.Clock()
    return screen, clock


def makeParser():
    argparser = argparse.ArgumentParser(description='''Display camera video with pygame (>= 1.9).
    Left mouse button + mouse motion drags video.
    Right mouse button takes screenshots, CTRL + right mouse button saves with drawn lines.
    CTRL + left mouse button + mouse motion draws calibration line.
    SHIFT + left mouse button draws measuring line.
    DEL deletes measured values.
    CTRL + DEL deletes calibration (including measured values).
    ESC exits.

    Please start this program from command line!''', add_help=False)
    argparser.add_argument('-l', '--list', action='store_true', help='Print avaiable video devices')
    argparser.add_argument('-s', '--scale', action='store_true', help='Scale video, otherwise it is displayed 1:1 and may be dragged with the mouse')
    argparser.add_argument('-m', '--flipHorizontal', action='store_true', help='Flip video horizontal')
    argparser.add_argument('-v', '--flipVertical', action='store_true', help='Flip video vertical')
    argparser.add_argument('-d', '--device', nargs = '?', default='/dev/video0', help='Name of the camera device')
    argparser.add_argument('-w', '--width', nargs = '?', type=int, default=176, help='Width of view')
    argparser.add_argument('-h', '--height', nargs = '?', type=int, default=144, help='Height of view')
    argparser.add_argument('-?', '--help', action='store_true', help='Print usage information')

    return argparser


def main(_args):
    global DEVICE
    argparser = makeParser()
    args = argparser.parse_args(_args)

    if args.list:
        printVideoDevices()
        exit()
    elif args.help:
        argparser.print_help()
        exit()

    cam = initCam(args.device, (args.width, args.height))

    fps = 30

    screen, clock = initPygame(cam.get_size())
    print('Using camera', args.device)
    print('Using camera resolution', cam.get_size())
    print('Using initial screen size (%d, %d)'%(screen.get_width(), screen.get_height()))
    if args.scale:
        print('Scaling video to screen size')

    DEVICE = args.device
    pygame.display.set_caption(args.device)

    args.cam = cam
    args.fps = fps
    args.screen = screen
    args.clock = clock

    cfg = configparser.RawConfigParser()
    cfg.read(INIFILE)
    if not cfg.has_section('MEASURING'):
        cfg.add_section('MEASURING')
    if not cfg.has_option('MEASURING', 'worldscale'):
        cfg.set('MEASURING', 'worldscale', 1.0)
    # TODO: handle options for screen resolution, camera resolution, ...

    loop = PGLoop(args, cfg)
    loop()

    pygame.quit()



if __name__ == '__main__':
    main(sys.argv[1:])
