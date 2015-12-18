# Captures and displays video images


###################################################################
# TODO: use the pygame.camera module instead of VideoCapture!!!!!!!
###################################################################

import pygame
from VideoCapture import Device



def initCam(_devnum=0, _res=(640, 480)):
    '''Wants the index of the wanted cam. Returns the device object and the resolution (w,h)'''
    cam = Device(devnum=_devnum)

    if cam is None:
        raise Exception('Cannot connect to camera. Maybe in use by other program?')

    try:
        cam.setResolution(*_res)
    except Exception:
        print 'Warning: cannot set resolution.'

    # capture 1 frame to determin resolution
    img = cam.getImage()
    print 'Camera "' + cam.getDisplayName() + '" resolution:', str(img.size)
    return cam, img.size



def initPygame(_windowSize=(640, 480)):
    pygame.init()
    screen = pygame.display.set_mode(_windowSize)
    clock = pygame.time.Clock()
    return screen, clock



def loop(_cam, _fps, _screen, _clock):
    done = False
    imgTicker = 1
    while not done:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.MOUSEBUTTONUP:    # mouse click
                snapName = 'snapshot_' + str(imgTicker) + '.png'
                _cam.saveSnapshot(snapName)
                print 'Saved snapshot as', snapName
                imgTicker += 1

        img = _cam.getBuffer()  # returns tuple (raw data string, width, height). undocumented.
        size = img[-2:]
        img = img[0]

        #screen.blit(pygame.image.frombuffer(img, size, 'RGB'), (0, 0)) # upside down
        screen.blit(pygame.image.fromstring(img, size, 'RGB', True), (0, 0)) # flip
        pygame.display.flip()
        _clock.tick(_fps)



def usage():
    print '''usage: displaycam [-h] [devidx] [width] [height]
    -h              prints this message and exits
    devidx          index of the wanted cam
    width           video resolution width
    height          video resolution height
    If you provide the video width you must provide the height, too.
    Setting the video resolution may not work.'''


if __name__ == '__main__':
    import sys

    devnum = None
    W = None
    H = None

    if len(sys.argv) > 1:
        if sys.argv[1] == '-h':
            usage()
            exit()
        else:
            try:
                devnum = int(sys.argv[1])
            except Exception, e:
                usage()
                print str(e)
                exit()
        if len(sys.argv) == 4:
            W = int(sys.argv[2])
            H = int(sys.argv[3])
        elif len(sys.argv) != 2:
            usage()
            exit()

    if devnum:
        if W:
            cam, res = initCam(devnum, (W, H))
        else:
            cam, res = initCam(devnum)
    else:
        cam, res = initCam()
    fps = 30
    screen, clock = initPygame(res)
    loop(cam, fps, screen, clock)
    pygame.quit()
