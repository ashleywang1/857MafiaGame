"""
Mafia Game Startup File
"""

# Standard library imports
import json
from random import SystemRandom
import sys
import time
import subprocess

# External dependencies
import tornado.ioloop
from tornado.options import parse_command_line
import tornado.web

# Local file imports
import miller_rabin as mr
from common import *
from crypto import CommutativeCipher, DiffieHellman
from util import (
    EnumEncoder, as_enum, # Enum serialization
    send_to_player, query_endpoint, load_request_body, check_response_error, # Requests
    BackgroundTaskRunner # Async tasks
)


#======================================================================
# Global State + Constants
#======================================================================
RANDOM = SystemRandom()
CRYPTO_INSTANCE = None # Instances created and used by various protocols

PLAYERS = []
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

HEARTBEAT_RUNNER = None
# Heartbeat settings
STATE = Stage.INITIALIZATION
ROUND = 0
LYNCHED = []
KILLED = []

MAFIA_DEAD = False
TOWN_DEAD = False
#======================================================================

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        if STATE == Stage.INITIALIZATION:
            print("Welcome to the Mafia Game Lobby!")
            print("Player {} has joined the game!".format(ME))

            # Start up asynchronous heartbeats
            HEARTBEAT_RUNNER = BackgroundTaskRunner(HeartbeatHandler.send_heartbeats, HEARTBEAT_INTERVAL)
            HEARTBEAT_RUNNER.start()

            # Start the setup process if first player
            if ME == 0: start_setup()



def start_setup():
    x = DiffieHellman.generate_prime()
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
    # TODO - special case with player A
    # Player A: Encrypts entire list of roles
    # Player A - N: Choose 1 card, encrypt it, send the resulting list to next player
    # Player A: Decrypt entire list of roles, keep the one in plaintext
    # Player B - N: Try to decrypt all the roles, keep the one in plaintext
    #               , send the unmodified list to next player

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
        """
        First player decrypts all cards and keeps the unencrypted one before
        passing on the rest of the cards decrypted with his/her key.

        Every other player tries decrypting all the cards, keeps the one that
        produces a valid card, and passes the rest unchanged.

        Returns the set of cards in the appropriate state based on the above
        and not including the player's own card.
        """
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

            # Set up state for next stage
            CRYPTO_INSTANCE = None
            STATE = Stage.DAY

            # Continue on to next step
            start_day_round()

        else: raise Exception('Invalid step reached during setup process!')

def start_day_round():
    # Tell everyone to start voting
    data = {
        'stage': json.dumps(Stage.DAY, cls=EnumEncoder),
        'step': 0
    }
    send_to_all_players('day', data, GET=False)

def cast_vote():
    vote = input("Which player would you like to lynch? ")
    while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS):
        print("Sorry! That input is invalid!")
        vote = input("Which player would you like to lynch? ")
    while PLAYERS[int(vote)] in LYNCHED + KILLED:
        print("These players {} are already dead".format(LYNCHED+KILLED))
        vote = input("Which player would you like to lynch? ")
    DayHandler.vote = vote

def get_lynch_votes(query_runner):
    """
    Callback that lynches based on the results of the response
    """
    voteList = []
    def lynch(r, voteList=voteList):
        global ME
        global ROUND
        print("The lynch result is {} ".format(r.body))
        v = load_request_body(r.body)
        if v['vote'] is not None:
            query_runner.stop()
        voteList.append(v['vote'])

        if len(voteList) == len(PLAYERS) - 1:
            # We have all the votes
            voteList = [int(x) for x in voteList]
            voteList.append(int(DayHandler.vote))
            print("Vote List is {} with length {}".format(voteList, len(voteList)))
            deadPlayer = max(set(voteList), key=voteList.count)
            print("This player - {} is now dead".format(PLAYERS[deadPlayer]))
            print(deadPlayer)

            if deadPlayer == ME: # you are dead!
                stage = Stage.DEAD
            LYNCHED.append(PLAYERS[deadPlayer])
            PLAYERS.pop(deadPlayer)
            if deadPlayer <= ME:
                ME -= 1
            ROUND += 1
            if (ME == 0):
                start_night_round()

    return lynch

