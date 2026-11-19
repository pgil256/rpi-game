'''
Author: David Feng
  
  Date: May 30, 2017
  
  Description: This program is remake of the Atari game, Centipede. 

'''

# I - IMPORT AND INITIALIZE
import pygame, GameSprites
pygame.init()
pygame.mixer.init()

def game():
    '''This function defines the game.'''
    
    # DISPLAY
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Centipede")
    pygame.display.set_icon(pygame.image.load("mushroom_icon.png"))

    # ENTITIES
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((0, 0, 0))
    screen.blit(background, (0, 0))
    
    level = 1

    # Sprites 
    player = GameSprites.Player(screen, False, level)
    scorekeeper = GameSprites.ScoreKeeper(screen)
    highscore = GameSprites.Highscore()

    # Centipede Body
    bodies = []
    right = 0
    for x in range(8):
        body = GameSprites.Centipede(screen, right, x, level)
        bodies.append(body)
        right += 16

    # Mushrooms    
    mushrooms = []
    for x in range(30):
        mushroom = GameSprites.Mushroom((0, 0), 1)
        mushrooms.append(mushroom)

    # Lives
    lives = []
    left = 0
    for x in range(3):
        life = GameSprites.Lives(left)
        lives.append(life)
        left += 16

    bodyGroup = pygame.sprite.Group(bodies)
    mushroomGroup = pygame.sprite.Group(mushrooms)
    flea_mushroomGroup = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    lifeGroup = pygame.sprite.Group(lives)
    spiderGroup = pygame.sprite.Group()
    fleaGroup = pygame.sprite.Group()

    allSprites = pygame.sprite.OrderedUpdates(player, bodyGroup, scorekeeper, \
        highscore, lifeGroup, mushroomGroup, bullets, spiderGroup, fleaGroup)
    
    # "Game Over" Image to display after game loop terminates
    font = pygame.font.Font("ARCADECLASSIC.TTF", 100)
    gameover = font.render("Game Over", 1, (255, 255, 255))
    
    # Background Music
    pygame.mixer.music.load("Sound/background music.mp3")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
    
    # Sound Effect when the player shoots a bullet
    shoot = pygame.mixer.Sound("Sound/270343__littlerobotsoundfactory__shoot-01.wav")
    shoot.set_volume(0.2)    
    
    # Sound Effect when the player dies
    dead = pygame.mixer.Sound("Sound/dead.wav")
    dead.set_volume(0.2)    
    
    # Sound Effect when the player kills an enemy
    killed = pygame.mixer.Sound("Sound/270306__littlerobotsoundfactory__explosion-02.wav")
    killed.set_volume(0.2)

    # Creates a timer event for the spider enemy
    pygame.time.set_timer(pygame.USEREVENT + 1, 4000)
    # Creates a timer event for the flea enemy
    pygame.time.set_timer(pygame.USEREVENT + 2, 8000)
    
    # ASSIGN 
    clock = pygame.time.Clock()
    keepGoing = True
    death = False
    # Hide the mouse pointer
    pygame.mouse.set_visible(False)
 
    # LOOP
    while keepGoing:
     
        # TIME
        clock.tick(60)

        # EVENT HANDLING: 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keepGoing = False
            elif event.type == pygame.USEREVENT+1:
                # Creates a spider and adds it to the sprite groups
                spider = GameSprites.Spider(screen, level)
                spiderGroup.add(spider)
                allSprites.add(spiderGroup)
            elif event.type == pygame.USEREVENT+2:
                # Creates a flea and adds it to the sprite groups if level is 2
                if level == 2:
                    flea = GameSprites.Flea(screen)
                    fleaGroup.add(flea)
                    allSprites.add(fleaGroup)

        # If statement checks if the player has been killed
        if death == False:
            pressed  = pygame.key.get_pressed()
            if pressed[273]:
                player.move_up()
            elif pressed[274]:
                player.move_down()
            elif pressed[275]:
                player.move_right()
            elif pressed[276]:
                player.move_left()
            # Checks if the player pressed the spacebar and no other bullets are on the screen   
            if pressed[pygame.K_SPACE] and len(bullets) <= 0:             
                shoot.play()
                # Creates a bullet and adds it into sprite groups                    
                missile = GameSprites.Bullet(player.rect.center, level)
                bullets.add(missile)
                allSprites.add(bullets)                
          
        # Centipede with Player Collision
        for body in bodyGroup:
            if body.rect.colliderect(player):
                dead.play()
                death = True
                player.set_killed()
        
        # Centipede with Mushroom Collision
        for body in bodyGroup:
            if pygame.sprite.spritecollide(body, mushroomGroup, False):
                body.change_movement()
                if pygame.sprite.spritecollide(body, mushroomGroup, False):
                    body.change_direction()
        
        # Bullet with Centipede Collision
        for bullet in bullets:
            centipede_hit = pygame.sprite.spritecollide(bullet, bodyGroup, True)
            if centipede_hit:
                # Loops through each centipede part in the centipede_hit list
                for centipede in centipede_hit:
                    killed.play()
                    # Creates a mushroom in place of the killed centipede body
                    mushroom = GameSprites.Mushroom(centipede.rect.topleft, level)
                    mushroomGroup.add(mushroom)
                    allSprites.add(mushroomGroup)
                    # Kills the bullet sprite
                    bullet.kill()
                    # Adds the point value of the centipede body to the score
                    scorekeeper.add_score(centipede.get_point_value())
                            
        # Bullet with Mushroom Collision
        for bullet in bullets:
            mushroom_hit = pygame.sprite.spritecollide(bullet, mushroomGroup, False)
            if mushroom_hit:
                # Kills the bullet sprite 
                bullet.kill()
                # Lowers the mushroom hit point by 1 and changes the sprite image 
                mushroom_hit[0].mushroom_hitpoint()
                mushroom_hit[0].mushroom_kill(mushroom_hit[0])
                # Checks if the mushroom is killed
                if mushroom_hit[0].get_hitpoint() == 0:
                    killed.play()
                    scorekeeper.add_score(mushroom_hit[0].get_point_value())

        # Player with Mushroom Collision
        player_mushroom_hit = pygame.sprite.spritecollide(player, mushroomGroup, False)
        if player_mushroom_hit:
            # Player with Mushroom left Collision
            if player.rect.collidepoint(player_mushroom_hit[0].rect.midleft) == True:
                player.rect.right = player_mushroom_hit[0].rect.left 
                
            # Player with Mushroom right Collision    
            if player.rect.collidepoint(player_mushroom_hit[0].rect.midright) == True:
                player.rect.left = player_mushroom_hit[0].rect.right
                
            # Player with Mushroom top Collision    
            if player.rect.collidepoint(player_mushroom_hit[0].rect.midtop) == True:
                player.rect.bottom = player_mushroom_hit[0].rect.top
                
            # Player with Mushroom bot Collision    
            if player.rect.collidepoint(player_mushroom_hit[0].rect.midbottom) == True:
                player.rect.top = player_mushroom_hit[0].rect.bottom
        
        # Player with Spider Collision
        player_spider_hit = pygame.sprite.spritecollide(player, spiderGroup, True)
        if player_spider_hit:
            dead.play()
            death = True
            player.set_killed()
        
        # Bullet with Spider Collision
        for bullet in bullets:
            spider_hit = pygame.sprite.spritecollide(bullet, spiderGroup, True)
            if spider_hit:
                killed.play()
                # Kills the bullet sprite
                bullet.kill()
                # Adds the point value of the spider to the score
                scorekeeper.add_score(spider_hit[0].get_point_value())
                point = GameSprites.Point(spider_hit[0].get_point_value(), spider_hit[0].rect.center, level)
                allSprites.add(point)

        # Player with Flea Collision
        player_flea_hit = pygame.sprite.spritecollide(player, fleaGroup, True)
        if player_spider_hit:
            dead.play()
            death = True
            player.set_killed()

        # Bullet with Flea Collision
        for bullet in bullets:
            flea_hit = pygame.sprite.spritecollide(bullet, fleaGroup, False)
            if flea_hit:
                flea_hit[0].flea_hit()
                # Kills the bullet sprite
                bullet.kill()
                if flea_hit[0].get_hitpoint() == 0:
                    killed.play()
                    flea_hit[0].kill()
                    # Adds the point value of the flea to the score
                    scorekeeper.add_score(flea_hit[0].get_point_value())

        # Creates Mushrooms based on where the flea is except for the last row
        for flea in fleaGroup:
            if flea.rect.bottom % 16 == 0 and not (464 <= flea.rect.bottom <= 480):
                mushroom = GameSprites.Mushroom(flea.rect.bottomleft, 2)
                flea_mushroomGroup.add(mushroom)
                mushroomGroup.add(flea_mushroomGroup)
                allSprites.add(flea_mushroomGroup)

        # Checks if the player is not in any sprite groups
        if player.alive() == False:
            # Player loses a life
            lives[len(lifeGroup)-1].kill()
            
            # Creates a new player sprite
            player = GameSprites.Player(screen, False, level)

            # Remove all enemies
            for body in bodyGroup:
                body.kill()
  
            for spider in spiderGroup:
                spider.kill()

            for flea in fleaGroup:
                flea.kill()
            
            # Remove mushrooms created by flea
            for mushroom in flea_mushroomGroup:
                mushroom.kill()                

            # Creates a new Centipede
            right = 0
            for x in range(8):
                body = GameSprites.Centipede(screen, right, x, level)
                bodyGroup.add(body)
                right += 16

            allSprites.add(player, bodyGroup)
            death = False

        # If the centipede is killed, level is increased
        if len(bodyGroup) == 0:
            level += 1

            if level == 2:
                # Adds a life 
                life = GameSprites.Lives(left)
                lives.append(life)
                lifeGroup.add(life)
                
                # Changes the colour of the sprites
                player.kill()
                player.change_level()

                for mushroom in mushroomGroup:
                    mushroom.change_level()
                
                for life in lifeGroup:
                    life.change_level()
                    
                scorekeeper.change_level()
                highscore.change_level()

                # Creates a new Centipede
                right = 0
                for x in range(8):
                    body = GameSprites.Centipede(screen, right, x, level)
                    bodyGroup.add(body)
                    right += 16
                    
                allSprites.add(bodyGroup)

        # If there are are no sprites in the lifeGroup and the level is 3, 
        # append the score to the highscore.txt file and stop the gaming loop
        if len(lifeGroup) == 0 or level == 3:
            infile = open("highscore.txt", 'a')
            infile.write(str(scorekeeper.get_score())+ "\n")
            infile.close()
            keepGoing = False

        # REFRESH SCREEN
        allSprites.clear(screen, background)
        allSprites.update()
        allSprites.draw(screen)       
        pygame.display.flip()
        
    # Display "Game Over" graphic and fade out background music
    screen.blit(gameover, (100, 180))
    pygame.display.flip()
    pygame.mixer.music.fadeout(3000)
    pygame.time.delay(3000)
            
    # Unhide the mouse pointer
    pygame.mouse.set_visible(True)
        
