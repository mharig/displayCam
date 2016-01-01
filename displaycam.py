# Captures and displays video images
from __future__ import print_function

###################################################################
# TODO:
#       - display unscaled (with offsets), move offsets with mouse drag & arrow keys
#       - make ESC & CTRL-C exit the program
#       - make possible to use different video & screenshot resolutions
#           (screenshot always in max cam resolution?)
#           current behaviour: screenshot res = vid res
###################################################################

import os.path as op

import pygame
import pygame.camera as camera


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

    screen = pygame.display.set_mode((w, h), 0)
    snapshot = pygame.surface.Surface((w, h), 0, screen)
    clock = pygame.time.Clock()
    return screen, snapshot, clock



def loop(_cam, _fps, _screen, _snapshot, _clock):
    done = False
    imgTicker = 1
    while not done:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.MOUSEBUTTONUP:    # mouse click
                img = _cam.get_image()     # use if cam.query_image(): ....

                snapName = 'snapshot_' + str(imgTicker) + '.png'
                while op.exists(snapName):
                    imgTicker += 1
                    snapName = 'snapshot_' + str(imgTicker) + '.png'
                pygame.image.save(img, snapName)
                print('Saved snapshot as', snapName)
                imgTicker += 1

        if _cam.query_image():
            img = _cam.get_image()
            _snapshot = pygame.transform.scale(img, (_screen.get_width(), _screen.get_height()))
            _screen.blit(_snapshot, (0,0))
            pygame.display.flip()




def usage():
    print('''usage: displaycam [-h] [-l] [camera device] [width] [height]
    -h              prints this message and exits
    -l              lists avaiable device names and exits
    camera device   name of the wanted cam
    width           video resolution width
    height          video resolution height
    If you provide the video width you must provide the height, too.
    Setting the video resolution may not work.''')


if __name__ == '__main__':
    import sys

    W = None
    H = None

    if len(sys.argv) > 1:
        if sys.argv[1] == '-h':
            usage()
            exit()
        if sys.argv[1] == '-l':
            printVideoDevices()
            exit()
        if len(sys.argv) == 4:
            W = int(sys.argv[2])
            H = int(sys.argv[3])
        elif len(sys.argv) != 2:
            usage()
            exit()

        if W:
            cam = initCam(sys.argv[1], (W, H))
        else:
            cam = initCam(sys.argv[1])
            W = 640
            H = 480
    else:
        cam = initCam()
        W = 640
        H = 480

    fps = 30

    screen, snapshot, clock = initPygame(cam.get_size())
    print('Using camera resolution', cam.get_size())
    print('Using display size (%d, %d)'%(screen.get_width(), screen.get_height()))
    loop(cam, fps, screen, snapshot, clock)
    pygame.quit()