class DayHandler(tornado.web.RequestHandler):

    vote = None

    def get(self):
        self.write(json.dumps({'vote':self.vote, 'round':ROUND, 'player': ME}, cls=EnumEncoder))

    def post(self):
        data = load_request_body(self.request.body)
        stage = json.loads(data['stage'], object_hook=as_enum)
        step = int(data['step'])

        assert stage == Stage.DAY, "Players do not agree on current stage!"

        if step == 0:
            
            cast_vote()
            time.sleep(DAY_VOTING_PERIOD)
            data = {
                'stage': json.dumps(Stage.DAY, cls=EnumEncoder),
                'step': 1
            }
            send_to_next_player('day', data, GET=False)

        elif step == 1:
            query_runner = BackgroundTaskRunner(None, QUERY_INTERVAL)
            callback = get_lynch_votes(query_runner)
            def query():
                query_endpoint(ME, PLAYERS, "day", callback = callback, check=lambda x: x['round'] == ROUND)

            query_runner.set_task(query)
            
            query_runner.start()
        else:
            print(step)
            print("WHY IS THE STEP WRONG")
            raise Exception("Invalid step!")

def start_night_round():
    # vote = input("Which player would you like to kill?")
    # print(LYNCHED+KILLED)
    # while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS) or PLAYERS[int(vote)] in LYNCHED + KILLED:
    #     print("Sorry! That input is invalid!")
    #     vote = input("Which player would you like to kill?")
    # NightHandler.vote = vote
    return
    if ROLE == Role.MAFIA:
        print(ROLE)
        print(LYNCHED+KILLED)
        vote = input("Which player would you like to kill? ")
        while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS):
            print("Sorry! That input is invalid!")
            vote = input("Which player would you like to kill? ")
        while PLAYERS[int(vote)] in LYNCHED + KILLED:
            print("These players are already dead")
            print(LYNCHED+KILLED)
            vote = input("Which player would you like to kill? ")
        NightHandler.vote = vote
    else:
        NightHandler.vote = RANDOM.randint(0, len(PLAYERS))
    data = {
        "stage": json.dumps(Stage.NIGHT, cls=EnumEncoder),
        "step": 0
    }
    send_to_next_player('night', data, GET=False)


