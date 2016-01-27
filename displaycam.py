# Captures and displays video images
from __future__ import print_function, division, absolute_import

###################################################################
# TODO:
#       - make OO       IN PROGRESS
#       - flags for vertical mirror, horizontal mirror
#       - split screen to display last/loaded still image side by side with video
#       - distance measuring tool       IN PROGRESS
#               - text input & output, allow more calibration measurement points
#       - screenshots with lines when CTRL or SHIFT is pressed with right mouse button
#       - move video offsets with arrow keys
#       - make possible to use different video & screenshot resolutions
#           (screenshot always in max cam resolution?)
#           current behaviour: screenshot res = vid res
###################################################################


__author__ = 'Michael Harig <floss@michaelharig.de>'
__version__ = '0.1'
__license__ = '''GPL v3'''


import os.path as op
import argparse
import sys
import math
from collections import namedtuple

# Python2 & 3 compatibility
try: input = raw_input
except NameError: pass


import pygame
import pygame.camera as camera
from pygame.locals import HWSURFACE,DOUBLEBUF,RESIZABLE

# define the mouse "buttons"
(   LEFT,
    MIDDLE,
    RIGHT,
    WHEEL_UP,
    WHEEL_DOWN) = range(1,6)


# just make args.device global
DEVICE = ''


# objects that are drawn to foreground, like lines and text
PGObject = namedtuple('PGobject', ('drawFunction', 'parameters'))

# Calibration values
CalibValue = namedtuple('CalibValue', ('pixels', 'worlddim'))

# Measured values
class MeasuredValue(object):
    def __init__(self, _pixels, _result):
        self.pixels = _pixels
        self.result = _result



