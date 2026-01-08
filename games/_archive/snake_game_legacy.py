# Snake Game in Python 3 using Pygame
# Refactored from turtle version

import pygame
import random
import sys
import os

# Constants - Use larger cells for fewer, larger pixels
CELL_SIZE = 40
GRID_WIDTH = 15
GRID_HEIGHT = 15
WINDOW_WIDTH = CELL_SIZE * GRID_WIDTH
WINDOW_HEIGHT = CELL_SIZE * GRID_HEIGHT
FPS = 10

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
DARK_GREEN = (0, 100, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)

# Snake body is white
SNAKE_COLOR = WHITE


def run_game(screen=None, return_to_menu=None):
    """
    Run the snake game.

    Args:
        screen: Pygame display surface (if None, creates its own)
        return_to_menu: Callback function to return to menu (if None, quits)
    """
    # Initialize pygame if not already done
    if not pygame.get_init():
        pygame.init()

    # Use provided screen or create new one
    own_screen = screen is None
    if own_screen:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Game")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    # Load sprites for ferret-themed snake game
    script_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(script_dir, '..', '..', 'media')

    # Load ferret sprite for the snake head
    ferret_path = os.path.join(media_dir, 'ferret-long-sprite.png')
    try:
        ferret_img = pygame.image.load(ferret_path).convert_alpha()
        ferret_img = pygame.transform.scale(ferret_img, (CELL_SIZE, CELL_SIZE))
    except:
        ferret_img = None

    # Load soupcan_new image for food and body segments (with translucency)
    # Preserve aspect ratio to avoid distortion
    soupcan_path = os.path.join(media_dir, 'soupcan_new.png')
    try:
        soupcan_img = pygame.image.load(soupcan_path).convert_alpha()
        # Scale preserving aspect ratio
        orig_w, orig_h = soupcan_img.get_size()
        scale = min(CELL_SIZE / orig_w, CELL_SIZE / orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        soupcan_img = pygame.transform.scale(soupcan_img, (new_w, new_h))
        # Apply translucency to match other game sprites
        soupcan_img.set_alpha(200)
    except:
        soupcan_img = None

    # Game state
    def reset_game():
        snake = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        direction = (0, 0)  # Start stationary
        food = spawn_food(snake)
        score = 0
        return snake, direction, food, score

    def spawn_food(snake):
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            if (x, y) not in snake:
                return (x, y)

    snake, direction, food, score = reset_game()
    high_score = 0
    running = True
    game_over = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN and game_over:
                    snake, direction, food, score = reset_game()
                    game_over = False
                elif not game_over:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        if direction != (0, 1):
                            direction = (0, -1)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        if direction != (0, -1):
                            direction = (0, 1)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        if direction != (1, 0):
                            direction = (-1, 0)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        if direction != (-1, 0):
                            direction = (1, 0)

        if not game_over and direction != (0, 0):
            # Move snake
            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            # Check collisions with walls
            if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
                new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
                game_over = True
                if score > high_score:
                    high_score = score
            # Check collision with self
            elif new_head in snake:
                game_over = True
                if score > high_score:
                    high_score = score
            else:
                snake.insert(0, new_head)

                # Check if food eaten
                if new_head == food:
                    score += 10
                    food = spawn_food(snake)
                else:
                    snake.pop()

        # Draw
        screen.fill(GREEN)

        # Draw grid lines (subtle)
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(screen, DARK_GREEN, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(screen, DARK_GREEN, (0, y), (WINDOW_WIDTH, y))

        # Draw food (soupcan_new)
        food_rect = pygame.Rect(food[0] * CELL_SIZE, food[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        if soupcan_img:
            screen.blit(soupcan_img, food_rect)
        else:
            pygame.draw.rect(screen, RED, food_rect)

        # Draw snake - ferret head with soupcan_new body segments
        for i, segment in enumerate(snake):
            segment_rect = pygame.Rect(segment[0] * CELL_SIZE, segment[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if i == 0:
                # Head is the ferret
                if ferret_img:
                    screen.blit(ferret_img, segment_rect)
                else:
                    pygame.draw.rect(screen, SNAKE_COLOR, segment_rect)
            else:
                # Body segments are soupcan_new
                if soupcan_img:
                    screen.blit(soupcan_img, segment_rect)
                else:
                    pygame.draw.rect(screen, SNAKE_COLOR, segment_rect)

        # Draw score
        score_text = font.render(f"Score: {score}  High Score: {high_score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        # Draw game over message
        if game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            game_over_text = font.render("GAME OVER", True, RED)
            restart_text = font.render("Press ENTER to restart or ESC to exit", True, WHITE)

            screen.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, WINDOW_HEIGHT // 2 - 30))
            screen.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT // 2 + 10))

        # Draw controls hint
        if direction == (0, 0) and not game_over:
            hint_text = font.render("Use WASD or Arrow Keys to move", True, WHITE)
            screen.blit(hint_text, (WINDOW_WIDTH // 2 - hint_text.get_width() // 2, WINDOW_HEIGHT // 2))

        pygame.display.flip()
        clock.tick(FPS)

    # Cleanup
    if own_screen:
        pygame.quit()

    # Return to menu if callback provided
    if return_to_menu:
        return_to_menu()


# Allow running standalone
if __name__ == "__main__":
    pygame.init()
    run_game()
