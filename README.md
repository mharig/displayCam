# displayCam
Displays video images using PyGame (>= 1.9). Allows selection of resolution and has a primitive tool to measure distances.

You can mark several distances (CTRL+left mouse button) and the mean value gets saved (in file .dc) and loaded on next start.
When you mark distances with SHIFT+left mouse button the length is displayed on command line.
So you should start displayCam.py from command line, if you want to use this feature!


usage:
displaycam.py [-l] [-s] [-m] [-v] [-d [DEVICE]] [-w [WIDTH]]
                     [-h [HEIGHT]] [-?]

Display camera video with pygame (>= 1.9). Left mouse button + mouse motion
drags video. Right mouse button takes screenshot, CTRL + right mouse button
saves screenshot with drawn lines. CTRL + left mouse button + mouse motion
draws calibration line. SHIFT + left mouse button + mouse motion draws
measuring line. DEL deletes measured values. CTRL + DEL deletes calibration
(including measured values). g displays/hides grid. ESC exits. Please start
this program from command line!

optional arguments:

  -l, --list            Print avaiable video devices

  -s, --scale           Scale video (default), otherwise it is displayed 1:1 and may be
                        dragged with the mouse.

  -m, --flipHorizontal  Flip video horizontal

  -v, --flipVertical    Flip video vertical

  -d [DEVICE], --device [DEVICE]  Name of the camera device. Default is /dev/video0

  -w [WIDTH], --width [WIDTH]     Width of view

  -h [HEIGHT], --height [HEIGHT]  Height of view

  -?, --help            Print usage information
