# Face Animation API
```bash
blender -y Sophia.blend -P autostart.py
xterm -geometry 131x6+450+905 -title "..." -ls /bin/csh
# in the xterm terminal type:
python speak.py
```


# About
The code is designed for Blender 2.71, but it has been tested to work with Blender 2.78 too. Currently, autostart.py runs a socket server on the blender animation, which can be used to trigger gestures remotely. A separate script called __speak.py__ sends UDP packets to the socket server to make the model speak it's own code. For full effect, start an xterm with csh shell to print out the actual spoken text.


# Design

![UML Diagram](docs/evaEmoDesign.png)

* The ROS node listens to and acts on ROS messages.  It uses the
  abstract base class `rigAPI` to communicate with blender.
* Animation messages are queued with the `CommandSource.py` module.
* The `CommandListener` listens to `CommandSource` messages; these
  are `'rigAPI` messages.
* The `command.py` module implements the `rigAPI`
* The `AnimationManager` keeps track of of Eva's internal state.
* The `Actuators` are responsible individual actions of Eva such as
  breathing, blinking and eye movement.

All animation sequences and 3D data are stored in the Blender file.

### Copyright 
Copyright (c) 2014,2015,2016 Hanson Robotics
Copyright (c) 2014,2015 Mike Pan
