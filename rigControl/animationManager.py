# AnimationManager is the primary datastore for the various paramters
# that define the Eva character.

from . import actuators
from .blendedNum import BlendedNum
from .helpers import *

import bpy
import random
import time
import imp
import pdb

debug = True


class AnimationManager():

	def __init__(self):
		print('Starting AnimationManager singleton')

		# Gesture params
		self.gesturesList = []
		self.emotionsList = []
		self.visemesList = []

		# Head and Eye tracking parameters
		self.headTargetLoc = BlendedNum([0,0,0], steps=10, smoothing=10)
		self.eyeTargetLoc = BlendedNum([0,0,0], steps=4, smoothing=2)

		# Autonomous (unconscious) behavior parameters
		self.eyeDartRate = 0.0
		self.eyeWander = 0.0
		self.blinkRate = 0.0
		self.blinkDuration = 0.0
		self.breathRate = 0.0
		self.breathIntensity = 0.0

		# Emotional parameters
		self.swiftness = 1.0
		self.shyness = 1.0
		self.idle = 0.0

		# Internal vars
		self._time = 0
		self.lastTriggered = {}

		# global access
		self.deformObj = bpy.data.objects['deform']
		self.bones = bpy.data.objects['control'].pose.bones

		# Camera hacks. See issue #25 in github.
		# Basic assumptions:
		# 1) blender viewport is about 80cm from me.
		# 2) Eva is just a little heind the viewport.
		# 3) Eva's head is 14cm wide.
		# This means that, with a camera field-of-view of 10 degrees
		# she should just fill the viewport.  That's becasue the half
		# angle is given by  arcsin(7/80) = 0.0876 radians = 5 degrees
		# or equivalently, a whole angle of 10 degrees (0.175 radians).
		# Then with this camera FOV, I have to position the camera at
		# -7 "blender units" to get her face to actually fill the
		# viewport.  So that is what the below does.
		#
		# The part that I don't get is that this means that 7 "blender
		# units" is 80cm (or 1 BU is 11 cm).  Which is ridiculously
		# inconsistent with the code in helpers.by, where 1 BU seems to
		# be about 500cm (5 meters!!). So WTF. Something about the camera
		# units and the BU's is crazy/broken.
		#
		bpy.data.cameras["Camera.001"].angle = 0.175
		bpy.data.objects["Camera.001"].location = [-0.028, -7, 0.96]

		self.availableVisemes = []
		for action in bpy.data.actions:
			if action.name.startswith('VIS-'):
				self.availableVisemes.append(action)

		if debug:
			imp.reload(actuators)


	def keepAlive(self):
		'''Called every frame, used to dispatch animation actuators'''
		self.idle += 1.0

		if True:
			actuators.idleCycle(self)

		if True:
			actuators.breathingCycle(self, self.breathRate, self.breathIntensity)

		if True and self.randomFrequency('dart', self.eyeDartRate):
			actuators.eyeSaccades(self, self.eyeWander)

		if True and self.randomFrequency('blink', self.blinkRate):
			actuators.blink(self, self.blinkDuration)

		if True and self.randomFrequency('headTargetLoc', 1):
			actuators.headDrift(self)

		if True and self.randomFrequency('emotionJitter', 20):
			actuators.emotionJitter(self)


	# Show all attributes
	def __repr__(self):
		string = ""
		for attr, value in sorted(self.__dict__.items()):
			if not attr.startswith('_'):
				string += str(attr) + ": " + str(value) + "\n"
		return string


	def newGesture(self, name, repeat = 1, speed=1, magnitude=0.5, priority=1):
		'''Perform a new gesture.'''
		fail = False
		try:
			actionDatablock = bpy.data.actions[name]
		except KeyError:
			fail = True

		if fail:
			raise TypeError('Gesture \"' + name + '\" is not known')
			return

		# Check value for sanity
		checkValue(repeat, 1, 1000)
		checkValue(speed, 0.1, 10)
		checkValue(magnitude, 0, 1)
		checkValue(priority, 0, 1)

		# Create NLA track
		newTrack = self.deformObj.animation_data.nla_tracks.new()
		newTrack.name = name

		# Create strip
		newStrip = newTrack.strips.new(name=name, start=1, action=actionDatablock)
		duration = (newStrip.frame_end - newStrip.frame_start)
		newStrip.blend_type = 'ADD'
		newStrip.use_animated_time = True

		# force blink to play at 1.0 intensity
		if 'blink' in name.lower():
			magnitude = 1

		if magnitude < 1:
			newStrip.use_animated_influence = True
			newStrip.influence = magnitude

		# Create object and add to list
		g = Gesture(name, newTrack, newStrip, duration=duration, speed=speed, \
			 magnitude=magnitude, priority=priority, repeat=repeat)
		self.gesturesList.append(g)


	def _deleteGesture(self, gesture):
		''' internal use only, stops and deletes a gesture'''
		# remove from list
		self.gesturesList.remove(gesture)

		# remove from Blender
		self.deformObj.animation_data.nla_tracks.remove(gesture.trackRef)


	def setEmotion(self, emotionDict):
		'''Set the emotional state of the character.'''
		for emotionName, data in emotionDict.items():
			try:
				control = self.bones['EMO-'+emotionName]
			except KeyError:
				print('Cannot set emotion. No bone with name ', emotionName)
				continue
			else:
				found = False
				for emotion in self.emotionsList:
					if emotionName == emotion.name:
						# update magnitude
						emotion.magnitude.target = data['magnitude']
						emotion.duration = data['duration']
						found = True

				if not found:
					emotion = Emotion(emotionName, magnitude = BlendedNum(data['magnitude'], steps = 10, smoothing = 10), duration = data['duration'])
					self.emotionsList.append(emotion)


	def newViseme(self, vis, duration=0.5, rampInRatio=0.1, rampOutRatio=0.8, startTime=0):
		'''Perform a new viseme'''
		action = None
		for viseme in self.availableVisemes:
			if vis in viseme.name:
				action = viseme
				break
			
		if not action:
			print('No Action mactching viseme: ', vis)
			return False

		# Check value for sanity
		checkValue(duration, 0, 10)
		checkValue(rampInRatio, 0, 0.9)
		checkValue(rampOutRatio, 0, 0.9)
		checkValue(rampInRatio+rampOutRatio, 0, 1.0)

		# Create NLA track
		newTrack = self.deformObj.animation_data.nla_tracks.new()
		newTrack.name = action.name

		# Create strip
		newStrip = newTrack.strips.new(name=action.name, start=1, action=action)
		newStrip.blend_type = 'ADD'
		newStrip.use_animated_influence = True
		newStrip.influence = 0

		# Create object and add to list
		v = Viseme(action.name, newTrack, newStrip, duration, rampInRatio, rampOutRatio, startTime)
		self.visemesList.append(v)

		return True

	
	def _deleteViseme(self, viseme):
			''' internal use only, stops and deletes a viseme'''
			# remove from list
			self.visemesList.remove(viseme)

			# remove from Blender
			self.deformObj.animation_data.nla_tracks.remove(viseme.trackRef)


	def coordConvert(self, loc, currbu):
		'''Convert coordinates from the external coord system (meters) to
		blender units.  This also clamps values to prevent completely
		crazy look-at directions from happening.  Returns the look-at
		point, in blender units.
		'''

		# Prevent crazy values, e.g. looking at inside of skull, or
		# lookings straight backwards.
		#
		# Negative y values will cause her neck to do a 'Linda Blair'
		# in the Exorcist.
		if loc[1] < 0.0:
			loc[1] = 0.0

		# The look-at target must be at least 10 centimeters away.
		# This is an error condition that should never happen, but
		# just in case it does, we don't want the rig to go berzerk.
		# (Right now, the head-drift becomes very large if this
		# distance is under 15 centimeters.)
		dist = computeDistance(loc, [0,0,0])
		mindist = 10.0
		if dist < mindist :
			if dist < 1.0:
				# If totally crazy, look straight ahead.
				# Should probably animate some puzzled wtf expression,
				# just in case this happens (and it never should ...)
				loc = [0.0, 30.0, 0.0]
			else:
				# Else try to look at approximately correct location
				dist = mindist / dist
				loc = [loc[0]*dist, loc[1]*dist, loc[2]*dist]

		# Convert from centimeters to 'blender-units'
		locBU = CM2BU(loc)

		# Adjust for world offset. Magic number incoming...
		locBU[1] -= (1.2)

		# Compute distance from previous eye position
		distance = computeDistance(locBU, currbu)

		# Behavior: if the point being looked at changed
		# significantly, then microlblink.
		if distance > 0.15:
			if self.randomFrequency('blink', 20):
				self.newGesture('GST-blink-micro')

		return locBU


	def setFaceTarget(self, loc):
		'''Set the target used by eye and face tracking.'''

		locBU = self.coordConvert(loc, self.eyeTargetLoc.current)

		self.headTargetLoc.target = locBU
		self.eyeTargetLoc.target = locBU


	def setGazeTarget(self, loc):
		'''Set the target used for eye tracking only.'''

		locBU = self.coordConvert(loc, self.eyeTargetLoc.current)
		self.eyeTargetLoc.target = locBU

	def setViseme(self):
		pass


	def terminate(self):
		'''House-keeping at the end of the run'''
		# remove all leftover gestures
		for gesture in self.gesturesList:
			self.deformObj.animation_data.nla_tracks.remove(gesture.trackRef)

		self.gesturesList = []

		# reset pose
		bpy.context.scene.objects.active = self.deformObj
		try:
			bpy.ops.pose.transforms_clear()
		except:
			bpy.ops.object.posemode_toggle()
			bpy.ops.pose.transforms_clear()


	def randomFrequency(self, name, hz):
		'''Returns a random true/false based on a hertz value as input'''
		try:
			oldTime = self.lastTriggered[name]
		except KeyError:
			self.lastTriggered[name] = time.time()
			return True

		elapsedTime = time.time() - oldTime
		hz = max(hz, 0.0001)  # prevents div by 0
		if elapsedTime > random.gauss(1.0/hz, 0.2/hz):  # sigma is hard coded to 1/5 the mu
			self.lastTriggered[name] = time.time()
			return True
		else:
			return False


