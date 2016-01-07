# Captures and displays video images
from __future__ import print_function

###################################################################
# TODO:
#       - display unscaled (with offsets), move offsets with arrow keys
#       - make CTRL-C exit the program
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

import pygame
import pygame.camera as camera
from pygame.locals import HWSURFACE,DOUBLEBUF,RESIZABLE

# define the mouse "buttons"
(   LEFT,
    MIDDLE,
    RIGHT,
    WHEEL_UP,
    WHEEL_DOWN) = range(1,6)

# current offset of the images
XOFFSET = 0
YOFFSET = 0

SCALE = False


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
    global XOFFSET, YOFFSET
    done = False
    imgTicker = 1
    dragging = False
    while not done:
        ### event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done = True
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
                elif dragging and event.button == LEFT:
                    dragging = False
                    #XOFFSET = 0
                    #YOFFSET = 0
            elif not SCALE and not dragging and event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT:
                dragging = True
                pygame.mouse.get_rel()  # init the relative mouse movement
            elif not SCALE and dragging and event.type == pygame.MOUSEMOTION:
                xr, yr = pygame.mouse.get_rel()
                XOFFSET += xr
                YOFFSET += yr
            elif event.type==pygame.VIDEORESIZE:
                _screen=pygame.display.set_mode(event.dict['size'],HWSURFACE|DOUBLEBUF|RESIZABLE)

        ### video diplay
        if _cam.query_image():
            img = _cam.get_image()

            if SCALE:
                _snapshot = pygame.transform.scale(img, (_screen.get_width(), _screen.get_height()))
                uRect = _screen.blit(_snapshot, (0, 0))
            else:
                uRect = _screen.blit(img, (XOFFSET,YOFFSET))
            pygame.display.update(uRect)

    pygame.quit()
    sys.exit()


def makeParser():
    argparser = argparse.ArgumentParser(description='Display cam video with pygame (>= 1.92)')
    argparser.add_argument('-l', '--list', action='store_true', help='Print avaiable video devices')
    argparser.add_argument('-s', '--scale', action='store_true', help='Scale video, otherwise it is displayed 1:1 and may be dragged with the mouse')
    argparser.add_argument('device', nargs = '?', default='/dev/video0', help='Name of the camera device')
    argparser.add_argument('width', nargs = '?', type=int, default=640, help='Width of view')
    argparser.add_argument('height', nargs = '?', type=int, default=480, help='Height of view')

    return argparser


def main(_args):
    global SCALE
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
    loop(cam, fps, screen, snapshot, clock)
    pygame.quit()



if __name__ == '__main__':
    main(sys.argv[1:])