def game_menu():
    '''This function defines the game menu for the Centipede game.'''

    # DISPLAY
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Centipede")
    pygame.display.set_icon(pygame.image.load("mushroom_icon.png"))
    
    # ENTITIES
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background = pygame.transform.scale(background, (640, 480))
    background.fill((0, 0, 0))
    
    title_font = pygame.font.Font("ARCADECLASSIC.TTF", 100)
    font = pygame.font.Font("ARCADECLASSIC.TTF", 60)
    
    title_label = title_font.render("Centipede", 1, (255, 255, 255))
    play_label = font.render("Play", 1, (0, 0, 0))
    quit_label = font.render("Quit", 1, (0, 0, 0))
    
    # Background Music
    pygame.mixer.music.load("Sound/menu music.mp3")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
    
    # ASSIGN
    clock = pygame.time.Clock()
    keepGoing = True

    # LOOP
    while keepGoing:

        # TIME
        clock.tick(60)

        # EVENT HANDLING
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 2
        
        # Checks if the play or quit button has been pressed
        if play_button(background):
            pygame.mixer.music.fadeout(1000)
            pygame.time.delay(1000)            
            return 1
        elif quit_button(background):
            pygame.mixer.music.fadeout(1000)
            pygame.time.delay(1000)            
            return 2
        
        # REFRESH SCREEN      
        screen.blit(background, (0,0))
        screen.blit(title_label, (70, 70))
        screen.blit(play_label, (140, 240))
        screen.blit(quit_label, (365, 240))
        pygame.display.flip()

