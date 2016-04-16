import tornado.ioloop
import tornado.web
from tornado.options import parse_command_line
import requests
import json
import sys

headers = {"Content-Type":"application/json", "Upgrade": "websocket",
    "Connection": "Upgrade"}

# This should later be moved to the Config Files
serverIP = "http://localhost:"
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

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")
        print "Player " + str(playerNum) + " has joined the game!"
        data = {"stage":"start"}

        for i in range(len(player)):
			hostname = "https://localhost:" + str(player[i])
			try:
				r = requests.get(hostname + "/heartbeat/", timeout=.1)
				print r.text
			except:
				self.write('\nPlayer {} is not in the lobby yet!\n'.format(i))
			#if r != "alive":
			#	break
			#else:
			#	r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))
			#	r = requests.post("http://localhost:8871/setup/",headers=headers,data=json.dumps(data))

class SetupHandler(tornado.web.RequestHandler):
	# Player A: Encrypts list of (mafia,x), (mafia,x), (doctor,0)...Sends list to B
	# Player B: Encrypts A's encrypted cardList with secret y ......Sends Enc(cardList, y) to C
	# Player C -> N -> A: chooses one, removes it, sends to next player
	# Player A: reveal A's secret key
	# Player B: reveal B's secret key

	def encrypt(cards, key):
		# TODO
		print "encrypt"
		return cards

	def choose(cards):
		card = cards[0]

	def get(self):
		self.write("Setting up!" + str(playerNum))
        # self.get_argument('cards')
        if playerNum in [0,1]:
        	x = 0 # secret key
        	cards = [("DOCTOR",None), ("DETECTIVE",None), ("MAFIA",x), ("MAFIA",x), ("TOWNSPERSON",None), ("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None),("TOWNSPERSON",None)]
        	shuffledCards = encrypt(cards, x)
        	data = data = {"cards":shuffledCards, "stage":"shuffling"}
        	print "when" + str(playerNum) + assignment
        	requests.post(serverIP + str(player[3]) + "/setup/",headers=headers,data=json.dumps(data))
        #global assignment = "DOCTOR"
        if playerNum == 2:
        	print "Player 3 got a message: " + self.get_argument('cards')

class NightHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's night!")
        print "night"
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))

class DayHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("It's day!")
        print "day"
        #data = {"data":[]}
        
class MessageHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("No messages received!")
        print "msg"
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))

class HeartbeatHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Heartbeat")
        #data = {"data":[]}
        #r = requests.post("http://localhost:8870/setup/",headers=headers,data=json.dumps(data))

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