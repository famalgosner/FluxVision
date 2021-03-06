#!/usr/bin/python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import time
import getpass
import dbus
import os
from os import stat
import pwd
from subprocess import check_output

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
a_pin = 5
b_pin = 6

def discharge():
	GPIO.setup(a_pin, GPIO.IN)
	GPIO.setup(b_pin, GPIO.OUT)
	GPIO.output(b_pin, False)
	time.sleep(0.005)

def charge_time():
	GPIO.setup(b_pin, GPIO.IN)
	GPIO.setup(a_pin, GPIO.OUT)
	count = 0
	GPIO.output(a_pin, True)
	while not GPIO.input(b_pin):
		count = count + 1
	return count

def analog_read():
	discharge()
	return charge_time()

def dbus_setup():
	global dbusIfaceProp
	done, retry = 0,0
	while done==0:
		try:
			#get username of omxplayer process
			omxplayer_pid = check_output(["pgrep","-of","omxplayer"])
			proc_stat_file = os.stat("/proc/%d" % int(omxplayer_pid))
			omxplayer_uid = proc_stat_file.st_uid
			username = pwd.getpwuid(omxplayer_uid)[0]

			#get uid and gid of omxplayer dbus process
			user_id = stat('/tmp/omxplayerdbus.' + username).st_uid
			group_id = stat('/tmp/omxplayerdbus.' + username).st_gid

			#set effective user and group to omxplayer dub process owner
			os.setegid(group_id)
			os.seteuid(user_id)

			#dbus access
			with open('/tmp/omxplayerdbus.' + username, 'r+') as f:
				omxplayerdbus = f.read().strip()
			bus = dbus.bus.BusConnection(omxplayerdbus)
			object = bus.get_object('org.mpris.MediaPlayer2.omxplayer','/org/mpris/MediaPlayer2', introspect=False)
			dbusIfaceProp = dbus.Interface(object,'org.freedesktop.DBus.Properties')
			done=1

			#return uid and gid to root
			os.setegid(0)
			os.seteuid(0)
		except Exception,e:
			if retry >= 300:
				print str(e)
				raise SystemExit
			retry+=1
			time.sleep(0.1)

#main
try:
	while True:
		raw_num = analog_read()
		#adapt raw readings so they are between 0 and 1
		#with a 10K potentiometer, the raw numbers are approximately between 50 (low) and 560 (high)
		vol = (raw_num - 50)/510.0
		if vol > 1:
			vol = 1.0
		if vol < 0.01:
			vol = 0.0
		try:
			dbusIfaceProp.Volume(dbus.Double(vol))
		except:
			dbus_setup()
		time.sleep(0.05)
except KeyboardInterrupt:
	GPIO.cleanup()
