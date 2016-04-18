import tornado.ioloop
import tornado.web
from tornado.options import parse_command_line
import socket
import requests
import json
import sys
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Util import Counter
from binascii import hexlify

headers = {"Content-Type":"application/json", "Upgrade": "websocket",
    "Connection": "Upgrade"}

# This should later be moved to the Config Files
serverIP = "http://{}".format(socket.gethostname())
#player = [int(x) for x in raw_input("IP List: ").split(',')]
player = list(range(8870, 8880+1))
# Another possible form of the player list:
#['https://localhost:8870/', 'https://localhost:8871/', 'https://localhost:8872/', 'https://localhost:8873/', 'https://localhost:8874/', 'https://localhost:8875/', 'https://localhost:8876/', 'https://localhost:8877/', 'https://localhost:8878/', 'https://localhost:8879/', 'https://localhost:8880/']

# Settings for each player
playerNum = -1
assignment = "" # Mafia, Townsperson, Doctor, Detective

# Mafia settings
MAFIA = False
mafia_secret_key = None #secret key for mafia_channel

# Hearbeat settings
state = "SETUP" #"DAY", "NIGHT"
roundNum = 0
lynched = []
killed = []

def heartbeat(self):
    for i in range(len(player)):
        if i == playerNum:
            continue
        hostname = serverIP + ":" + str(player[i]) + "/heartbeat"
        print(hostname)
        try:
            r = requests.get(hostname, timeout=.1)
            print(json.loads(r.text))
        except:
            self.write('\nPlayer {} is not in the lobby yet!\n'.format(i))

def day_round(self):
    for i in range(len(player)):
        if i == playerNum:
            continue
        hostname = serverIP + ":" + str(player[i]) + "/day"
        try:
            r = requests.get(hostname, timeout=.1)
            #print(json.loads(r.text))
        except:
            self.write('\nPlayer {} has no response!\n'.format(i))


def night_round(self):
    for i in range(len(player)):
        if i == playerNum:
            continue
        hostname = serverIP + ":" + str(player[i]) + "/night"
        try:
            r = requests.get(hostname, timeout=.1)
            print(json.loads(r))
        except:
            pass


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Welcome to the Mafia Game Lobby!")
        print("Player " + str(playerNum) + " has joined the game!")
        data = {"stage":"start"}

        # Hearbeat
        heartbeat(self)
        day_round(self)
        night_round(self)
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))
        #r = requests.post("http://localhost:8871/setup/",headers=headers,data=json.dumps(data))

class SetupHandler(tornado.web.RequestHandler):
    # Player A: Encrypts list of (mafia,x), (mafia,x), (doctor,0)...Sends list to B
    # Player B: Encrypts A's encrypted cardList with secret y ......Sends Enc(cardList, y) to C
    # Player C -> N -> A: chooses one, removes it, sends to next player
    # Player A: reveal A's secret key
    # Player B: reveal B's secret key

    ctr_decrypt_counter = None;
    ctr_encrypt_counter = None;

    def encrypting_setup():
        # TODO: determine best way to make the key

        original_key = 'This is my k\u00eay!! The extra stuff will be truncated before using it.'
        key = original_key.encode('utf-8')[0:32]

        # message = '0123456789'.encode('utf-8')



    def decrypt(enc_cards, key):
        dec_cards = []

        # if(not(ctr_decrypt_counter)): 
        ctr_decrypt_counter = Counter.new(128, initial_value=ctr_iv)

        for c in enc_cards:
            ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
            ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(c))
            ctr_unpadded_message = ctr_unpad_message(ctr_msg_decrypt)

            dec_cards.append(ctr_unpad_message)

        return dec_cards

    def encrypt(cards, key):
        print("encrypt")
        enc_cards = []

        ctr_iv = int(hexlify(Random.new().read(AES.block_size)), 16)
        ctr_encrypt_counter = Counter.new(128, initial_value=ctr_iv)

        for c in cards:
            message = c.encode('utf-8')
            ctr_padded_message = ctr_pad_message(message)
            ctr_padded_message = ctr_pad_message(c)
            ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
            ctr_msg_encrypt = b64encode(ctr_cipher_encrypt.encrypt(ctr_padded_message))
            enc_cards.append(ctr_msg_encrypt)

        return enc_cards

    def ctr_pad_message(in_message):
        # http://stackoverflow.com/questions/14179784/python-encrypting-with-pycrypto-aes
        # We use PKCS7 padding
        length = 16 - (len(in_message) % 16)
        return (in_message + bytes([length])*length)

    def ctr_unpad_message(in_message):
        return in_message[:-in_message[-1]]

    def choose(cards):
        card = cards[0]

    def get(self):
        self.write("Setting up for player " + str(playerNum))

        if playerNum in [0,1]:
            x = 0 # TODO: secret key
            cards = [("DOCTOR",None), ("DETECTIVE",None), ("MAFIA",x), ("MAFIA",x), ("TOWNSPERSON",None), ("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None)]
            shuffledCards = encrypt(cards, x)
            data = data = {"cards":shuffledCards, "stage":"shuffling"}
            print("when" + str(playerNum) + assignment)
            requests.post(serverIP + str(player[3]) + "/setup/",headers=headers,data=json.dumps(data))
        #global assignment = "DOCTOR"
        if playerNum == 2:
            print("Player 3 got a message: " + self.get_argument('cards'))

class NightHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's night!")
        print("night")
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))

class DayHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("It's day!")
        print("day")

    def lynch(player):
        if player == playerNum:
            # you are dead!
            stage = "DEAD"
        lynched.append(player)
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
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))

class HeartbeatHandler(tornado.web.RequestHandler):
    # synchronize state = {Day, Night, Setup}
    # synchronize roundNum = 0 to numPlayers at most
    # synchronize deadPlayers = {lynched[], killed[]}
    # synchronize mafiaAllDead = False, True
    # synchronize townspeopleAllDead = False,True
    def get(self):
        heartbeat = {
            'state':state,
            'round':roundNum,
            'deadPlayers':lynched + killed,
            'mafiaAllDead':False,
            'townspeopleAllDead':False
        }
        self.write(json.dumps(heartbeat))

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/setup", SetupHandler),
        (r"/night", NightHandler),
        (r"/day", DayHandler),
        (r"/message", MessageHandler),
        (r"/heartbeat", HeartbeatHandler)
    ])

if __name__ == "__main__":
    # Run server with python mafia.py 'list of player ips' 'playerNum'
        # ex: python mafia.py '8871, 8872, 8873, 8874, 8875, 8876, 8877, 8878, 8879, 8880' 0
    app = make_app()
    argv = parse_command_line(sys.argv)
    if len(argv) != 2:
        raise ValueError("Please run server with arguments 'list of player ips' 'playerNum'")
    # set global variables
    player = [int(x) for x in argv[0].split(',')]
    playerNum = int(argv[1])
    # start the mafia server
    port = player[playerNum]
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