class PGLoop(object):

    [DRAGGING, DRAWCALIB, DRAWMEASURE, NONE] = range(4)
    def __init__(self, _cam, _fps, _screen, _clock, _scale):
        self.cam = _cam
        self.fps = _fps
        self.screen = _screen
        self.clock = _clock
        self.scale = _scale

        self.state = self.NONE
        self.measuredValues = []        # list of namedtuples
        self.calibValues = []           # list of namedtuples
        self.WORLDSCALE = 1.0

        self.calibLines = []
        self.measureLines = []


    def __call__(self):
        DRAWCALIB_KEY = False
        DRAWMEASURE_KEY = False
        XOFFSET = 0
        YOFFSET = 0
        DONE = False
        IMGCOUNTER = 1

        # video image
        snapshot = pygame.surface.Surface((self.screen.get_width(), self.screen.get_height()), 0, self.screen)

        # lines & text
        foreground = pygame.surface.Surface((self.screen.get_width(), self.screen.get_height()))
        foreground.convert()        # for faster blitting
        foreground = foreground.convert_alpha() # faster blitting with transparent color

        while not DONE:
            ### event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
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
                        img = self.cam.get_image()

                        snapName = 'snapshot_' + str(IMGCOUNTER) + '.png'
                        while op.exists(snapName):
                            IMGCOUNTER += 1
                            snapName = 'snapshot_' + str(IMGCOUNTER) + '.png'
                        pygame.image.save(img, snapName)
                        print('Saved snapshot as', snapName)
                        IMGCOUNTER += 1
                    elif event.button == LEFT:
                        if self.state == self.DRAGGING:
                            self.state = self.NONE
                        elif self.state == self.DRAWCALIB:
                            pos = pygame.mouse.get_pos()
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
                            self.state = self.NONE
                            # add line to foreground 'til death
                            line = PGObject(pygame.draw.line, (foreground, (255, 0, 0), lineOrig, pos, 1))
                            self.calibLines.append(line)
                        elif self.state == self.DRAWMEASURE:
                            pos = pygame.mouse.get_pos()
                            distance = math.sqrt( (pos[1]-lineOrig[1])**2 + (pos[0]-lineOrig[0])**2 )
                            self.measuredValues.append(MeasuredValue(distance, distance * self.WORLDSCALE))
                            print('Measured distance: ', distance * self.WORLDSCALE, ' your unit; average: ',
                                self.getMeasuredValuesAverage())

                            self.state = self.NONE
                            # add line to foreground 'til death
                            line = PGObject(pygame.draw.line, (foreground, (0, 0, 255), lineOrig, pos, 1))
                            self.measureLines.append(line)
                elif not self.state == self.DRAGGING and event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
                    pygame.mouse.get_rel()  # init the relative mouse movement
                    if DRAWCALIB_KEY:
                        lineOrig = pygame.mouse.get_pos()
                        lineOrig[0] += XOFFSET
                        lineOrig[1] += YOFFSET
                        self.state = self.DRAWCALIB
                    elif DRAWMEASURE_KEY:
                        lineOrig = pygame.mouse.get_pos()
                        lineOrig[0] += XOFFSET
                        lineOrig[1] += YOFFSET
                        self.state = self.DRAWMEASURE
                    elif not self.scale:
                        self.state = self.DRAGGING
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == self.DRAGGING:
                        xr, yr = pygame.mouse.get_rel()
                        XOFFSET += xr
                        YOFFSET += yr
                    elif self.state == self.DRAWCALIB:
                        # temporary line
                        foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                        pygame.draw.line(foreground, (255, 0, 0), lineOrig, pygame.mouse.get_pos(), 1)
                    elif self.state == self.DRAWMEASURE:
                        # temporary line
                        foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                        pygame.draw.line(foreground, (0, 0, 255), lineOrig, pygame.mouse.get_pos(), 1)
                elif event.type==pygame.VIDEORESIZE:
                    self.screen=pygame.display.set_mode(event.dict['size'], HWSURFACE|DOUBLEBUF|RESIZABLE)
                    self.screen.convert()
                    foreground = pygame.surface.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
                    foreground.convert()
                    foreground = foreground.convert_alpha() # faster blitting with transparent color
                    # calibration is no longer valid:
                    self.deleteCalibration()

            ### video diplay
            # to get fastest possible framerate & no flicker (near) all updating should be
            # made here
            if self.cam.query_image():
                img = self.cam.get_image()

                if self.scale:
                    snapshot = pygame.transform.scale(img, (self.screen.get_width(), self.screen.get_height()))
                    snapshot.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                    uRect = self.screen.blit(snapshot, (0, 0))
                else:
                    img.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                    uRect = self.screen.blit(img, (XOFFSET,YOFFSET))
                pygame.display.update(uRect)

                # draw foreground with all objects, as fast as camera framerate
                if not self.state == self.DRAWCALIB and not self.state == self.DRAWMEASURE:
                    foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                    for o in self.calibLines:
                        o.drawFunction(*o.parameters)
                    for o in self.measureLines:
                        o.drawFunction(*o.parameters)

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
        sum = 0
        for m in self.measuredValues:
            m.result = m.pixels * self.WORLDSCALE
            sum += m.result
            print('New distance: ', m.result)

        if len(self.measuredValues) > 0:
            print('New average distance:', sum / len(self.measuredValues))


    def updateCalibration(self):
        sum = 0
        for c in self.calibValues:
            if c.pixels > 0:
                sum += c.worlddim / c.pixels

        if sum > 0:
            self.WORLDSCALE = sum / len(self.calibValues)
        else:
            self.WORLDSCALE = 1.0
        print('New scaling: ', self.WORLDSCALE, ' your unit/pixels')

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
    argparser = argparse.ArgumentParser(description='''Display camera video with pygame (>= 1.92).
    Left mouse button + mouse motion drags video.
    Right mouse button takes screenshots.
    CTRL + left mouse button + mouse motion draws calibration line.
    SHIFT + left mouse button draws measuring line (not implemented yet).
    DEL deletes measured values.
    CTRL + DEL deletes calibration (including measured values).
    ESC exits.

    Please start this program from command line!''')
    argparser.add_argument('-l', '--list', action='store_true', help='Print avaiable video devices')
    argparser.add_argument('-s', '--scale', action='store_true', help='Scale video, otherwise it is displayed 1:1 and may be dragged with the mouse')
    argparser.add_argument('device', nargs = '?', default='/dev/video0', help='Name of the camera device')
    argparser.add_argument('width', nargs = '?', type=int, default=640, help='Width of view')
    argparser.add_argument('height', nargs = '?', type=int, default=480, help='Height of view')

    return argparser


def main(_args):
    global SCALE, DEVICE
    argparser = makeParser()
    args = argparser.parse_args(_args)

    if args.list:
        printVideoDevices()
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
    pygame.display.set_caption(DEVICE)

    loop = PGLoop(cam, fps, screen, clock, args.scale)
    loop()

    pygame.quit()



if __name__ == '__main__':
    main(sys.argv[1:])
