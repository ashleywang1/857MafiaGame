import tornado.ioloop
import tornado.web
from tornado.options import parse_command_line
import requests
import json
import sys
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Util import Counter

headers = {"Content-Type":"application/json", "Upgrade": "websocket",
    "Connection": "Upgrade"}

# This should later be moved to the Config Files
serverIP = "http://18.189.63.57"
#player = [int(x) for x in raw_input("IP List: ").split(',')]
player = [8870, 8871, 8872, 8873, 8874, 8875, 8876, 8877, 8878, 8879, 8880]
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
        try:
            r = requests.get(hostname, timeout=.1)
            print(json.loads(r))
        except:
            self.write('\nPlayer {} is not in the lobby yet!\n'.format(i))

def day_round(self):
    for i in range(len(player)):
        if i == playerNum:
            continue
        hostname = serverIP + ":" + str(player[i]) + "/day"
        try:
            r = requests.get(hostname, timeout=.1)
            print(json.loads(r))
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

    def decrypt(enc_cards, key, ctr):
        # TODO: need to retrieve the ctr here?
        cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
        dec_cards = []
        for c in enc_cards:
            pt = cipher.decrypt(c)
            dec_cards.append(pt)
        return dec_cards    

    def encrypt(cards, key):
        # TODO 
        print("encrypt")
        enc_cards = []
        # iv = Random.new().read(AES.block_size)
        ctr = Counter.new(128)
        cipher = AES.new(key, AES.MODE_CTR, counter=ctr) 
        for c in cards:
            
            # TODO: is card a string? (how may byte literal)
            ct = cipher.encrypt(b'PLAINTEXT GOES HERE')
            enc_cards.append(ct)

        return enc_cards

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
        player_to_lynch = -1
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
            'mafiaAllDead':mafiaAllDead,
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
