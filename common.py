"""
Functions, classes, variables, etc. used in various
other files.
"""

from enum import Enum, unique
import socket

# This should later be moved to the Config Files
SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_URL = 'http://{}'.format(SERVER_IP)

CONNECT_TIMEOUT = 1 # Seconds
REQUEST_TIMEOUT = 1 # Seconds

HEARTBEAT_INTERVAL = 15 # Seconds

ENCODING = 'UTF-8'
HEADERS = {
    'Content-Type': 'application/json',
    'Upgrade': 'websocket',
    'Connection': 'Upgrade'
}

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
