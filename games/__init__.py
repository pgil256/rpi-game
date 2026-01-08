"""
Games package for the Weasel Entertainment System.

This package exports all game classes and their run functions.
"""

from .snake import SnakeGame
from .pacman import PacmanGame
from .frogger import FroggerGame
from .centipede import CentipedeGame
from .digdug import DigDugGame
from .boulderdash import BoulderDashGame

__all__ = [
    'SnakeGame',
    'PacmanGame',
    'FroggerGame',
    'CentipedeGame',
    'DigDugGame',
    'BoulderDashGame',
]
