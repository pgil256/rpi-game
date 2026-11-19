#!/usr/bin/python3

import random
import os

import pygame

from pygame.locals import *

from frogger import *


#ACTORS
class Rectangle:

	def __init__(self, x, y, w, h):
		self.x = x
		self.y = y
		self.w = w
		self.h = h

	def intersects(self, other):
		left = self.x
		top = self.y
		right = self.x + self.w
		bottom = self.y + self.h

		oleft = other.x
		otop = other.y
		oright = other.x + other.w
		obottom = other.y + other.h

		return not (left >= oright or right <= oleft or top >= obottom or bottom <= otop)


class Lane(Rectangle):

	def __init__(self, y, c=None, n=0, l=0, spc=0, spd=0):
		super(Lane, self).__init__(0, y * g_vars['grid'], g_vars['width'], g_vars['grid'])
		self.type = t
		self.color = c
		self.obstacles = []
		offset = random.uniform(0, 200)
		if self.type == 'car':
			o_color = (128, 128, 128)
		if self.type == 'log':
			o_color = (185, 122, 87)
		for i in range(n):
			self.obstacles.append(Obstacle(offset + spc * i, y * g_vars['grid'], l * g_vars['grid'], g_vars['grid'], spd, o_color))


class Frog(Rectangle):

	def __init__(self, x, y, w):
		super(Frog, self).__init__(x, y, w, w)
		self.x0 = x
		self.y0 = y
		self.color = (34, 177, 76)
		self.attached = None
		# Load weasel.png image for player
		script_dir = os.path.dirname(os.path.abspath(__file__))
		media_dir = os.path.join(script_dir, '..', '..', 'media')
		weasel_path = os.path.join(media_dir, 'weasel.png')
		try:
			self.image = pygame.image.load(weasel_path).convert_alpha()
			self.image = pygame.transform.scale(self.image, (int(w), int(w)))
		except:
			self.image = None

	def reset(self):
		self.x = self.x0
		self.y = self.y0
		self.attach(None)

	def move(self, xdir, ydir):
		self.x += xdir * g_vars['grid']
		self.y += ydir * g_vars['grid']

	def attach(self, obstacle):	
		self.attached = obstacle

	def update(self):
		if self.attached is not None:
			self.x += self.attached.speed

		if self.x + self.w > g_vars['width']:
			self.x = g_vars['width'] - self.w
		
		if self.x < 0:
			self.x = 0
		if self.y + self.h > g_vars['width']:
			self.y = g_vars['width'] - self.w
		if self.y < 0:
			self.y = 0

	def draw(self):
		rect = Rect( [self.x, self.y], [self.w, self.h] )
		if self.image:
			g_vars['window'].blit(self.image, (self.x, self.y))
		else:
			pygame.draw.rect( g_vars['window'], self.color, rect )


class Obstacle(Rectangle):

	def __init__(self, x, y, w, h, s, c):
		super(Obstacle, self).__init__(x, y, w, h)
		self.color = c
		self.speed = s
		self.is_car = True  # Will be set properly by Lane
		# Load soupcan_new.png for cars and boats (with translucency)
		# Preserve aspect ratio to avoid distortion
		script_dir = os.path.dirname(os.path.abspath(__file__))
		media_dir = os.path.join(script_dir, '..', '..', 'media')
		soupcan_path = os.path.join(media_dir, 'soupcan_new.png')
		try:
			self.soupcan_img = pygame.image.load(soupcan_path).convert_alpha()
			# Scale preserving aspect ratio
			orig_w, orig_h = self.soupcan_img.get_size()
			target_size = int(g_vars['grid'])
			scale = min(target_size / orig_w, target_size / orig_h)
			new_w, new_h = int(orig_w * scale), int(orig_h * scale)
			self.soupcan_img = pygame.transform.scale(self.soupcan_img, (new_w, new_h))
			# Apply translucency to match other game sprites
			self.soupcan_img.set_alpha(200)
		except:
			self.soupcan_img = None

	def update(self):
		self.x += self.speed
		if self.speed > 0 and self.x > g_vars['width'] + g_vars['grid']:
			self.x = -self.w
		elif self.speed < 0 and self.x < -self.w:
			self.x = g_vars['width']

	def draw(self):
		# Draw cars and boats using soupcan_new.png
		if self.soupcan_img:
			segment_width = g_vars['grid']
			num_segments = max(1, int(self.w / segment_width))
			for i in range(num_segments):
				seg_x = self.x + i * segment_width
				g_vars['window'].blit(self.soupcan_img, (seg_x, self.y))
		else:
			pygame.draw.rect(g_vars['window'], self.color, Rect([self.x, self.y], [self.w, self.h]))


class Lane(Rectangle):

	def __init__(self, y, t='safety', c=None, n=0, l=0, spc=0, spd=0):
		super(Lane, self).__init__(0, y * g_vars['grid'], g_vars['width'], g_vars['grid'])
		self.type = t
		self.color = c
		self.obstacles = []
		offset = 0#random.uniform(0, 200)
		if self.type == 'car':
			o_color = (128, 128, 128)
		if self.type == 'log':
			o_color = (185, 122, 87)
		for i in range(n):
			obs = Obstacle(offset + spc * i, y * g_vars['grid'], l * g_vars['grid'], g_vars['grid'], spd, o_color)
			obs.is_car = (self.type == 'car')  # Only cars use ferret palette
			self.obstacles.append(obs)

	def check(self, frog):
		checked = False
		attached = False
		frog.attach(None)
		for obstacle in self.obstacles:
			if frog.intersects(obstacle):
				if self.type == 'car':
					frog.reset()
					checked = True
				if self.type == 'log':
					attached = True
					frog.attach(obstacle)
		if not attached and self.type == 'log':
			frog.reset()
			checked = True
		return checked

	def update(self):
		for obstacle in self.obstacles:
			obstacle.update()

	def draw(self):
		if self.color is not None:
			pygame.draw.rect( g_vars['window'], self.color, Rect( [self.x, self.y], [self.w, self.h] ) )
		for obstacle in self.obstacles:
			obstacle.draw()


#SCORE
class Score:

	def __init__(self):
		self.score = 0
		self.high_score = 0
		self.high_lane = 1
		self.lives = 3

	def update(self, points):
		self.score += points
		if self.score > self.high_score:
			self.high_score = self.score

	def reset(self):
		self.score = 0
		self.high_lane = 1
		self.lives = 3
		