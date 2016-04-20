"""
Mafia Game Startup File
"""

# Standard library imports
from base64 import b64encode, b64decode
from binascii import hexlify
import json
import socket
import sys

# External dependencies
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Random import random
from Crypto.Util import Counter
import requests
import tornado.ioloop
from tornado.options import parse_command_line
import tornado.web

# Local file imports
from common import *
from util import EnumEncoder, as_enum

#======================================================================
# DUMMY TEMPORARY FUNCTIONS
# TODO: Remove once crypto module is ready
#======================================================================
def encrypt(text):
    print("encrypting")
    return text

def decrypt(text):
    print("decrypting")
    return text
#======================================================================

#======================================================================
# Global State + Constants
#======================================================================
REQUEST_TIMEOUT = 1 # Seconds
HEADERS = {
    "Content-Type": "application/json",
    "Upgrade": "websocket",
    "Connection": "Upgrade"
}

# This should later be moved to the Config Files
SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_URL = "http://{}".format(SERVER_IP)
PLAYERS = list(range(8870, 8880+1))

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

# Heartbeat settings
STATE = Stage.INITIALIZATION
ROUND = 0
LYNCHED = []
KILLED = []
def get_state():
    return STATE

def change_state(state):
    STATE = state

def get_round():
    return ROUND

# def change_round():
#     ROUND += 1

# def get_lynched():
#     return LYNCHED

# def lynch(player):
#     LYNCHED.append(player)

# def get_killed():
#     return KILLED

# def kill(player):
#     KILLED.append(player)

#======================================================================

def heartbeat(self):
    for i, player in enumerate(PLAYERS):
        if i == ME: continue # Don't send heartbeat to yourself

        hostname = SERVER_URL + ":" + str(player) + "/heartbeat"
        print(hostname)
        try:
            r = requests.get(hostname, timeout=REQUEST_TIMEOUT)
            heartbeat = json.loads(r.text, object_hook=as_enum)
            print(heartbeat)
            verify_hearbeat(heartbeat)
            return heartbeat
        except Exception:
            self.write("\nPlayer {} is not in the lobby yet!\n".format(i))

def night_round(self):
    for i, player in enumerate(PLAYERS):
        if i == ME: continue

        hostname = SERVER_URL + ":" + str(player) + "/night"
        try:
            r = requests.get(hostname, timeout=REQUEST_TIMEOUT)
            print(json.loads(r))
        except Exception:
            pass

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        hb = heartbeat(self)
        STATE = hb['state']
        if STATE == Stage.INITIALIZATION:
            print("Welcome to the Mafia Game Lobby!")
            print("Player {} has joined the game!".format(ME))
            # Start the setup process if first player
            if ME == 0: setup(self)

def setup(self):
    x = 0 # TODO: secret key
    cards = [{"card": (Role.MAFIA, x), "taken": False}] * ROLE_DISTRIBUTION[Role.MAFIA]
    cards.extend([{"card": (Role.TOWNSPERSON, None), "taken": False}] * ROLE_DISTRIBUTION[Role.TOWNSPERSON])
    cards.extend([{"card": (Role.DETECTIVE, None), "taken": False}] * ROLE_DISTRIBUTION[Role.DETECTIVE])
    cards.extend([{"card": (Role.DOCTOR, None), "taken": False}] * ROLE_DISTRIBUTION[Role.DOCTOR])

    # Stringify the list items in preparation for encryption
    encrypted_cards = [{
        "card": (encrypt(json.dumps(block["card"], cls=EnumEncoder))),
        "taken": block["taken"]
    } for block in cards]
    random.shuffle(encrypted_cards)
    data = {
        "cards": json.dumps(encrypted_cards, cls=EnumEncoder),
        "stage": json.dumps(Stage.SETUP, cls=EnumEncoder),
        "step": 0
    }
    print("when {} {}".format(ME, ROLE))
    send_to_next_player('setup', data, GET=False)

