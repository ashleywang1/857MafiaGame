"""
Mafia Game Startup File
"""

# Standard library imports
import json
from random import SystemRandom
import socket
import sys

# External dependencies
from tornado.httpclient import AsyncHTTPClient
import tornado.ioloop
from tornado.options import parse_command_line
import tornado.web

# Local file imports
from common import *
from crypto import CommutativeCipher
from util import EnumEncoder, as_enum

#======================================================================
# Global State + Constants
#======================================================================
RANDOM = SystemRandom()
CRYPTO_INSTANCE = None # Instances created and used by various protocols

CONNECT_TIMEOUT = 1 # Seconds
REQUEST_TIMEOUT = 1 # Seconds
ENCODING = 'UTF-8'
HEADERS = {
    'Content-Type': 'application/json',
    'Upgrade': 'websocket',
    'Connection': 'Upgrade'
}

ASYNC_HTTP_CLIENT = AsyncHTTPClient()

# This should later be moved to the Config Files
SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_URL = 'http://{}'.format(SERVER_IP)
#player = [int(x) for x in raw_input('IP List: ').split(',')]
PLAYERS = list(range(8870, 8880+1))
# Another possible form of the player list:
#['https://localhost:8870/', 'https://localhost:8871/', 'https://localhost:8872/', 'https://localhost:8873/', 'https://localhost:8874/', 'https://localhost:8875/', 'https://localhost:8876/', 'https://localhost:8877/', 'https://localhost:8878/', 'https://localhost:8879/', 'https://localhost:8880/']

# TODO: Make this variable with number of players
ROLE_DISTRIBUTION = {
    Role.DETECTIVE: 1,
    Role.DOCTOR: 1,
    Role.MAFIA: 3,
    Role.TOWNSPERSON: 6
}

# Settings for each player
ME = -1
ROLE = None # Mafia, Townsperson, Doctor, Detective

# Mafia settings
MAFIA = False
MAFIA_SECRET_KEY = None #secret key for mafia_channel

# Hearbeat settings
STATE = Stage.INITIALIZATION
ROUND = 0
LYNCHED = []
KILLED = []

MAFIA_DEAD = False
TOWN_DEAD = False
#======================================================================

def send_heartbeats():
    for i, player in enumerate(PLAYERS):
        if i == ME: continue # Don't send heartbeat to yourself
        send_to_player(player, 'heartbeat', callback=verify_hearbeat(i))

def day_round(self):
    for i, player in enumerate(PLAYERS):
        if i == ME: continue

        try:
            r = send_to_player(player, 'day')
            #print(json.loads(r.body))
        except Exception:
            self.write('\nPlayer {} has no response!\n'.format(i))


def night_round(self):
    for i, player in enumerate(PLAYERS):
        if i == ME: continue

        try:
            r = send_to_player(player, 'night')
            wait(r)
            print(json.loads(r.result().body))
        except tornado.httpclient.HTTPError as e:
            pass # TODO: Handle this

def setup(self):
    x = 0 # TODO: secret key
    cards = [{'card': (Role.MAFIA, x), 'taken': False}] * ROLE_DISTRIBUTION[Role.MAFIA]
    cards.extend([{'card': (Role.TOWNSPERSON, None), 'taken': False}] * ROLE_DISTRIBUTION[Role.TOWNSPERSON])
    cards.extend([{'card': (Role.DETECTIVE, None), 'taken': False}] * ROLE_DISTRIBUTION[Role.DETECTIVE])
    cards.extend([{'card': (Role.DOCTOR, None), 'taken': False}] * ROLE_DISTRIBUTION[Role.DOCTOR])

    # Stringify the list items in preparation for encryption
    global CRYPTO_INSTANCE
    CRYPTO_INSTANCE = CommutativeCipher()
    encrypted_cards = [{
        'card': (CRYPTO_INSTANCE.encrypt(json.dumps(block['card'], cls=EnumEncoder))),
        'taken': block['taken']
    } for block in cards]
    RANDOM.shuffle(encrypted_cards)
    data = {
        'cards': json.dumps(encrypted_cards, cls=EnumEncoder),
        'stage': json.dumps(Stage.SETUP, cls=EnumEncoder),
        'step': 0
    }
    print('when {} {}'.format(ME, ROLE))
    send_to_next_player('setup', data=data, GET=False)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Welcome to the Mafia Game Lobby!')
        print('Player {} has joined the game!'.format(ME))
        data = {'stage': Stage.INITIALIZATION}

        # Check initial state
        send_heartbeats()

        # Start the setup process if first player
        if ME == 0: setup(self)

        #day_round(self)
        #night_round(self)
        #r = requests.post('http://localhost:8870/setup/',headers=HEADERS,data=json.dumps(data))
        #r = requests.post('http://localhost:8871/setup/',headers=HEADERS,data=json.dumps(data))

