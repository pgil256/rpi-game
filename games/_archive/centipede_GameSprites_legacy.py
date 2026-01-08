'''
Author: David Feng

  Date: May 29, 2017

  Description: This file contains the Class Sprites for my Centipede Game.

'''

import pygame
import random
import os

# Get media directory path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_media_dir = os.path.join(_script_dir, '..', '..', 'media')


class Player(pygame.sprite.Sprite):
    '''This class defines the sprite for the player.'''
    def __init__(self, screen, killed, level):
        '''This initializer method takes a screen surface, boolean value and 
        level as parameters. It initializes the image and rect attributes, xy 
        vectors for the player, if it has been killed and instance variables to 
        control the animation.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of the screen surface, x,y vectors, 
        # whether or not the player sprite is killed and level
        self.__screen = screen
        self.__dx = 4
        self.__dy = 4
        self.__killed = False
        self.__level = level

        # Instance variables to control the animation
        self.__animate = []
        self.__index = 0

        # Instance variables to control the speed at which the image changes
        self.__last = pygame.time.get_ticks()
        self.__intervals = 80

        # Colour of the sprites change depending on level
        # Loads each death image for the player and the player sprite
        # Use ferret-long-sprite.png for player (long ferret protagonist)
        ferret_path = os.path.join(_media_dir, 'ferret-long-sprite.png')
        try:
            self.image = pygame.image.load(ferret_path).convert_alpha()
            self.image = pygame.transform.scale(self.image, (16, 16))
        except:
            if self.__level == 1:
                self.image = pygame.image.load("Green Sprites/greengun.png")
            elif self.__level == 2:
                self.image = pygame.image.load("Blue Sprites/gun.png")

        if self.__level == 1:
            for num in range(1, 9):
                self.__animate.append(pygame.image.load("Green Sprites/greendeath"+str(num)+".png"))

        elif self.__level == 2:
            for num in range(1, 9):
                self.__animate.append(pygame.image.load("Blue Sprites/death" + str(num) + ".png"))

        # Set rect attributes for the player
        self.rect = self.image.get_rect()
        
        self.rect.centerx = self.__screen.get_width()/2
        self.rect.centery = self.__screen.get_height() - 50
        
    def move_up(self):
        '''This method moves the player sprite up by dy.'''
        self.rect.centery -= self.__dy
    
    def move_down(self):
        '''This method moves the player sprite down by dy.'''
        self.rect.centery += self.__dy
    
    def move_left(self):
        '''This methods moves the player sprite left by dx.'''
        self.rect.centerx -= self.__dx
        
    def move_right(self):
        '''This methods moves the player sprite right by dx.'''
        self.rect.centerx += self.__dx

    def set_killed(self):
        '''This method sets the killed instance variable to True.'''
        self.__killed = True

    def change_level(self):
        '''This method changes the level of the game and the colour of the images'''
        self.__level = 2
        self.__animate = []
        for num in range(1, 9):
            self.__animate.append(pygame.image.load("Blue Sprites/death" + str(num) + ".png"))

    def update(self):
        '''This method will be called automatically to reposition the player 
        sprite on the screen and to switch images for death animation.'''

        now = pygame.time.get_ticks()
        # If statement checks if the player has been killed
        if self.__killed:
            # If statement causes the death images to switch every 0.1 seconds
            if now - self.__last >= self.__intervals:
                self.__last = now
                self.__index += 1
                # If statement kills the sprite when the death animation is finished
                if self.__index >= len(self.__animate):
                    self.__index = 0
                    self.kill()
                    pygame.time.delay(1000)
                self.image = self.__animate[self.__index]

        # top
        if self.rect.top <= (self.__screen.get_height() - 112):
            self.rect.top = self.__screen.get_height() - 112
        # bottom
        if self.rect.bottom >= self.__screen.get_height():
            self.rect.bottom = self.__screen.get_height()
        # left
        if self.rect.left <= 0:
            self.rect.left = 0
        # right
        if self.rect.right >= self.__screen.get_width():
            self.rect.right = self.__screen.get_width()

class Bullet(pygame.sprite.Sprite):
    '''This class defines the sprite for the bullet.'''
    def __init__(self, center, level):
        '''This initializer takes the center of the player sprite and level as
        parameters. It initializes the image and rect attributes and y vector
        for the bullet.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of the player center, y vector
        # and level
        self.__center = center
        self.__dy = -15
        self.__level = level

        # Use soupcan_new.png as projectile instead of default bullet (with translucency)
        # Preserve aspect ratio to avoid distortion
        soupcan_path = os.path.join(_media_dir, 'soupcan_new.png')
        try:
            self.image = pygame.image.load(soupcan_path).convert_alpha()
            # Scale preserving aspect ratio
            orig_w, orig_h = self.image.get_size()
            target_size = 16
            scale = min(target_size / orig_w, target_size / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            self.image = pygame.transform.scale(self.image, (new_w, new_h))
            # Apply translucency to match other game sprites
            self.image.set_alpha(200)
        except:
            # Fallback to original sprites if soupcan_new not found
            if self.__level == 1:
                self.image = pygame.image.load("Green Sprites/greenbullet.png")
            elif self.__level == 2:
                self.image = pygame.image.load("Blue Sprites/bullet.png")

        self.rect = self.image.get_rect()

        self.rect.center = self.__center

    def change_level(self):
        '''This method changes the level instance variable to 2.'''
        self.__level = 2

    def update(self):
        '''This method will be automatically called to reposition the bullet and
        kill it if it goes past the screen.'''

        self.rect.centery += self.__dy
        if self.rect.bottom <= 0:
            self.kill()

class Centipede(pygame.sprite.Sprite):
    '''This class defines the sprite for the Centipede enemy.'''
    def __init__(self, screen, right, number, level):
        '''This initializer takes the screen, a right coordinate, a number and 
        level as parameters. It initializes the image and rect attributes, and 
        creates instance variables for the x vector, point value, and to control 
        animation.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of screen surface, number, right var,
        # if it has reached the bottom and level
        self.__screen = screen
        self.__num = number
        self.__right = right
        self.__reached_bottom = False
        self.__level = level

        # Instance variables to control the animation
        self.__animate_head = []
        self.__animate_body = []
        self.__index = 0

        # Instance variables to control the speed at which the image changes
        self.__last = pygame.time.get_ticks()
        self.__intervals = 50
        
        # Loads each head and body image
        # Colour of the sprites and the speed of the centipede are different
        # depending on level
        # Use soupcan_new.png for centipede segments (with translucency)
        # Preserve aspect ratio to avoid distortion
        soupcan_path = os.path.join(_media_dir, 'soupcan_new.png')
        try:
            soupcan_img = pygame.image.load(soupcan_path).convert_alpha()
            # Scale preserving aspect ratio
            orig_w, orig_h = soupcan_img.get_size()
            target_size = 16
            scale = min(target_size / orig_w, target_size / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            soupcan_img = pygame.transform.scale(soupcan_img, (new_w, new_h))
            # Apply translucency to match other game sprites
            soupcan_img.set_alpha(200)
        except:
            soupcan_img = None

        if self.__level == 1:
            for num in range(1, 9):
                # Use soupcan_new.png for head/body sprites
                if soupcan_img:
                    self.__animate_head.append(soupcan_img.copy())
                    self.__animate_body.append(soupcan_img.copy())
                else:
                    self.__animate_head.append(pygame.image.load("Green Sprites/greenhead"+str(num)+".png"))
                    self.__animate_body.append(pygame.image.load("Green Sprites/greenbody"+str(num)+".png"))
            self.__dx = -2
        elif self.__level == 2:
            for num in range(1, 9):
                if soupcan_img:
                    self.__animate_head.append(soupcan_img.copy())
                    self.__animate_body.append(soupcan_img.copy())
                else:
                    self.__animate_head.append(pygame.image.load("Blue Sprites/head"+str(num)+".png"))
                    self.__animate_body.append(pygame.image.load("Blue Sprites/body"+str(num)+".png"))
            self.__dx = -4

        # Sets the image and point value for the centipede
        # num value of 7 is the head of the centipede
        if self.__num == 7:
            self.__point_value = 100
            self.image = self.__animate_head[0]
        else:
            self.__point_value = 10
            self.image = self.__animate_body[0]

        # Sets the rect attributes for the centipede
        self.rect = self.image.get_rect()
        
        self.rect.right = self.__screen.get_width() - self.__right
        self.rect.top = 64

    def change_movement(self):
        '''This method lowers the sprite by 16 pixels and changes the x direction.'''
        if self.__reached_bottom == False:
            self.rect.top += 16
        else:
            self.rect.top -= 16
        self.__dx = -self.__dx
    
    def change_direction(self):
        '''This methods changes the x direction of the sprite.'''
        self.__dx = -self.__dx
        
    def get_point_value(self):
        '''This method returns the point value of the Centipede.'''
        return self.__point_value

    def update(self):
        '''This method will be called automatically to change the image of the 
        centipede(animation) and reposition the centipede sprite on the screen.'''
        
        now = pygame.time.get_ticks()
        # num value of 7 is the head
        if self.__num == 7:
            # if statement causes the head image to switch every 0.1 seconds
            if now - self.__last >= self.__intervals:
                self.__last = now
                self.__index += 1
                if self.__index >= len(self.__animate_head):
                    self.__index = 0
                self.image = self.__animate_head[self.__index]
        else:
            # if statement causes the body image to switch every 0.1 seconds
            if now - self.__last >= self.__intervals:
                self.__last = now
                self.__index += 1
                if self.__index >= len(self.__animate_body):
                    self.__index = 0
                self.image = self.__animate_body[self.__index]

        self.rect.right += self.__dx

        # If statement checks that if the centipede has not reached the bottom
        if self.__reached_bottom == False:
            # checks whether the sprite has hit the left/right of the screen and 
            # lowers the sprite & changes the x direction
            if self.rect.left <= 0 or self.rect.right >= self.__screen.get_width():
                self.rect.top += 16
                self.__dx = -self.__dx
            elif self.rect.bottom == (self.__screen.get_height() + 16):
                self.__reached_bottom = True
                self.rect.top -= 32
                
        # Changes the boundary of the centipede if it has reached the bottom before
        if self.__reached_bottom:
            if self.rect.left <= 0 or self.rect.right >= self.__screen.get_width():
                self.rect.top -= 16
                self.__dx = -self.__dx
            elif self.rect.top == self.__screen.get_height() - 128:
                self.rect.top += 32
                self.__reached_bottom = False

class Mushroom(pygame.sprite.Sprite):
    '''This class defines the sprites for the Mushroom.'''
    def __init__(self, topleft, level):
        '''This initializer takes a topleft coord and level as parameters. It 
        initializes the image and rect attributes and creates instance variables 
        for hit point, point value and x,y coordinate.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of the hit points, point value, 
        # x,y coord and level
        self.__hit = 4
        self.__point_value = 1
        self.__x = topleft[0]
        self.__y = topleft[1]
        self.__level = level

        self.__phase = []
        
        # Loads each mushroom image
        # Colour of the sprites are different depending on level
        if self.__level == 1:
            for num in range(1, 5):
                self.__phase.append(pygame.image.load("Green Sprites/greenmushroom"+str(num)+".png"))

        elif self.__level == 2:
            for num in range(1, 5):
                self.__phase.append(pygame.image.load("Blue Sprites/mushroom"+str(num)+".png"))

        # Sets the x,y coordinate for the mushroom (rounds to a multiple of 16)
        if self.__x == 0 and self.__y == 0:
            self.__randx = random.randrange(32, 609)
            self.__randy = random.randrange(80, 440)
        else:
            self.__randx = self.__x
            self.__randy = self.__y

        if self.__randx % 16 != 0:
            self.__randx -= self.__randx % 16
        if self.__randy % 16 != 0:
            self.__randy -= self.__randy % 16

        # Sets the image and rect attributes for the mushroom
        self.image = self.__phase[0]
        self.rect = self.image.get_rect()

        self.rect.right = self.__randx
        self.rect.top = self.__randy
        
    def mushroom_hitpoint(self):
        '''This method decreases to hitpoint of the mushroom by 1.'''
        self.__hit -= 1
        
    def mushroom_kill(self, mushroom):
        '''This method changes the the mushroom image based on the hit points or 
        kills the sprite.''' 
        if self.__hit == 3:
            self.image = self.__phase[1]
        elif self.__hit == 2:
            self.image = self.__phase[2]
        elif self.__hit == 1:
            self.image = self.__phase[3]
        else:
            mushroom.kill()
        
    def get_point_value(self):
        '''This method returns the point value of the mushroom.'''
        return self.__point_value
        
    def get_hitpoint(self):
        '''This method gets the amount of hit points left.'''
        return self.__hit

    def change_level(self):
        '''This method changes the colour of sprites.'''
        self.__level = 2
        self.__phase = []
        for num in range(1, 5):
            self.__phase.append(pygame.image.load("Blue Sprites/mushroom" + str(num) + ".png"))

        self.image = self.__phase[0]

class Spider(pygame.sprite.Sprite):
    '''This class defines the sprite for the spider enemy.'''
    def __init__(self, screen, level):
        '''This initializer takes the screen and level as parameters. It 
        initializes the image and rect attributes, and instance variables to 
        control the x,y vector, point value and to control animation.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of screen surface, points, 
        # point value, x,y vector, position and level
        self.__screen = screen
        self.__points = [300, 600, 900]
        self.__point_value = self.__points[random.randrange(0, 3)]
        self.__position = random.randrange(0, 2)
        self.__level = level

        # Instance variables to control the animation
        self.__animate = []
        self.__index = 0

        # Instance variables to control the speed at which the image changes
        self.__last = pygame.time.get_ticks()
        self.__intervals = 80

        # Colour of the sprites and x,y vectors are different depending on level
        # Loads each spider image
        if self.__level == 1:
            for num in range(1, 9):
                self.__animate.append(pygame.image.load("Green Sprites/greenspider"+str(num)+".png"))
            self.__dy = 2
            self.__dx = random.randrange(2, 4)

        elif self.__level == 2:
            for num in range(1, 9):
                self.__animate.append(pygame.image.load("Blue Sprites/spider" + str(num) + ".png"))
            self.__dy = 4
            self.__dx = random.randrange(3, 5)

        # Sets the image and rect attributes for the spider
        self.image = self.__animate[0]
        self.rect = self.image.get_rect()

        # Defines the rect position of the spider and the x vector
        if self.__position == 0:
            self.rect.left = 0
        else:
            self.rect.right = self.__screen.get_width() - 15
            self.__dx = -self.__dx

        self.rect.centery = self.__screen.get_height() - 56

    def get_point_value(self):
        '''This method returns the point value of the spider.'''
        return self.__point_value

    def update(self):
        '''This method will be called automatically to change the image of the 
        spider(animation) and reposition the spider sprite on the screen.'''
        
        now = pygame.time.get_ticks()
        # if statement causes the spider image to switch every 0.1 seconds
        if now - self.__last >= self.__intervals:
            self.__last = now
            self.__index += 1
            if self.__index >= len(self.__animate):
                self.__index = 0
            self.image = self.__animate[self.__index]

        self.rect.centerx += self.__dx
        self.rect.centery += self.__dy

        # Changes the y direction if it goes past the borders
        if self.rect.top <= self.__screen.get_height() - 112 or self.rect.bottom >= self.__screen.get_height():
            self.__dy = -self.__dy

        # Kills the sprite if it goes off the screen
        if self.rect.left <= 0 or self.rect.right >= self.__screen.get_width():
            self.kill()

class Point(pygame.sprite.Sprite):
    '''This class defines the point sprite for the spider.'''
    def __init__(self, point_value, center, level):
        '''The initializer method take a point value, center and level as 
        parameters. It initializes the image and rect attributes for the sprite.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of the point value, center and level
        self.__point_value = point_value
        self.__center = center
        self.__level = level

        # Colour of the sprites are different depending on level
        if self.__level == 1:
            self.__300 = pygame.image.load("Green Sprites/green300.png")
            self.__600 = pygame.image.load("Green Sprites/green600.png")
            self.__900 = pygame.image.load("Green Sprites/green900.png")

        elif self.__level == 2:
            self.__300 = pygame.image.load("Blue Sprites/300.png")
            self.__600 = pygame.image.load("Blue Sprites/600.png")
            self.__900 = pygame.image.load("Blue Sprites/900.png")

        # Instance variables to control the speed at which the image changes
        self.__last = pygame.time.get_ticks()
        self.__timer = 300

        # Sets the image and rect attributes for the sprite
        if self.__point_value == 300:
            self.image = self.__300
        elif self.__point_value == 600:
            self.image = self.__600
        else:
            self.image = self.__900

        self.rect = self.image.get_rect()
        self.rect.center = self.__center

    def update(self):
        '''This method will be called automatically called to kill the sprite in 0.3 seconds.'''
        now = pygame.time.get_ticks()
        # If statement kills the sprite if the sprite has been on the screen for more than 0.3 seconds
        if now - self.__last >= self.__timer:
            self.kill()

class Flea(pygame.sprite.Sprite):
    '''This class defines the sprite for the flea enemy.'''
    def __init__(self, screen):
        '''This initializer method takes a screen surface as a parameter. It 
        initializes the image and rect attributes, and creates instance 
        variables for the point value, y vector and to control animation. '''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of screen surface, point value, 
        # x,y vector and position
        self.__screen = screen
        self.__hit = 2
        self.__point_value = 200
        self.__dy = 2
        self.__position = random.randrange(0, 641)

        # Instance variables to control the animation
        self.__animate = []
        self.__index = 0

        # Loads each flea image
        for num in range(1, 5):
            self.__animate.append(pygame.image.load("Blue Sprites/flea"+str(num)+".png"))

        # Instance variables to control the speed at which the image changes
        self.__last = pygame.time.get_ticks()
        self.__intervals = 80

        # Sets the image and rect attributes for the spider
        self.image = self.__animate[0]
        self.rect = self.image.get_rect()

        if self.__position % 16 != 0:
            self.__position -= self.__position % 16

        self.rect.bottom = 0
        self.rect.right = self.__position

    def get_point_value(self):
        '''This method returns the point value of the flea.'''
        return self.__point_value

    def flea_hit(self):
        '''This method lower the hit point of the flea by 1.'''
        self.__hit -= 1

    def get_hitpoint(self):
        '''This method returns the hit point of the flea.'''
        return self.__hit

    def update(self):
        '''This method will be automatically called to change the image of the 
        flea(animation) and reposition the flea sprite on the screen. '''
        
        now = pygame.time.get_ticks()
        # if statement causes the flea image to switch every 0.08 seconds
        if now - self.__last >= self.__intervals:
            self.__last = now
            self.__index += 1
            if self.__index >= len(self.__animate):
                self.__index = 0
            self.image = self.__animate[self.__index]

        self.rect.bottom += self.__dy

        # Kills the flea sprite if it goes past the screen
        if self.rect.top >= self.__screen.get_height():
            self.kill()

        # Doubles the speed of the flea if it has 1 hit point
        if self.__hit == 1:
            self.__dy = 4

class ScoreKeeper(pygame.sprite.Sprite):
    '''This class defines the sprite for the score.'''
    def __init__(self, screen):
        '''This initializer method takes a screen surface as a parameter. 
        Tt initializes instance variables for the font and the score.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variable to keep track of the font, score, level and colour
        self.__font = pygame.font.Font("ARCADECLASSIC.TTF", 30)
        self.__score = 0
        self.__colour = (255, 0, 0)
        
    def add_score(self, value):
        '''This method adds a certain value to the score.'''
        self.__score += value
        
    def get_score(self):
        '''This method returns the value of the score.'''
        return self.__score

    def change_level(self):
        '''This method changes the colour of the score.'''
        self.__colour = (51, 216, 232)

    def update(self):
        '''This method will be called automatically to change the value of the score.'''
        
        message = "%d" % self.__score
        self.image = self.__font.render(message, 1, self.__colour)
        self.rect = self.image.get_rect()
        self.rect.center = (120, 10)

class Lives(pygame.sprite.Sprite):
    '''This class defines the sprite for the life counter.'''
    def __init__(self, left):
        '''This initializer method takes a left integer as a parameter. 
        It initializes the image and rect attributes for the sprite.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variable to keep track of the left integer
        self.__right = left

        # Sets the image and rect attributes for the life counter
        self.image = pygame.image.load("Green Sprites/greengun.png")
        self.rect = self.image.get_rect()

        self.rect.top = 0
        self.rect.left = self.__right

    def change_level(self):
        '''This method changes the colour of the life sprites.'''
        self.image = pygame.image.load("Blue Sprites/gun.png")

class Highscore(pygame.sprite.Sprite):
    '''This class defines the sprite for the highscore.'''
    def __init__(self):
        '''This initializer method opens the highscore.txt file and gets the 
        all time high score. It initializes the image and rect attributes.'''
        pygame.sprite.Sprite.__init__(self)

        # Instance variables to keep track of the highscore and font
        self.__highscore = 0
        self.__colour = (255, 0, 0)
        self.__font = pygame.font.Font("ARCADECLASSIC.TTF", 30) 

        # Opens the highscore.txt file and gets the highest score
        infile = open("highscore.txt", 'r')
        for num in infile:
            num = int(num)
            if num >= self.__highscore:
                self.__highscore = num
        infile.close()

    def update(self):
        '''This method will be called automatically to change the colour of the 
        high score.'''
        
        # Sets the image and rect attributes for the highscore label
        self.image = self.__font.render(str(self.__highscore), 1, self.__colour)
        self.rect = self.image.get_rect()
        self.rect.center = (320, 10)

    def change_level(self):
        '''This method changes the colour of the highscore label.'''
        self.__colour = (51, 216, 232)