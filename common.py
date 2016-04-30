"""
Functions, classes, variables, etc. used in various
other files.
"""

from enum import Enum, unique
import socket

"""
Server and Message Parameters
"""
SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_URL = 'http://{}'.format(SERVER_IP)

ENCODING = 'UTF-8'
HEADERS = {
    'Content-Type': 'application/json',
    'Upgrade': 'websocket',
    'Connection': 'Upgrade'
}

"""
Time Intervals
"""
CONNECT_TIMEOUT = 1 # Seconds
REQUEST_TIMEOUT = 1 # Seconds

HEARTBEAT_INTERVAL = 60 # Seconds
QUERY_INTERVAL = 2 # Seconds

DAY_VOTING_PERIOD = 5 # Seconds
NIGHT_VOTING_PERIOD = 5 # Seconds

"""
Messages and Prompts
"""
INVALID_INPUT_MESSAGE = "Sorry! That input is invalid!"
LIVE_PLAYERS_MESSAGE = "Players {} are currently alive."
DEAD_PLAYERS_MESSAGE = "Players {} are already dead."
LYNCH_PROMPT = "Which player would you like to lynch? "
MAFIA_KILL_PROMPT = "Which player would you like to kill? "
DOCTOR_SAVE_PROMPT = "Which player would you like to save? "
DETECTIVE_QUERY_PROMPT = "Which player would you like to query? "

"""
Enums
"""
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

"""
Other
"""
MAX_CARD_IDENTIFIER = 2**32
MAX_CARD_NONCE = 2**32