class NightHandler(tornado.web.RequestHandler):

    vote = None

    def kill(self):
        global ME
        print("These players are already dead: ")
        print(LYNCHED + KILLED)
        # Get the votes from all the players
        voteList = query_endpoint(ME, PLAYERS, "night")
        voteList.append(int(self.vote))

        deadPlayer = max(set(voteList), key=voteList.count)
        if deadPlayer == ME: # you are dead!
            stage = Stage.DEAD
        KILLED.append(PLAYERS[deadPlayer])
        PLAYERS.pop(deadPlayer)
        if deadPlayer < ME:
            ME -= 1
        return True

    def mafia_vote(self):
        if ROLE == Role.MAFIA:
            print(ROLE)
            print(LYNCHED+KILLED)
            vote = input("Which player would you like to kill? ")
            while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS):
                print("Sorry! That input is invalid!")
                vote = input("Which player would you like to kill? ")
            while PLAYERS[int(vote)] in LYNCHED + KILLED:
                print("These players are already dead")
                print(LYNCHED+KILLED)
                vote = input("Which player would you like to kill? ")
            NightHandler.vote = vote
        else:
            NightHandler.vote = RANDOM.randint(0, len(PLAYERS))

    def get(self):
        if ROLE == Role.MAFIA:
            self.write(json.dumps(self.vote, cls=EnumEncoder))

    def post(self):
        first_player = (ME == 0)
        data = load_request_body(self.request.body)
        stage = json.loads(data['stage'], object_hook=as_enum)
        step = int(data['step'])

        assert stage == Stage.NIGHT, "Players do not agree on current stage!"

        if first_player: step += 1 # We've arrived back at the first player

        if step == 0: # In the first step, players cast their votes
            print('Step 0, I am voting')
            print(str(ME))
            self.mafia_vote()
            data = {
                'stage': json.dumps(Stage.NIGHT, cls=EnumEncoder),
                'step': step
            }
            send_to_next_player('night', data=data, GET=False)

        elif step == 1: # In this step, everyone figures out who died
            print('Step 1, I am the one who knocks')
            data = {
                'stage': json.dumps(Stage.NIGHT, cls=EnumEncoder),
                'step': step
            }
            self.kill()
            send_to_next_player('night', data=data, GET=False)

        elif step == 2: # start next step
            print("Night round has ended!")
            start_day_round()
        else:
            raise Exception("Invalid step!")

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
    @staticmethod
    def send_heartbeats():
        for i, player in enumerate(PLAYERS):
            if i == ME: continue # Don't send heartbeat to yourself
            send_to_player(player, 'heartbeat', callback=HeartbeatHandler.verify_heartbeat(i))

    @staticmethod
    def verify_heartbeat(player):
        def check_heartbeat_response(response):
            # Handle any errors
            handled = check_response_error(PLAYERS[player], request_name='Heartbeat')(response)
            # If there was an error, but it was handled continue
            if handled: return

            try:
                heartbeat = load_request_body(response.body)
                # TODO: Do something if there is disagreement
                assert heartbeat['state'] == STATE, 'Heartbeat state did not match!'
                assert heartbeat['round'] == ROUND, 'Round numbers do not match!'
                assert heartbeat['dead_players'] == LYNCHED + KILLED, 'Dead players list does not match!'
                assert heartbeat['mafia_dead'] == MAFIA_DEAD, 'Mafia dead (end condition) disagreement!'
                assert heartbeat['town_dead'] == TOWN_DEAD, 'Town dead (end condition) disagreement!'
                print('Heartbeat check for player {} successful!'.format(PLAYERS[player]))
            except json.JSONDecodeError:
                raise Exception('Problem parsing heartbeat from player {}!'.format(player))

        return check_heartbeat_response

    def get(self):
        heartbeat = {
            'state': STATE,
            'round': ROUND,
            'dead_players': LYNCHED + KILLED,
            'mafia_dead': MAFIA_DEAD,
            'town_dead': TOWN_DEAD
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

def send_to_next_player(endpoint, data=None, callback=None,
                        connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    next_player = PLAYERS[(ME + 1) % len(PLAYERS)]
    # print("SENDING TO PLAYER {}: ======================================================".format(next_player))
    # print("I am player {}".format(ME))
    # print("These are the alive players: ")
    # print(PLAYERS)
    # print("The next player is {}".format(next_player))
    # print("Sending them {}".format(data))
    # print("========================================================================")
    # if next_player == PLAYERS[ME]:
        # raise Exception("I'm so lonely...")
    send_to_player(next_player, endpoint, data, callback=callback,
                   connect_timeout=connect_timeout, request_timeout=request_timeout, GET=GET)

def send_to_all_players(endpoint, data=None, callback=None,
                        connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    # print("SENDING TO ALL PLAYERS: ======================================================")
    # print("I am player {}".format(ME))
    # print("These are the alive players: ")
    # print(PLAYERS)
    # print("Sending them {}".format(data))
    # print("========================================================================")
    for i, player in enumerate(PLAYERS):
        send_to_player(player, endpoint, data, callback=callback,
                   connect_timeout=connect_timeout, request_timeout=request_timeout, GET=GET)

def send_to_other_players(endpoint, data=None, callback=None,
                        connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT, GET=True):
    # print("SENDING TO ALL PLAYERS: ======================================================")
    # print("I am player {}".format(ME))
    # print("These are the alive players: ")
    # print(PLAYERS)
    # print("Sending them {}".format(data))
    # print("========================================================================")
    for i, player in enumerate(PLAYERS):
        if i == ME: continue
        send_to_player(player, endpoint, data, callback=callback,
                   connect_timeout=connect_timeout, request_timeout=request_timeout, GET=GET)

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
