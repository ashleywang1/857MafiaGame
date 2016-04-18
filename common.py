"""
Functions, classes, variables, etc. used in various
other files.
"""

from enum import Enum, unique

@unique
class Stage(Enum):
    INITIALIZATION = 1
    SETUP = 2
    DAY = 3
    NIGHT = 4
    DEAD = 5

@unique
class Role(Enum):
    MAFIA = 1
    TOWNSPERSON = 2
    DOCTOR = 3
    DETECTIVE = 4
