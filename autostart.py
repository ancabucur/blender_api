#
# Autostart the blender animation.
#
# Run this as:
#    blender -y ./Eva269.blend -P ./autostart.py
#
import bpy
# Start Timer
bpy.ops.wm.global_timer()
# Starts Command Listener
bpy.ops.wm.command_listener()
# Starts animation manager
#bpy.ops.wm.animation_playback()


import socket, threading
from rigControl import commands

commands.init()

def thread_update():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('', 12200))

    while True:
        data, address = serverSocket.recvfrom(1024)
        message = data.decode('utf-8')
        if message:
            parts = message.split('\t')
            function = parts[0]
            params = parts[1]
            try:
                #commands.EvaAPI().queueViseme(vis="E")
                #commands.EvaAPI().queueViseme(vis=message.strip())
                getattr(commands.EvaAPI(), function)(params)
            except Exception as e:
                print (str(e))
            

thread = threading.Thread(target=thread_update)
thread.start()