class SetupHandler(tornado.web.RequestHandler):
    # Player A: Encrypts list of (mafia,x), (mafia,x), (doctor,0)...Sends list to B
    # Player B: Encrypts A's encrypted cardList with secret y ......Sends Enc(cardList, y) to C
    # Player C -> N -> A: chooses one, removes it, sends to next player
    # Player A: reveal A's secret key
    # Player B: reveal B's secret key

    ctr_decrypt_counter = None;
    ctr_encrypt_counter = None;

    def encrypting_setup(self):
        # TODO: determine best way to make the key

        original_key = 'This is my k\u00eay!! The extra stuff will be truncated before using it.'
        key = original_key.encode('utf-8')[0:32]
        # message = '0123456789'.encode('utf-8')


    def decrypt(self, enc_cards, key):
        print("decrypting")
        dec_cards = []

        #if(not(ctr_decrypt_counter)):
        ctr_decrypt_counter = Counter.new(128, initial_value=ctr_iv)

        for c in enc_cards:
            ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
            ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(c))
            ctr_unpadded_message = self.ctr_unpad_message(ctr_msg_decrypt)
            dec_cards.append(ctr_unpadded_message)

        return dec_cards

    def encrypt(self, cards, key):
        print("encrypting")
        enc_cards = []

        ctr_iv = int(hexlify(Random.new().read(AES.block_size)), 16)
        ctr_encrypt_counter = Counter.new(128, initial_value=ctr_iv)

        for c in cards:
            message = c.encode('utf-8')
            ctr_padded_message = self.ctr_pad_message(message)
            ctr_padded_message = self.ctr_pad_message(c)
            ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
            ctr_msg_encrypt = b64encode(ctr_cipher_encrypt.encrypt(ctr_padded_message))
            enc_cards.append(ctr_msg_encrypt)

        return enc_cards


    def post(self):
        cards = json.loads(self.get_body_argument("cards"), object_hook=as_enum)
        stage = json.loads(self.get_body_argument("stage"), object_hook=as_enum)
        step = int(self.get_body_argument("step"))

        assert stage == Stage.SETUP, "Players do not agree on current stage!"
        # STATE = Stage.SETUP
        change_state(Stage.SETUP)

        # Cards have reached first player again
        if ME == 0: step += 1

        # In first step, all players encrypt one card
        if step == 0:
            available_card_indices = [i for i, block in enumerate(cards) if not block["taken"]]
            index = random.choice(available_card_indices)
            cards[index]["card"] = encrypt(cards[index]["card"])
            cards[index]["taken"] = True
            random.shuffle(cards)

            data = {
                "cards": json.dumps(cards, cls=EnumEncoder),
                "stage": json.dumps(Stage.SETUP, cls=EnumEncoder),
                "step": step
            }
            send_to_next_player('setup', data, GET=False)

        # In second step, all players decrypt everything and get the plaintext card
        elif step == 1:
            my_card_index = -1
            for i, block in enumerate(cards):
                decrypted_card = json.loads(decrypt(block["card"]), object_hook=as_enum)
                if isinstance(decrypted_card[0], Role):
                    ROLE, MAFIA_SECRET_KEY = decrypted_card
                    print(ME, ROLE)
                    my_card_index = i
                    break

            if my_card_index == -1: raise Exception("No valid plaintext card found!")

            # Remove my card from the card list
            cards.pop(my_card_index)
            data = {
                "cards": json.dumps(cards, cls=EnumEncoder),
                "stage": json.dumps(Stage.SETUP, cls=EnumEncoder),
                "step": step
            }
            send_to_next_player('setup', data, GET=False)

        # Setup process done!
        elif step == 2:
            print("Setup process done!")
            # TODO: Continue on to next step
            start_day_round()

        else:
            raise Exception("Invalid step!")

def start_day_round():
    vote = input("Which player would you like to kill?")
    while not vote.isdigit() or int(vote) < 0 or int(vote) >= 10 or PLAYERS[int(vote)] in LYNCHED + KILLED:
        print("Sorry! That input is invalid!")
        vote = input("Which player would you like to kill?")
    DayHandler.vote = vote
    data = {
        "stage": json.dumps(Stage.DAY, cls=EnumEncoder),
        "step": 0
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

    def vote(self):
        vote = input("Which player would you like to kill?")
        while not vote.isdigit() or int(vote) < 0 or int(vote) >= len(PLAYERS) or PLAYERS[int(vote)] in LYNCHED + KILLED:
            print("Sorry! That input is invalid!")
            vote = input("Which player would you like to kill?")
        DayHandler.vote = vote

    def get(self):
        self.write(json.dumps(self.vote, cls=EnumEncoder))

    def post(self):
        print("It's day! It's time for lynching!\n")
        stage = json.loads(self.get_body_argument("stage"), object_hook=as_enum)
        step = int(self.get_body_argument("step"))

        assert stage == Stage.DAY, "Players do not agree on current stage!"

        # Voting has reached first player again
        if ME == 0: step += 1

        if step == 0: # In the first step, players cast their votes
            self.vote()
            data = {
                "stage": json.dumps(Stage.DAY, cls=EnumEncoder),
                "step": step
            }
            send_to_next_player('day', data, GET=False)
            
        elif step == 1: # In this step, everyone figures out who died
            data = {
                "stage": json.dumps(Stage.DAY, cls=EnumEncoder),
                "step": step
            }
            self.lynch()
            send_to_next_player('day', data, GET=False)
        
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
        self.write("No messages received!")
        print("msg")
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=HEADERS,data=json.dumps(data))

class HeartbeatHandler(tornado.web.RequestHandler):
    # synchronize STATE = {Day, Night, Setup}
    # synchronize ROUND = 0 to numPlayers at most
    # synchronize deadPlayers = {LYNCHED[], KILLED[]}
    # synchronize mafiaAllDead = False, True
    # synchronize townspeopleAllDead = False,True

    def get(self):
        heartbeat = {
            'state': STATE,
            'round': ROUND,
            'deadPlayers': LYNCHED + KILLED,
            'mafiaAllDead': False,
            'townspeopleAllDead': False
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

# FIXME: Implement me :D
def verify_hearbeat(heartbeat):
    pass

def send_to_next_player(endpoint, data, timeout=REQUEST_TIMEOUT, GET=True):
    url = "{server_url}:{next_player}/{endpoint}".format(
        server_url=SERVER_URL,
        next_player=PLAYERS[(ME + 1) % len(PLAYERS)],
        endpoint=endpoint
    )

    try:
        if GET: return requests.get(url, data=data, timeout=timeout)
        return requests.post(url, data=data, timeout=timeout)
    except requests.exceptions.ReadTimeout:
        pass # TODO: Do something about timeouts?

if __name__ == "__main__":
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
    assert NUM_ROLES == NUM_PLAYERS, "{} roles but {} players!".format(NUM_ROLES, NUM_PLAYERS)

    # start the mafia server
    port = PLAYERS[ME]
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
