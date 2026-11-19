"""
Burrow Defender - Winston Entertainment System

A ferret defends its burrow from an invading weasel-colored centipede!
The player controls an animated ferret turret that shoots projectiles
at the centipede before it reaches the bottom of the screen.

Features:
- AnimatedFerret player with IDLE/MOVEMENT/DEATH animations
- Weasel-colored centipede (brown head, tan/white body pattern)
- Cute soup bowl obstacles (much cuter than mushrooms!)
- Single bullet mechanic with 8-segment centipede
"""

import os
import random
import pygame

from engine import (
    BaseGame,
    AnimatedFerret,
    AssetLoader,
    AudioManager,
    Difficulty,
    get_score_manager,
    get_stats_manager,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    BLACK,
    WHITE,
    YELLOW,
    WEASEL_BROWN,
    WEASEL_TAN,
)

import math

# Enhanced cute garden color palette
GARDEN_BG_DARK = (30, 50, 35)  # Deep forest green
GARDEN_BG_LIGHT = (50, 80, 55)  # Lighter garden green
GARDEN_GRASS = (80, 140, 90)  # Grass color
FLOWER_PINK = (255, 182, 193)  # Pink flowers
FLOWER_YELLOW = (255, 255, 150)  # Yellow flowers
FLOWER_PURPLE = (200, 160, 220)  # Purple flowers
STAR_GLOW = (255, 255, 200)  # Firefly/star glow


