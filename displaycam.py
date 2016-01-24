# Captures and displays video images
from __future__ import print_function

###################################################################
# TODO:
#       - flags for vertical mirror, horizontal mirror
#       - split screen to display last/loaded still image side by side with video
#       - distance measuring tool       IN PROGRESS
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
DRAW = False
CTRL = False

# scale or 1:1
SCALE = False

# scale factor for world
WORLDSCALE = 1.0


# just make args.device global
DEVICE = ''

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

    cam.start()

    return cam


def initPygame(_windowSize=(640, 480)):
    pygame.init()

    # get display resolution and adjust screen size
    vidinfo = pygame.display.Info()
    w = min(vidinfo.current_w, _windowSize[0])
    h = min(vidinfo.current_h, _windowSize[1])

    screen = pygame.display.set_mode((w, h), HWSURFACE|DOUBLEBUF|RESIZABLE)
    snapshot = pygame.surface.Surface((w, h), 0, screen)
    clock = pygame.time.Clock()
    return screen, snapshot, clock


def loop(_cam, _fps, _screen, _snapshot, _clock):
    global XOFFSET, YOFFSET, DRAW, CTRL, WORLDSCALE
    done = False
    imgTicker = 1
    dragging = False
    foreground = pygame.surface.Surface((_screen.get_width(), _screen.get_height()))
    foreground.convert()        # for faster blitting
    foreground = foreground.convert_alpha() # faster blitting with transparent color

    while not done:
        ### event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done = True
                elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                    CTRL = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                    CTRL = False
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
                        #print('Dragging stopped')
                    if DRAW:
                        pos = pygame.mouse.get_pos()
                        WORLDSCALE = math.sqrt( (pos[1]-lineOrig[1])**2 + (pos[0]-lineOrig[0])**2 )
                        print('pixels: ', WORLDSCALE)
                        DRAW = False
                        #print('Drawing stopped')

            elif not dragging and event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
                pygame.mouse.get_rel()  # init the relative mouse movement
                if CTRL:
                    lineOrig = pygame.mouse.get_pos()
                    DRAW = True
                    #print('Drawing started')
                elif not SCALE:
                    dragging = True
                    #print('Dragging startet')
            elif event.type == pygame.MOUSEMOTION:
                if not SCALE and dragging:
                    xr, yr = pygame.mouse.get_rel()
                    XOFFSET += xr
                    YOFFSET += yr
                elif DRAW:
                    foreground.fill((0,0,0,0))    # erase foreground & make it transparent
                    pygame.draw.line(foreground, (255, 0, 0), lineOrig, pygame.mouse.get_pos(), 1)
            elif event.type==pygame.VIDEORESIZE:
                _screen=pygame.display.set_mode(event.dict['size'], HWSURFACE|DOUBLEBUF|RESIZABLE)
                _screen.convert()
                foreground = pygame.surface((_screen.get_width(), _screen.get_height()), pygame.SRCALPHA)
                foreground.convert()
                foreground = foreground.convert_alpha() # faster blitting with transparent color

        ### video diplay
        if _cam.query_image():
            img = _cam.get_image()

            if SCALE:
                _snapshot = pygame.transform.scale(img, (_screen.get_width(), _screen.get_height()))
                _snapshot.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                uRect = _screen.blit(_snapshot, (0, 0))
            else:
                img.blit(foreground, (0, 0), special_flags=(pygame.BLEND_RGBA_ADD))
                uRect = _screen.blit(img, (XOFFSET,YOFFSET))
            pygame.display.update(uRect)

            # does not work:
            #pygame.display.set_caption(DEVICE + 'with frame rate: {:0.2f} fps'.format(_clock.get_fps()))

    pygame.quit()
    sys.exit()


def makeParser():
    argparser = argparse.ArgumentParser(description='Display camera video with pygame (>= 1.92)')
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

    screen, snapshot, clock = initPygame(cam.get_size())
    print('Using camera', args.device)
    print('Using camera resolution', cam.get_size())
    print('Using initial screen size (%d, %d)'%(screen.get_width(), screen.get_height()))
    if SCALE:
        print('Scaling video to screen size')

    DEVICE = args.device
    pygame.display.set_caption(DEVICE)

    loop(cam, fps, screen, snapshot, clock)
    pygame.quit()



if __name__ == '__main__':
    main(sys.argv[1:])