def play_button(background):
    '''This function defines the play button for my game menu.'''
    
    mouse = pygame.mouse.get_pos()
    pressed = pygame.mouse.get_pressed()
    
    # Changes the colour of the button if the mouse position is within the rect
    if 130 < mouse[0] < 280 and 240 < mouse[1] < 300:
        pygame.draw.rect(background, (0, 255, 0), ((130, 240), (150, 60)))
        # Returns a 1 if the left mouse button is clicked
        if pressed[0]:
            return 1
    else:
        pygame.draw.rect(background, (0, 150, 0), ((130, 240), (150, 60)))

def quit_button(background):
    '''This function defines the quit button for my game menu.'''
    
    mouse = pygame.mouse.get_pos()
    pressed = pygame.mouse.get_pressed()
    
    # Changes the colour of the button if the mouse position is within the rect
    if 350 < mouse[0] < 500 and 240 < mouse[1] < 300:
        pygame.draw.rect(background, (255, 0, 0), ((350, 240), (150, 60)))
        # Returns a 1 if the left mouse button is clicked
        if pressed[0]:
            return 1
    else:
        pygame.draw.rect(background, (150, 0, 0), ((350, 240), (150, 60)))
        
def main():
    '''This function defines the "main line" logic of the program.'''
    
    menu = game_menu()
    keepGoing = True
    
    # loop switches between game and menu until the user clicks the quit button
    while keepGoing:
        if menu == 1:
            game()
        elif menu == 2:
            break
        menu = game_menu()
        
    pygame.quit()

# Call the main function
main()