class Emotion():
	'''Represents an emotion'''
	def __init__(self, name, magnitude, duration):
		self.name = name
		self.magnitude = magnitude
		self.duration = duration
		self.priority = 0


class Gesture():
	'''Represents a blender actions'''
	def __init__(self, name, track, strip, duration, speed, magnitude, priority, repeat):
		self.name = name
		self.duration = duration
		self.magnitude = magnitude
		self.speed = speed
		self.priority = priority
		self.repeat = repeat

		self.trackRef = track
		self.stripRef = strip


class Viseme():
	'''Represents a Viseme'''
	def __init__(self, vis, track, strip, duration, rampInRatio, rampOutRatio, startTime):
		self.vis = vis
		self.trackRef = track
		self.stripRef = strip
		self.duration = duration  		# duration of animation in seconds
		self.time = 0 - startTime 		# -time is scheduled for the future (seconds)
										# 0 is happening right away
										# +time is animation in progress (seconds)
		self.magnitude = BlendedNum(0, steps=2, smoothing=4) 	# normalized amplitude
		self.rampInRatio = rampInRatio 		# percentage of time spent blending in
		self.rampOutRatio = rampOutRatio 	# percentage of time spent blending out


def init():
	'''Create AnimationManager singleton and make it available for global access'''
	if hasattr(bpy, 'evaAnimationManager'):
		print('Skipping Singleton instantiation')
	else:
		bpy.evaAnimationManager = AnimationManager()
