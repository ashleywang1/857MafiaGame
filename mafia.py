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
SERVER_URL = "http://{}".format(SERVER_IP)
PLAYERS = list(range(8870, 8883+1))# list(range(8870, 8880+1))

# TODO: Make this variable with number of players
ROLE_DISTRIBUTION = {
    Role.DETECTIVE: 1,
    Role.DOCTOR: 1,
    Role.MAFIA: 1,#3,
    Role.TOWNSPERSON: 1#6
}

# Settings for each player
ME = -1
ROLE = None # Mafia, Townsperson, Doctor, Detective

# Mafia settings
MAFIA = False
MAFIA_SECRET_KEY = None #secret key for mafia_channel

# Heartbeat settings
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
        send_to_player(player, 'heartbeat', callback=verify_heartbeat(i))

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        if STATE == Stage.INITIALIZATION:
            print("Welcome to the Mafia Game Lobby!")
            print("Player {} has joined the game!".format(ME))
            # Start the setup process if first player
            if ME == 0: start_setup(self)

def start_setup(self):
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
            # Extend the request timeout for the last player
            # since the first player will start setting up the next stage
            # before responding
            request_timeout = 10*REQUEST_TIMEOUT if ME == len(PLAYERS) - 1 else REQUEST_TIMEOUT
            send_to_next_player('setup', data=data, GET=False, request_timeout=request_timeout)

        # Setup process done!
        elif step == 2:
            print('Setup process done!')
            send_heartbeats() # TODO: Get all players to do this here?

            # Set up state for next stage
            CRYPTO_INSTANCE = None
            STATE = Stage.DAY

            # TODO: Continue on to next step
            start_day_round()

        else: raise Exception('Invalid step reached during setup process!')

def start_day_round():
    vote = input("Which player would you like to kill?")
    while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS) or PLAYERS[int(vote)] in LYNCHED + KILLED:
        print("Sorry! That input is invalid!")
        vote = input("Which player would you like to kill?")
    DayHandler.vote = vote
    data = {
        'stage': json.dumps(Stage.DAY, cls=EnumEncoder),
        'step': 0
    }
    send_to_next_player('day', data, GET=False)

class DayHandler(tornado.web.RequestHandler):

    vote = None

    def lynch(self):
        # Get the votes from all the players
        voteList = [int(self.vote)]
        for i, player in enumerate(PLAYERS):
            if i == ME: continue
            hostname = SERVER_URL + ":" + str(player) + "/day"
            try:
                r = requests.get(hostname, timeout=REQUEST_TIMEOUT)
                v = json.loads(r.text, object_hook=as_enum)
                voteList.append(int(v))
            except Exception:
                self.write("\nPlayer {} has no response!\n".format(i))

        # Figure out who got the most votes
        # tally = [voteList.count(x) for x in set(voteList)]
        # if tally.count(max(tally)) != 1:
        #     return False
        deadPlayer = max(set(voteList), key=voteList.count)
        if deadPlayer == ME: # you are dead!
            stage = Stage.DEAD
        LYNCHED.append(deadPlayer)
        return True

    def cast_vote(self):
        vote = input("Which player would you like to kill?")
        while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS) or PLAYERS[int(vote)] in LYNCHED + KILLED:
            print("Sorry! That input is invalid!")
            vote = input("Which player would you like to kill?")
        DayHandler.vote = vote

    def get(self):
        self.write(json.dumps(self.vote, cls=EnumEncoder))

    def post(self):
        first_player = (ME == 0)
        data = load_request_body(self.request.body)
        stage = json.loads(data['stage'], object_hook=as_enum)
        step = int(data['step'])

        assert stage == Stage.DAY, "Players do not agree on current stage!"

        # Voting has reached first player again
        if ME == 0: step += 1

        if step == 0: # In the first step, players cast their votes
            print('Step 0, I am voting')
            print(str(ME))
            self.cast_vote()
            data = {
                'stage': json.dumps(Stage.DAY, cls=EnumEncoder),
                'step': step
            }
            send_to_next_player('day', data=data, GET=False)

        elif step == 1: # In this step, everyone figures out who died
            print('Step 1, I am lynching')
            data = {
                'stage': json.dumps(Stage.DAY, cls=EnumEncoder),
                'step': step
            }
            self.lynch()
            send_to_next_player('day', data=data, GET=False)

        elif step == 2: # start next step
            print("Day round has ended!")
            start_night_round()
        else:
            raise Exception("Invalid step!")


def start_night_round():
    vote = input("Which player would you like to kill?")
    while not vote.isdigit() or int(vote) < 0 or int(vote) >= 10 or PLAYERS[int(vote)] in LYNCHED + KILLED:
        print("Sorry! That input is invalid!")
        vote = input("Which player would you like to kill?")
    DayHandler.vote = vote
    data = {
        "stage": json.dumps(Stage.NIGHT, cls=EnumEncoder),
        "step": 0
    }
    send_to_next_player('night', data, GET=False)


class NightHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's night!")
        print("night")
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=HEADERS,data=json.dumps(data))

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
        print(heartbeat)
        self.write(json.dumps(heartbeat, cls=EnumEncoder))

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/setup", SetupHandler),
        (r"/day", DayHandler),
        (r"/night", NightHandler),
        (r"/message", MessageHandler),
        (r"/heartbeat", HeartbeatHandler)
    ])

def load_request_body(body):
    return json.loads(body.decode(ENCODING), object_hook=as_enum)

def verify_heartbeat(player):
    def check_heartbeat_response(response):
        if response.error is not None:
            response.rethrow()

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
    # ex: python3 mafia.py '8871, 8872, 8873, 8874, 8875, 8876, 8877, 8878, 8879, 8880' 0
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