class CentipedeGame(BaseGame):
    """Burrow Defender: a ferret protects its garden from beetles."""

    # Game constants
    PLAYER_SPEED = 4
    BULLET_SPEED = 15
    CENTIPEDE_SEGMENTS = 8
    SOUP_BOWL_COUNT = 30  # Soup bowls as obstacles (cuter than mushrooms!)
    MAX_SOUP_BOWLS = 80
    FIRE_INTERVAL = 8
    PLAYER_AREA_HEIGHT = 112  # Bottom area where player can move
    SPRITE_SIZE = 16
    PLAYER_SIZE = 32

    # Enemy spawn timing (in frames at 60 FPS)
    SPIDER_SPAWN_MIN = 600  # 10 seconds
    SPIDER_SPAWN_MAX = 900  # 15 seconds
    FLEA_SOUP_THRESHOLD = 20  # Spawn flea when soup bowls fall below this
    FLEA_SPAWN_COOLDOWN = 300  # 5 seconds between flea spawns

    # Difficulty presets
    DIFFICULTY_PRESETS = {
        Difficulty.EASY: {
            "centipede_speed": 1,  # Slow centipede
            "centipede_segments": 6,  # Fewer segments
        },
        Difficulty.NORMAL: {
            "centipede_speed": 2,  # Normal speed
            "centipede_segments": 8,  # Normal segments
        },
        Difficulty.HARD: {
            "centipede_speed": 3,  # Fast centipede
            "centipede_segments": 12,  # More segments
        },
    }

    def setup(self):
        """Initialize game state."""
        # Apply difficulty settings
        preset = self.DIFFICULTY_PRESETS[self.difficulty]
        self.centipede_speed = preset["centipede_speed"]
        self.centipede_segments = preset["centipede_segments"]

        self.font = pygame.font.Font(None, 30)
        self.wave = 1
        self._fire_cooldown = 0
        self._move_input = (0, 0)
        self._firing = False

        # Animation timer for visual effects
        self._anim_timer = 0

        # Generate garden decorations
        self._generate_garden()

        # Get base directory for loading sprites
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Asset loader for beetle sprites
        self.asset_loader = AssetLoader(self.base_dir)

        # Load sprites
        self._load_sprites()

        # Game state
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.death_timer = 0
        self.death_duration = 60  # Frames for death animation
        self.paused = False
        self.score_manager = get_score_manager()
        self.stats = get_stats_manager()
        self.high_score = self.score_manager.get_high_score("centipede", difficulty=self.difficulty)
        self.new_high_score = False
        self._centipedes_destroyed = 0  # Track for stats
        self._spiders_killed = 0  # Track for stats
        self._deaths = 0  # Track for stats

        # Spider and flea spawn timers
        self.spider_spawn_timer = random.randint(self.SPIDER_SPAWN_MIN, self.SPIDER_SPAWN_MAX)
        self.flea_spawn_cooldown = 0

        # Create game objects
        self._create_player()
        self._create_centipede()
        self._create_soup_bowls()

        # Bullets group
        self.bullets = pygame.sprite.Group()

        # Enemy groups (spider, flea)
        self.spiders = pygame.sprite.Group()
        self.fleas = pygame.sprite.Group()
        self._cache_garden()

    def _load_sprites(self):
        """Load all game sprites."""
        # Load soup bowl sprite for obstacles (cuter than mushrooms!)
        soup_bowl_base = self.asset_loader.load_image(
            "soupbowl.png", (self.SPRITE_SIZE, self.SPRITE_SIZE)
        )
        if soup_bowl_base is None:
            # Fallback: brown bowl shape
            soup_bowl_base = pygame.Surface((self.SPRITE_SIZE, self.SPRITE_SIZE), pygame.SRCALPHA)
            pygame.draw.ellipse(soup_bowl_base, WEASEL_TAN, (0, 4, 16, 12))
            pygame.draw.ellipse(soup_bowl_base, WEASEL_BROWN, (2, 6, 12, 8))

        # Create 4 damage states for soup bowls (progressively emptier)
        self.soup_bowl_sprites = self._create_soup_bowl_damage_states(soup_bowl_base)

        # Original garden beetle art; no branded source artwork.
        beetle_base = pygame.Surface((self.SPRITE_SIZE, self.SPRITE_SIZE), pygame.SRCALPHA)
        pygame.draw.ellipse(beetle_base, (174, 110, 85), (2, 1, 12, 14))
        pygame.draw.line(beetle_base, (90, 55, 45), (8, 3), (8, 14), 2)
        pygame.draw.circle(beetle_base, WHITE, (5, 4), 2)
        pygame.draw.circle(beetle_base, WHITE, (11, 4), 2)

        # Create centipede sprites from beetle
        self.head_sprites = self._create_beetle_centipede_sprites(beetle_base, is_head=True)
        self.body_sprites = self._create_beetle_centipede_sprites(beetle_base, is_head=False)

        # Spider sprite - beetle with slight tint
        self.spider_sprite = self._create_enemy_sprite(beetle_base, tint=(200, 100, 100))

        # Flea sprite - beetle with different tint
        self.flea_sprite = self._create_enemy_sprite(beetle_base, tint=(100, 200, 100))

        # Projectile sprite - bright yellow/orange bolt (distinct from beetle)
        self.bullet_sprite = self._create_bullet_sprite()

    def _create_soup_bowl_damage_states(self, soup_bowl_base):
        """Create 4 damage states for soup bowls (full to empty)."""
        sprites = []
        size = self.SPRITE_SIZE

        for damage in range(4):
            s = soup_bowl_base.copy()

            if damage > 0:
                # Add visual damage - darken and add "eaten" effect
                # Create a mask to show soup being consumed
                damage_overlay = pygame.Surface((size, size), pygame.SRCALPHA)

                if damage == 1:
                    # 25% eaten - small dark spot
                    pygame.draw.circle(damage_overlay, (0, 0, 0, 100), (size // 2, size // 2), 2)
                elif damage == 2:
                    # 50% eaten - larger dark area
                    pygame.draw.circle(damage_overlay, (0, 0, 0, 120), (size // 2, size // 2), 4)
                elif damage == 3:
                    # 75% eaten - mostly empty bowl
                    pygame.draw.circle(damage_overlay, (0, 0, 0, 150), (size // 2, size // 2), 5)

                s.blit(damage_overlay, (0, 0))

            sprites.append(s.convert_alpha())

        return sprites

    def _create_beetle_centipede_sprites(self, beetle_base, is_head):
        """Create animated sprites for centipede segments using beetle sprite."""
        sprites = []
        size = self.SPRITE_SIZE

        for frame in range(8):
            # Start with a copy of the beetle
            s = beetle_base.copy()

            if is_head:
                # Head gets a slightly larger appearance and eye indicator
                # Add a small weasel-brown dot as "eye"
                eye_x = size * 3 // 4 if frame % 2 == 0 else size // 4
                pygame.draw.circle(s, WEASEL_BROWN, (eye_x, size // 3), 3)
                pygame.draw.circle(s, BLACK, (eye_x, size // 3), 2)
            else:
                # Body segments get slight animation wobble by shifting
                if frame % 3 == 1:
                    # Create wobble effect
                    temp = pygame.Surface((size, size), pygame.SRCALPHA)
                    temp.blit(s, (0, 1))
                    s = temp

            sprites.append(s.convert_alpha())

        return sprites

    def _create_enemy_sprite(self, beetle_base, tint):
        """Create an enemy sprite from beetle with a color tint."""
        s = beetle_base.copy()
        # Apply tint by blending
        tint_surface = pygame.Surface((self.SPRITE_SIZE, self.SPRITE_SIZE), pygame.SRCALPHA)
        tint_surface.fill((*tint, 60))  # Semi-transparent tint
        s.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return s.convert_alpha()

    def _create_bullet_sprite(self):
        """Create a bright projectile sprite distinct from beetle."""
        size = 8
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        # Bright yellow/orange bolt
        pygame.draw.circle(s, YELLOW, (size // 2, size // 2), size // 2)
        pygame.draw.circle(s, (255, 200, 0), (size // 2, size // 2), size // 2 - 1)
        # Add bright center
        pygame.draw.circle(s, WHITE, (size // 2, size // 2), 2)
        return s.convert_alpha()

    def _create_player(self):
        """Create the player ferret."""
        self.player = AnimatedFerret(
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - self.PLAYER_SIZE // 2 - 10,
            scale=1,  # Match sprite size
            speed=self.PLAYER_SPEED,
            frame_delay=8,
        )
        # Match the original 32px artwork and collision box, including edges.
        self.player.set_sprite_size(self.PLAYER_SIZE)

    def _create_centipede(self):
        """Create the centipede with all segments."""
        self.centipede = pygame.sprite.Group()
        for i in range(self.centipede_segments):  # Use difficulty-based segment count
            is_head = i == self.centipede_segments - 1  # Last segment is head
            segment = CentipedeSegment(
                x=WINDOW_WIDTH - self.SPRITE_SIZE - i * self.SPRITE_SIZE,
                y=64,
                head_sprites=self.head_sprites,
                body_sprites=self.body_sprites,
                is_head=is_head,
                segment_index=i,
                speed=self.centipede_speed,  # Use difficulty-based speed
            )
            self.centipede.add(segment)

    def _create_soup_bowls(self):
        """Create random soup bowl obstacles."""
        self.soup_bowls = pygame.sprite.Group()
        for _ in range(self.SOUP_BOWL_COUNT):
            x = random.randint(32, WINDOW_WIDTH - 32)
            y = random.randint(80, WINDOW_HEIGHT - 150)
            soup_bowl = SoupBowl(x, y, self.soup_bowl_sprites)
            self.soup_bowls.add(soup_bowl)

    def handle_input(self):
        """Process player input. Returns True to exit to menu."""
        self.input_manager.update()

        # Back button to exit
        if self.input_manager.back_pressed():
            return True

        if self.game_over:
            if self.death_timer == 0 and self.input_manager.action_pressed():
                self.restart_session()
                self.setup()
            return False

        # Check for pause toggle
        if self.input_manager.pause_pressed() and not self.game_over and self.death_timer == 0:
            self.paused = not self.paused
            return False

        # Don't process input when paused
        if self.paused:
            return False

        # Don't process input during death animation
        if self.death_timer > 0:
            return False

        self._firing = self.input_manager.get_any_action_button()
        self._move_input = self.input_manager.get_dpad()

        return False

    def _fire_bullet(self):
        """Fire a bullet from the player's position."""
        bullet = Bullet(
            self.player.x,
            self.player.y - self.PLAYER_SIZE // 2,
            self.bullet_sprite,
            self.BULLET_SPEED,
        )
        self.bullets.add(bullet)
        self.audio.play_sound(AudioManager.SOUND_SHOT)

    def update(self, dt):
        """Update game logic."""
        # Don't update when paused
        if self.paused:
            return

        # Handle death animation
        if self.death_timer > 0:
            self.player.update(0, 0)
            self.death_timer -= 1
            if self.death_timer <= 0 and not self.game_over:
                self._respawn()
            return
        if self.game_over:
            return

        self._anim_timer += 1
        dx, dy = self._move_input
        if dx and dy:
            dx /= math.sqrt(2)
            dy /= math.sqrt(2)
        self.player.update(dx, dy)
        self.player.clamp_to_bounds(
            0, WINDOW_HEIGHT - self.PLAYER_AREA_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT
        )
        self._fire_cooldown = max(0, self._fire_cooldown - 1)
        if self._firing and self._fire_cooldown == 0 and len(self.bullets) < 3:
            self._fire_bullet()
            self._fire_cooldown = self.FIRE_INTERVAL

        # Update bullets
        self.bullets.update()

        # Update centipede
        for segment in self.centipede:
            segment.update()

            # Check soup bowl collisions for centipede
            hits = pygame.sprite.spritecollide(segment, self.soup_bowls, False)
            if hits:
                segment.descend()
                segment.dx = -segment.dx

        # Update spiders
        self.spiders.update()

        # Update fleas (they leave soup bowls behind)
        for flea in list(self.fleas):
            flea.update(self.soup_bowls, self.soup_bowl_sprites, self.MAX_SOUP_BOWLS)

        # Spider spawn logic
        self.spider_spawn_timer -= 1
        if self.spider_spawn_timer <= 0:
            self._spawn_spider()
            self.spider_spawn_timer = random.randint(self.SPIDER_SPAWN_MIN, self.SPIDER_SPAWN_MAX)

        # Flea spawn logic (when soup bowl count is low)
        if self.flea_spawn_cooldown > 0:
            self.flea_spawn_cooldown -= 1
        if len(self.soup_bowls) < self.FLEA_SOUP_THRESHOLD and self.flea_spawn_cooldown <= 0:
            self._spawn_flea()
            self.flea_spawn_cooldown = self.FLEA_SPAWN_COOLDOWN

        score_before_hits = self.score
        # Bullet vs centipede collisions
        for bullet in list(self.bullets):
            hits = pygame.sprite.spritecollide(bullet, self.centipede, True)
            for hit in hits:
                self.score += hit.points
                self.audio.play_sound(AudioManager.SOUND_HIT)
                self._centipedes_destroyed += 1  # Track for stats
                # Spawn soup bowl where segment was destroyed
                self._add_soup_bowl(hit.rect.x, hit.rect.y)
                bullet.kill()

        # Bullet vs spider collisions
        for bullet in list(self.bullets):
            hits = pygame.sprite.spritecollide(bullet, self.spiders, True)
            for hit in hits:
                self.score += 600  # Spider is worth 600 points
                self.audio.play_sound(AudioManager.SOUND_COLLECT)
                self._spiders_killed += 1  # Track for stats
                self.achievements.unlock("centipede_spider")
                bullet.kill()

        # Bullet vs flea collisions
        for bullet in list(self.bullets):
            hits = pygame.sprite.spritecollide(bullet, self.fleas, True)
            for hit in hits:
                self.score += 200  # Flea is worth 200 points
                self.audio.play_sound(AudioManager.SOUND_COLLECT)
                bullet.kill()

        # Bullet vs soup bowl collisions
        for bullet in list(self.bullets):
            hits = pygame.sprite.spritecollide(bullet, self.soup_bowls, False)
            for soup_bowl in hits:
                self.audio.play_sound(AudioManager.SOUND_HIT)
                if soup_bowl.hit():
                    self.score += 1
                bullet.kill()

        if score_before_hits < 500 <= self.score:
            self.achievements.unlock("centipede_500")
        # Player vs centipede collision
        player_rect = self.player.get_body_rect()
        for segment in self.centipede:
            if player_rect.colliderect(segment.rect):
                self._player_death()
                return

        # Player vs spider collision
        for spider in self.spiders:
            if player_rect.colliderect(spider.rect):
                self._player_death()
                return

        # Player vs flea collision
        for flea in self.fleas:
            if player_rect.colliderect(flea.rect):
                self._player_death()
                return

        # Respawn centipede if all destroyed
        if len(self.centipede) == 0:
            self.audio.play_sound(AudioManager.SOUND_VICTORY)
            # Check achievements
            self.achievements.unlock("centipede_first")
            self.stats.increment("global", "games_completed")
            self.wave += 1
            preset = self.DIFFICULTY_PRESETS[self.difficulty]
            self.centipede_speed = min(6, preset["centipede_speed"] + (self.wave - 1) // 2)
            self.centipede_segments = min(20, preset["centipede_segments"] + self.wave - 1)
            self._create_centipede()

    def _add_soup_bowl(self, x, y):
        """Bound collision work and keep only one bowl per grid cell."""
        cell = (x - x % 16, y - y % 16)
        if len(self.soup_bowls) < self.MAX_SOUP_BOWLS and not any(
            bowl.rect.topleft == cell for bowl in self.soup_bowls
        ):
            self.soup_bowls.add(SoupBowl(x, y, self.soup_bowl_sprites))

    def _spawn_spider(self):
        """Spawn a spider enemy at the edge of the player area."""
        # Spider enters from left or right side
        from_left = random.choice([True, False])
        x = -self.SPRITE_SIZE if from_left else WINDOW_WIDTH
        y = random.randint(
            WINDOW_HEIGHT - self.PLAYER_AREA_HEIGHT, WINDOW_HEIGHT - self.SPRITE_SIZE
        )
        spider = Spider(x, y, self.spider_sprite, from_left)
        self.spiders.add(spider)

    def _spawn_flea(self):
        """Spawn a flea enemy at the top of the screen."""
        x = random.randint(32, WINDOW_WIDTH - 32)
        flea = Flea(x, 0, self.flea_sprite)
        self.fleas.add(flea)

    def _player_death(self):
        """Handle player death."""
        if self.death_timer or self.game_over:
            return
        self.lives -= 1
        self._deaths += 1  # Track for stats
        self.player.set_state("death")
        self.death_timer = self.death_duration
        self.audio.play_sound(AudioManager.SOUND_DEATH)

        if self.lives <= 0:
            # Check and save high score
            if self.score_manager.set_high_score(
                "centipede", self.score, difficulty=self.difficulty
            ):
                self.new_high_score = True
                self.high_score = self.score
            # Track statistics
            self._finalize_game_statistics()
            self.game_over = True

    def _record_game_statistics(self):
        self.stats.add("centipede", "total_score", self.score)
        self.stats.increment("centipede", "centipedes_destroyed", self._centipedes_destroyed)
        self.stats.increment("centipede", "spiders_killed", self._spiders_killed)
        self.stats.increment("centipede", "deaths", self._deaths)

    def _respawn(self):
        """Respawn player after death."""
        self._create_player()
        self._create_centipede()
        self.bullets.empty()
        self.spiders.empty()
        self.fleas.empty()
        # Reset spawn timers
        self.spider_spawn_timer = random.randint(self.SPIDER_SPAWN_MIN, self.SPIDER_SPAWN_MAX)
        self.flea_spawn_cooldown = 0
        self._move_input = (0, 0)
        self._firing = False
        self._fire_cooldown = 0

    def _generate_garden(self):
        """Generate cute garden decorations."""
        rng = random.Random(42)

        # Background grass patches
        self._grass_patches = []
        for _ in range(40):
            x = rng.randint(0, WINDOW_WIDTH)
            y = rng.randint(0, WINDOW_HEIGHT)
            w = rng.randint(40, 100)
            h = rng.randint(30, 60)
            self._grass_patches.append((x, y, w, h))

        # Flowers scattered around
        self._flowers = []
        flower_colors = [FLOWER_PINK, FLOWER_YELLOW, FLOWER_PURPLE]
        for _ in range(25):
            x = rng.randint(10, WINDOW_WIDTH - 10)
            y = rng.randint(50, WINDOW_HEIGHT - 50)
            color = rng.choice(flower_colors)
            size = rng.randint(3, 5)
            self._flowers.append((x, y, color, size))

        # Fireflies/stars
        self._fireflies = []
        for _ in range(15):
            x = rng.randint(10, WINDOW_WIDTH - 10)
            y = rng.randint(40, WINDOW_HEIGHT - 50)
            phase = rng.uniform(0, 6.28)
            self._fireflies.append([x, y, phase])

    def _cache_garden(self):
        self._garden_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
        self._garden_surface.fill(GARDEN_BG_DARK)
        for x, y, w, h in self._grass_patches:
            pygame.draw.ellipse(self._garden_surface, GARDEN_BG_LIGHT, (x, y, w, h))
        area = pygame.Surface((WINDOW_WIDTH, self.PLAYER_AREA_HEIGHT), pygame.SRCALPHA)
        area.fill((80, 120, 90, 40))
        self._garden_surface.blit(area, (0, WINDOW_HEIGHT - self.PLAYER_AREA_HEIGHT))
        target = self.screen
        self.screen = self._garden_surface
        for x, y, color, size in self._flowers:
            self._draw_flower(x, y, color, size)
        self.screen = target
        self._glows = {}
        for name, size, color, radius in (
            ("bowl", 24, (255, 220, 180, 40), 10),
            ("spider", 30, (255, 100, 100, 50), 12),
            ("flea", 30, (100, 255, 100, 50), 12),
            ("bullet", 16, (255, 255, 100, 100), 6),
            ("firefly", 14, (*STAR_GLOW, 180), 6),
        ):
            glow = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(glow, color, (size // 2, size // 2), radius)
            self._glows[name] = glow

    def render(self):
        """Draw cached scenery and animated game objects."""
        self.screen.blit(self._garden_surface, (0, 0))
        for x, y, phase in self._fireflies:
            glow = abs(math.sin(self._anim_timer * 0.08 + phase))
            if glow > 0.5:
                sprite = self._glows["firefly"]
                sprite.set_alpha(int((glow - 0.5) * 510))
                self.screen.blit(sprite, (x - 7, y - 7))

        # Draw soup bowls with subtle glow
        for bowl in self.soup_bowls:
            glow_surf = self._glows["bowl"]
            self.screen.blit(glow_surf, (bowl.rect.centerx - 12, bowl.rect.centery - 12))
        self.soup_bowls.draw(self.screen)

        # Draw centipede
        self.centipede.draw(self.screen)

        # Draw spiders with red glow
        for spider in self.spiders:
            glow_surf = self._glows["spider"]
            self.screen.blit(glow_surf, (spider.rect.centerx - 15, spider.rect.centery - 15))
        self.spiders.draw(self.screen)

        # Draw fleas with green glow
        for flea in self.fleas:
            glow_surf = self._glows["flea"]
            self.screen.blit(glow_surf, (flea.rect.centerx - 15, flea.rect.centery - 15))
        self.fleas.draw(self.screen)

        # Draw bullets with trail effect
        for bullet in self.bullets:
            # Yellow glow around bullet
            glow_surf = self._glows["bullet"]
            self.screen.blit(glow_surf, (bullet.rect.centerx - 8, bullet.rect.centery - 8))
        self.bullets.draw(self.screen)

        # Draw player
        self.player.draw(self.screen)

        # Draw HUD with shadow
        hud_text = (
            f"Score {self.score}   High {self.high_score}   Lives {self.lives}   Wave {self.wave}"
        )
        shadow_surface = self.font.render(hud_text, True, (20, 40, 25))
        self.screen.blit(shadow_surface, (11, 11))
        text_surface = self.font.render(hud_text, True, (220, 255, 220))
        self.screen.blit(text_surface, (10, 10))
        controls = self.font.render("Hold A / Space to fire    B: Menu", True, (220, 255, 220))
        self.screen.blit(controls, controls.get_rect(topright=(WINDOW_WIDTH - 10, 10)))

        # Draw pause overlay
        if self.paused:
            self._draw_pause_overlay()

        if self.game_over and self.death_timer == 0:
            self._draw_game_over_overlay(score=self.score)

    def _draw_flower(self, x, y, color, size):
        """Draw a cute garden flower."""
        # Petals
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            px = x + int(size * 0.7 * math.cos(rad))
            py = y + int(size * 0.7 * math.sin(rad))
            pygame.draw.circle(self.screen, color, (px, py), size)
        # Center
        pygame.draw.circle(self.screen, (255, 220, 100), (x, y), max(1, size // 2))


class CentipedeSegment(pygame.sprite.Sprite):
    """A single segment of the centipede."""

    def __init__(self, x, y, head_sprites, body_sprites, is_head=False, segment_index=0, speed=2):
        super().__init__()
        self.is_head = is_head
        self.sprites = head_sprites if is_head else body_sprites
        self.frame_index = 0
        self.base_speed = speed
        self.dx = -speed  # Movement direction (negative = moving left)
        self.points = 100 if is_head else 10
        self.segment_index = segment_index
        self.vertical_direction = 1

        self.image = self.sprites[0]
        self.rect = self.image.get_rect(x=x, y=y)

    def update(self):
        """Update segment position and animation."""
        # Animate
        self.frame_index = (self.frame_index + 1) % len(self.sprites)
        self.image = self.sprites[self.frame_index]

        # Move horizontally
        self.rect.x += self.dx

        # Bounce off walls and descend
        if self.rect.left <= 0 or self.rect.right >= WINDOW_WIDTH:
            self.descend()
            self.rect.clamp_ip(pygame.Rect(0, 40, WINDOW_WIDTH, WINDOW_HEIGHT - 40))
            # Reverse direction while maintaining speed magnitude
            self.dx = self.base_speed if self.dx < 0 else -self.base_speed

    def descend(self):
        """Bounce vertically inside the player area instead of leaving the field."""
        next_y = self.rect.y + 16 * self.vertical_direction
        if next_y + self.rect.height > WINDOW_HEIGHT:
            self.vertical_direction = -1
            next_y = WINDOW_HEIGHT - self.rect.height
        elif self.vertical_direction < 0 and next_y < WINDOW_HEIGHT - 112:
            self.vertical_direction = 1
            next_y = WINDOW_HEIGHT - 112
        self.rect.y = next_y


class SoupBowl(pygame.sprite.Sprite):
    """A soup bowl obstacle that can be damaged (cuter than mushrooms!)."""

    def __init__(self, x, y, sprites):
        super().__init__()
        self.sprites = sprites
        self.hp = 4
        self.image = self.sprites[0]
        # Snap to grid
        self.rect = self.image.get_rect(x=x - x % 16, y=y - y % 16)

    def hit(self):
        """
        Handle being hit by a bullet.

        Returns:
            True if soup bowl was destroyed, False otherwise.
        """
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
            return True
        # Update sprite to show damage (soup getting eaten)
        self.image = self.sprites[4 - self.hp]
        return False


class Bullet(pygame.sprite.Sprite):
    """A projectile fired by the player."""

    def __init__(self, x, y, sprite, speed):
        super().__init__()
        self.image = sprite
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed

    def update(self):
        """Move bullet upward."""
        self.rect.y -= self.speed
        if self.rect.bottom < 0:
            self.kill()


class Spider(pygame.sprite.Sprite):
    """
    Spider enemy that moves diagonally across the bottom of the screen.

    Appears from the left or right side and moves in a zigzag pattern
    through the player's area, then exits the other side.
    """

    SPEED = 3
    VERTICAL_RANGE = 60  # How far up/down the spider moves

    def __init__(self, x, y, sprite, moving_right=True):
        super().__init__()
        self.image = sprite
        self.rect = self.image.get_rect(x=x, y=y)
        self.moving_right = moving_right
        self.dx = self.SPEED if moving_right else -self.SPEED
        self.dy = random.choice([-2, 2])  # Diagonal movement
        self.start_y = y
        self.frame_count = 0

    def update(self):
        """Move spider in zigzag pattern."""
        self.frame_count += 1

        # Move horizontally
        self.rect.x += self.dx

        # Zigzag vertically
        self.rect.y += self.dy

        # Reverse vertical direction at boundaries
        if abs(self.rect.y - self.start_y) > self.VERTICAL_RANGE:
            self.dy = -self.dy

        # Keep within screen vertically
        if self.rect.top < WINDOW_HEIGHT - 150:
            self.rect.top = WINDOW_HEIGHT - 150
            self.dy = abs(self.dy)
        if self.rect.bottom > WINDOW_HEIGHT:
            self.rect.bottom = WINDOW_HEIGHT
            self.dy = -abs(self.dy)

        # Remove when off screen
        if self.moving_right and self.rect.left > WINDOW_WIDTH:
            self.kill()
        elif not self.moving_right and self.rect.right < 0:
            self.kill()


class Flea(pygame.sprite.Sprite):
    """
    Flea enemy that drops from the top of the screen.

    Moves straight down and leaves soup bowls behind as it falls.
    """

    SPEED = 4
    SOUP_DROP_INTERVAL = 32  # Drop soup bowl every N pixels

    def __init__(self, x, y, sprite):
        super().__init__()
        self.image = sprite
        self.rect = self.image.get_rect(x=x, y=y)
        self.last_soup_y = y
        self.hp = 2  # Takes 2 hits to kill

    def update(self, soup_bowls_group, soup_bowl_sprites, max_bowls=80):
        """Move flea downward and drop soup bowls."""
        self.rect.y += self.SPEED

        # Drop soup bowl at intervals
        if self.rect.y - self.last_soup_y >= self.SOUP_DROP_INTERVAL:
            # Check if there's already a soup bowl nearby
            soup_at_pos = False
            for s in soup_bowls_group:
                if abs(s.rect.x - self.rect.x) < 16 and abs(s.rect.y - self.rect.y) < 16:
                    soup_at_pos = True
                    break

            if (
                not soup_at_pos
                and len(soup_bowls_group) < max_bowls
                and self.rect.bottom < WINDOW_HEIGHT - 112
            ):
                new_soup_bowl = SoupBowl(self.rect.x, self.rect.y, soup_bowl_sprites)
                soup_bowls_group.add(new_soup_bowl)

            self.last_soup_y = self.rect.y

        # Remove when off screen
        if self.rect.top > WINDOW_HEIGHT:
            self.kill()