class SetupHandler(tornado.web.RequestHandler):
    # Player A: Encrypts list of (mafia,x), (mafia,x), (doctor,0)...Sends list to B
    # Player B: Encrypts A's encrypted cardList with secret y ......Sends Enc(cardList, y) to C
    # Player C -> N -> A: chooses one, removes it, sends to next player
    # Player A: reveal A's secret key
    # Player B: reveal B's secret key

    def first_stage(self, cards):
        """
        Randomly chooses a single card and encrypts it.
        Returns the shuffled cards containing the newly encrypted card.
        """
        available_card_indices = [i for i, block in enumerate(cards) if not block['taken']]
        index = RANDOM.choice(available_card_indices)
        cards[index]['card'] = CRYPTO_INSTANCE.encrypt(cards[index]['card'], base64=True)
        cards[index]['taken'] = True
        RANDOM.shuffle(cards)
        return cards

    def second_stage(self, cards, first_player):
        my_card_index = -1

        # First player decrypts all cards before sending on
        if first_player: decrypted_cards = []
        for i, card in enumerate(cards):
            # Try to parse the card and keep going upon failure
            if first_player:
                card = card['card']
                # Remove first player's layer on encryption
                decrypted_value = CRYPTO_INSTANCE.decrypt(card, base64=True)
                decrypted_cards.append(decrypted_value)

            try:
                decrypted_json = CRYPTO_INSTANCE.decrypt(card)
                decrypted_card = json.loads(decrypted_json, object_hook=as_enum)
            except json.JSONDecodeError:
                continue
            except UnicodeDecodeError:
                continue

            if isinstance(decrypted_card[0], Role):
                ROLE, MAFIA_SECRET_KEY = decrypted_card
                print(ME, ROLE)
                my_card_index = i

                # If not the first player, terminate early
                # First player must keep going since he/she needs to decrypt all
                if not first_player: break

        if my_card_index == -1: raise Exception('No valid plaintext card found!')

        # Replace card with decrypted if first player
        if first_player: cards = decrypted_cards

        # Remove my card from the card list
        cards.pop(my_card_index)
        return cards

    def post(self):
        first_player = (ME == 0)
        data = load_request_body(self.request.body)
        cards = json.loads(data['cards'], object_hook=as_enum)
        stage = json.loads(data['stage'], object_hook=as_enum)
        step = int(data['step'])

        assert stage == Stage.SETUP, 'Players do not agree on current stage!'

        # Set appropriate state
        global CRYPTO_INSTANCE
        if not CRYPTO_INSTANCE: CRYPTO_INSTANCE = CommutativeCipher()
        STATE = Stage.SETUP

        # Cards have reached first player again, so next step should start
        if first_player: step += 1

        # In first step, all players encrypt one card
        if step == 0:
            cards = self.first_stage(cards)
            data = {
                'cards': json.dumps(cards, cls=EnumEncoder),
                'stage': json.dumps(Stage.SETUP, cls=EnumEncoder),
                'step': step
            }
            send_to_next_player('setup', data=data, GET=False)

        # In second step, all players decrypt everything and get the plaintext card
        elif step == 1:
            cards = self.second_stage(cards, first_player)
            data = {
                'cards': json.dumps(cards, cls=EnumEncoder),
                'stage': json.dumps(Stage.SETUP, cls=EnumEncoder),
                'step': step
            }
            send_to_next_player('setup', data=data, GET=False)

        # Setup process done!
        elif step == 2:
            print('Setup process done!')
            send_heartbeats() # TODO: Get all players to do this here?

            # Set up state for next stage
            CRYPTO_INSTANCE = None
            STATE = Stage.DAY
            # TODO: Continue on to next step

        else: raise Exception('Invalid step reached during setup process!')

class NightHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's night!")
        print('night')
        #data = {'data':[]}
        #r = requests.post('http://localhost:8870/setup/',headers=HEADERS,data=json.dumps(data))

class DayHandler(tornado.web.RequestHandler):
    def lynch(self, player):
        if player == ME:
            # you are dead!
            stage = Stage.DEAD
        LYNCHED.append(player)

    def get(self):
        self.write("It's day!")
        print('day')
        player_to_lynch = str(-1)
        self.write(player_to_lynch)

        #data = {'data':[]}

class MessageHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('No messages received!')
        print('msg')
        #data = {'data':[]}
        #r = requests.post('http://localhost:8870/setup/',headers=HEADERS,data=json.dumps(data))

class HeartbeatHandler(tornado.web.RequestHandler):
    # synchronize STATE = {Day, Night, Setup}
    # synchronize ROUND = 0 to numPlayers at most
    # synchronize dead_players = {LYNCHED[], KILLED[]}
    # synchronize mafia_dead = False, True
    # synchronize townspeople_dead = False,True
    def get(self):
        heartbeat = {
            'state': STATE,
            'round': ROUND,
            'dead_players': LYNCHED + KILLED,
            'mafia_dead': False,
            'town_dead': False
        }
        self.write(json.dumps(heartbeat, cls=EnumEncoder))

def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/setup', SetupHandler),
        (r'/night', NightHandler),
        (r'/day', DayHandler),
        (r'/message', MessageHandler),
        (r'/heartbeat', HeartbeatHandler)
    ])

def load_request_body(body):
    return json.loads(body.decode(ENCODING), object_hook=as_enum)

def verify_hearbeat(player):
    def check_heartbeat_response(response):
        try:
            heartbeat = load_request_body(response.body)
            # TODO: Do something if there is disagreement
            assert heartbeat['state'] == STATE, 'Heartbeat state did not match!'
            assert heartbeat['round'] == ROUND, 'Round numbers do not match!'
            assert heartbeat['dead_players'] == LYNCHED + KILLED, 'Dead players list does not match!'
            assert heartbeat['mafia_dead'] == MAFIA_DEAD, 'Mafia dead (end condition) disagreement!'
            assert heartbeat['town_dead'] == TOWN_DEAD, 'Town dead (end condition) disagreement!'
            print('Heartbeat check by player {} for player {} successful!'.format(ME, player))
        except json.JSONDecodeError:
            raise Exception('Problem parsing heartbeat from player {}!'.format(player))

    return check_heartbeat_response

def send_to_next_player(endpoint, data=None, callback=None,
                        connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    next_player = PLAYERS[(ME + 1) % len(PLAYERS)]
    send_to_player(next_player, endpoint, data, callback=callback,
                   connect_timeout=connect_timeout, request_timeout=request_timeout, GET=GET)

def send_to_player(player, endpoint, data=None, callback=None,
                   connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    url = '{server_url}:{player}/{endpoint}'.format(
        server_url=SERVER_URL,
        player=player,
        endpoint=endpoint
    )

    method = 'GET' if GET else 'POST'
    if not GET and data is not None: data = json.dumps(data, cls=EnumEncoder)
    return ASYNC_HTTP_CLIENT.fetch(url, body=data, method=method, callback=callback,
                                   connect_timeout=connect_timeout, request_timeout=request_timeout)

if __name__ == '__main__':
    # Run server with python mafia.py 'list of player ips' 'ME'
    # ex: python mafia.py '8871, 8872, 8873, 8874, 8875, 8876, 8877, 8878, 8879, 8880' 0
    app = make_app()
    argv = parse_command_line(sys.argv)
    if len(argv) != 2:
        raise ValueError("Please run server with arguments 'list of player ips' 'ME'")
    # set global variables
    PLAYERS = [int(x) for x in argv[0].split(',')]
    ME = int(argv[1])

    # Check that the number of roles equals the number of players
    NUM_PLAYERS = len(PLAYERS)
    NUM_ROLES = sum(ROLE_DISTRIBUTION.values())
    assert NUM_ROLES == NUM_PLAYERS, '{} roles but {} players!'.format(NUM_ROLES, NUM_PLAYERS)

    # start the mafia server
    port = PLAYERS[ME]
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
