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
from Crypto.Util import Counter
import requests
import tornado.ioloop
from tornado.options import parse_command_line
import tornado.web

# Local file imports
from common import *
from util import EnumEncoder, as_enum

#======================================================================
# Constants
#======================================================================
REQUEST_TIMEOUT = 0.1 # Seconds
HEADERS = {
    "Content-Type": "application/json",
    "Upgrade": "websocket",
    "Connection": "Upgrade"
}

# This should later be moved to the Config Files
SERVER_IP = socket.gethostbyname(socket.gethostname())
SERVER_URL = "http://{}".format(SERVER_IP)
#player = [int(x) for x in raw_input("IP List: ").split(',')]
PLAYERS = list(range(8870, 8880+1))
# Another possible form of the player list:
#['https://localhost:8870/', 'https://localhost:8871/', 'https://localhost:8872/', 'https://localhost:8873/', 'https://localhost:8874/', 'https://localhost:8875/', 'https://localhost:8876/', 'https://localhost:8877/', 'https://localhost:8878/', 'https://localhost:8879/', 'https://localhost:8880/']

# TODO: Make this variable with number of players
ROLE_DISTRIBUTION = {
    Role.DETECTIVE: 1,
    Role.DOCTOR: 1,
    Role.MAFIA: 2,
    Role.TOWNSPERSON: 6
}

# Settings for each player
ME = -1
ROLE = None # Mafia, Townsperson, Doctor, Detective

# Mafia settings
MAFIA = False
MAFIA_SECRET_KEY = None #secret key for mafia_channel

# Hearbeat settings
STATE = Stage.SETUP
ROUND = 0
LYNCHED = []
KILLED = []

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
        except Exception:
            self.write("\nPlayer {} is not in the lobby yet!\n".format(i))

def day_round(self):
    for i, player in enumerate(PLAYERS):
        if i == ME: continue

        hostname = SERVER_URL + ":" + str(player) + "/day"
        try:
            r = requests.get(hostname, timeout=REQUEST_TIMEOUT)
            #print(json.loads(r.text))
        except Exception:
            self.write("\nPlayer {} has no response!\n".format(i))


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
        self.write("Welcome to the Mafia Game Lobby!")
        print("Player {} has joined the game!".format(ME))
        data = {"stage": Stage.INITIALIZATION}

        # Hearbeat
        heartbeat(self)
        day_round(self)
        night_round(self)
        #r = requests.post("http://localhost:8870/setup/",headers=HEADERS,data=json.dumps(data))
        #r = requests.post("http://localhost:8871/setup/",headers=HEADERS,data=json.dumps(data))

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
        dec_cards = []

        # if(not(ctr_decrypt_counter)):
        ctr_decrypt_counter = Counter.new(128, initial_value=ctr_iv)

        for c in enc_cards:
            ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
            ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(c))
            ctr_unpadded_message = self.ctr_unpad_message(ctr_msg_decrypt)
            dec_cards.append(ctr_unpadded_message)

        return dec_cards

    def encrypt(self, cards, key):
        print("encrypt")
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

    def ctr_pad_message(self, in_message):
        # http://stackoverflow.com/questions/14179784/python-encrypting-with-pycrypto-aes
        # We use PKCS7 padding
        length = 16 - (len(in_message) % 16)
        return (in_message + bytes([length])*length)

    def ctr_unpad_message(self, in_message):
        return in_message[:-in_message[-1]]

    def choose(self, cards):
        index = Random.random.randint(0, len(cards)-1)
        return index, cards[index]

    def get(self):
        self.write("Setting up for player {}".format(ME))

        if ME in [0,1]:
            x = 0 # TODO: secret key
            cards = [(Role.MAFIA, x)] * ROLE_DISTRIBUTION[Role.MAFIA]
            cards.extend([(Role.TOWNSPERSON, None)] * ROLE_DISTRIBUTION[Role.TOWNSPERSON])
            cards.extend([(Role.DETECTIVE, None)] * ROLE_DISTRIBUTION[Role.DETECTIVE])
            cards.extend([(Role.DOCTOR, None)] * ROLE_DISTRIBUTION[Role.DOCTOR])

            # Stringify the list items in preparation for encryption
            stringified_cards = [json.dumps(card, cls=EnumEncoder) for card in cards]
            shuffled_cards = Random.random.shuffle(self.encrypt(stringified_cards, x))
            data = {"cards": shuffled_cards, "stage": Stage.SHUFFLING}
            print("when" + str(ME) + ROLE)

            post_url = "{server_url}:{player}/setup".format(server_url=SERVER_URL, player=PLAYERS[3])
            requests.post(post_url, headers=HEADERS, data=json.dumps(data))
        elif ME == 2:
            print("Player 3 got a message: " + self.get_argument('cards'))

class NightHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's night!")
        print("night")
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=HEADERS,data=json.dumps(data))

class DayHandler(tornado.web.RequestHandler):
    def lynch(self, player):
        if player == ME:
            # you are dead!
            stage = Stage.DEAD
        LYNCHED.append(player)

    def get(self):
        self.write("It's day!")
        print("day")
        player_to_lynch = str(-1)
        self.write(player_to_lynch)

        #data = {"data":[]}

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
        self.write(json.dumps(heartbeat, cls=EnumEncoder))

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/setup", SetupHandler),
        (r"/night", NightHandler),
        (r"/day", DayHandler),
        (r"/message", MessageHandler),
        (r"/heartbeat", HeartbeatHandler)
    ])

# FIXME: Implement me :D
def verify_hearbeat(heartbeat):
    pass

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
    # start the mafia server
    port = PLAYERS[ME]
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
