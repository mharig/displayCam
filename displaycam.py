# Captures and displays video images
from __future__ import print_function, division, absolute_import

###################################################################
# TODO:
#       - make OO       IN PROGRESS
#       - flags for vertical mirror, horizontal mirror
#       - split screen to display last/loaded still image side by side with video
#       - distance measuring tool       IN PROGRESS
#               - text input & output, allow more calibration measurement points
#               - test if a calibration is valid after resize of main window when scaling
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

# current offset of the video
XOFFSET = 0
YOFFSET = 0

# dragging or drawing line
DRAWCALIB = False
DRAWCALIB_KEY = False
DRAWMEASURE = False
DRAWMEASURE_KEY = False

# scale or 1:1
SCALE = False

# scale factor for world
WORLDSCALE = 1.0


# just make args.device global
DEVICE = ''


# objects that are drawn to foreground, like lines and text
PGObject = namedtuple('PGobject', ('drawFunction', 'parameters'))


# class PGLoop(object):
#   enum state = [DRAGGING, DRAWCALIB, DRAWMEASURE, NONE]
#   def __init__(self, _cam, _fps, _screen, _clock, _scale):
#       self.state = NONE
#       pass
#   def __call__(self):
#              # loop function goes here


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


def loop(_cam, _fps, _screen, _clock):
    global XOFFSET, YOFFSET, DRAWCALIB, DRAWCALIB_KEY, DRAWMEASURE, DRAWMEASURE_KEY, WORLDSCALE
    done = False
    imgTicker = 1
    dragging = False

    # video image
    snapshot = pygame.surface.Surface((_screen.get_width(), _screen.get_height()), 0, _screen)

    # lines & text
    foreground = pygame.surface.Surface((_screen.get_width(), _screen.get_height()))
    foreground.convert()        # for faster blitting
    foreground = foreground.convert_alpha() # faster blitting with transparent color

    # list of PGobjects in foreground
    fgObjects = []

    # list of measured units for averaging
    measuredValues = []

    while not done:
        ### event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done = True
                elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                    DRAWCALIB_KEY = True
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    DRAWMEASURE_KEY = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                    DRAWCALIB_KEY = False
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    DRAWMEASURE_KEY = False
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == RIGHT:    # right mouse button click
                    img = _cam.get_image()

                    snapName = 'snapshot_' + str(imgTicker) + '.png'
                    while op.exists(snapName):
                        imgTicker += 1
                        snapName = 'snapshot_' + str(imgTicker) + '.png'
                    pygame.image.save(img, snapName)
                    print('Saved snapshot as', snapName)
                    imgTicker += 1
                elif event.button == LEFT:
                    if dragging:
                        dragging = False
                    elif DRAWCALIB:
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

                        WORLDSCALE = worlddim / distance
                        print('Scaling: ', WORLDSCALE, ' your unit/pixels')
                        DRAWCALIB = False
                        # add line to foreground 'til death'
                        line = PGObject(pygame.draw.line, (foreground, (255, 0, 0), lineOrig, pos, 1))
                        fgObjects.append(line)
                    elif DRAWMEASURE:
                        pos = pygame.mouse.get_pos()
                        distance = math.sqrt( (pos[1]-lineOrig[1])**2 + (pos[0]-lineOrig[0])**2 ) * WORLDSCALE
                        measuredValues.append(distance)
                        print('Measured distance: ', distance, ' your unit; average: ', sum(measuredValues)/len(measuredValues))
                        # add line to foreground 'til death'
                        line = PGObject(pygame.draw.line, (foreground, (0, 0, 255), lineOrig, pos, 1))
                        fgObjects.append(line)
                        DRAWMEASURE = False
            elif not dragging and event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
                pygame.mouse.get_rel()  # init the relative mouse movement
                if DRAWCALIB_KEY:
                    fgObjects = []          # delete all lines
                    measuredValues = []     # delete all measured values
                    lineOrig = pygame.mouse.get_pos()
                    DRAWCALIB = True
                elif DRAWMEASURE_KEY:
                    lineOrig = pygame.mouse.get_pos()
                    DRAWMEASURE = True
                elif not SCALE:
                    dragging = True
            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    xr, yr = pygame.mouse.get_rel()
                    XOFFSET += xr
                    YOFFSET += yr
                elif DRAWCALIB:
                    # temporary line
                    foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                    pygame.draw.line(foreground, (255, 0, 0), lineOrig, pygame.mouse.get_pos(), 1)
                elif DRAWMEASURE:
                    # temporary line
                    foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                    pygame.draw.line(foreground, (0, 0, 255), lineOrig, pygame.mouse.get_pos(), 1)
            elif event.type==pygame.VIDEORESIZE:
                _screen=pygame.display.set_mode(event.dict['size'], HWSURFACE|DOUBLEBUF|RESIZABLE)
                _screen.convert()
                foreground = pygame.surface((_screen.get_width(), _screen.get_height()), pygame.SRCALPHA)
                foreground.convert()
                foreground = foreground.convert_alpha() # faster blitting with transparent color

        ### video diplay
        # to get fastest possible framerate & no flicker (near) all updating should be
        # made here
        if _cam.query_image():
            img = _cam.get_image()

            if SCALE:
                snapshot = pygame.transform.scale(img, (_screen.get_width(), _screen.get_height()))
                snapshot.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                uRect = _screen.blit(snapshot, (0, 0))
            else:
                img.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                uRect = _screen.blit(img, (XOFFSET,YOFFSET))
            pygame.display.update(uRect)

            # draw foreground with all objects, as fast as camera framerate
            if not DRAWCALIB and not DRAWMEASURE:
                foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                for o in fgObjects:
                    o.drawFunction(*o.parameters)

            # does not work:
            #pygame.display.set_caption(DEVICE + 'with frame rate: {:0.2f} fps'.format(_clock.get_fps()))

    pygame.quit()
    sys.exit()


def makeParser():
    argparser = argparse.ArgumentParser(description='''Display camera video with pygame (>= 1.92).
    Left mouse button + mouse motion drags video.
    Right mouse button takes screenshots.
    DRAWCALIB_KEY + left mouse button + mouse motion draws calibration line.
    DRAWMEASURE_KEY + left mouse button draws measuring line (not implemented yet).
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

    if args.scale:
        SCALE = True

    cam = initCam(args.device, (args.width, args.height))

    fps = 30

    screen, clock = initPygame(cam.get_size())
    print('Using camera', args.device)
    print('Using camera resolution', cam.get_size())
    print('Using initial screen size (%d, %d)'%(screen.get_width(), screen.get_height()))
    if SCALE:
        print('Scaling video to screen size')

    DEVICE = args.device
    pygame.display.set_caption(DEVICE)

    loop(cam, fps, screen, clock)
    pygame.quit()



if __name__ == '__main__':
    main(sys.argv[1:])
