#!/usr/bin/env python
"""
PyDHE - Diffie-Hellman Key Exchange in Python
Copyright (C) 2015 by Mark Loiseau

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


#===============================================================================
# Modified for use in 857Mafia
#===============================================================================

import hashlib
from binascii import hexlify # For debug output

# If a secure random number generator is unavailable, exit with an error.
try:
	import ssl
	random_function = ssl.RAND_bytes
	random_provider = "Python SSL"
except (AttributeError, ImportError):
	import OpenSSL
	random_function = OpenSSL.rand.bytes
	random_provider = "OpenSSL"

class DiffieHellman(object):
	"""
	A reference implementation of the Diffie-Hellman protocol.
	By default, this class uses the 6144-bit MODP Group (Group 17) from RFC 3526.
	This prime is sufficient to generate an AES 256 key when used with
	a 540+ bit exponent.
	"""

	def __init__(self, generator=2, group=17, keyLength=540):
		"""
		Generate the public and private keys.
		"""
		
		#min_keyLength = 180
		#default_keyLength = 540

		default_generator = 2
		valid_generators = [ 2, 5] #not sure what other generatos openSSL uses

		# Sanity check fors generator and keyLength
		if(generator not in valid_generators):
		    print("Error: Invalid generator. Using default.")
		    self.generator = default_generator
		else:
			self.generator = generator

		#if(keyLength < min_keyLength):
		#	print("Error: keyLength is too small. Setting to minimum.")
		#	self.keyLength = min_keyLength
		#else:
		#	self.keyLength = keyLength

		self.prime = self.genPrime()

		self.privateKey = self.genPrivateKey(keyLength)
		self.publicKey = self.genPublicKey()

	def getPrime(self):
		"""
		Returns safe-prime.
		"""
		return self.prime
		
	def genPrime(self):
	    """
	    Generates a new safe-prime through openssl
	    """
	    # TODO: generate safe prime here
	    
	    prime = "00:ea:44:3a:64:04:59:64:58:b2:bc:4f:4a:89:ad: \
            4e:31:1a:ed:98:b9:a1:fe:7f:2b:c0:6f:85:d6:65: \
            08:9b:da:0d:b5:cd:02:07:23:21:c0:54:98:0d:19: \
            82:7f:3d:f1:cd:e1:9c:71:1d:fb:28:c3:72:bf:8d: \
            06:97:08:39:8e:7f:7b:bd:7a:04:40:b4:98:1b:9b: \
            42:45:a8:29:b5:05:d9:ee:fa:18:50:73:de:bd:dd: \
            56:18:0d:d6:01:f5:ad:fd:7a:8d:b6:36:f5:e2:69: \
            3a:03:b7:10:30:ca:35:ba:f8:b3:f4:62:7d:4e:fe:\
            86:59:28:a6:9e:a0:76:62:ff:70:af:52:31:76:ef:\
            bd:cb:4d:96:6a:d6:49:d0:e6:95:11:3a:d5:55:13:\
            39:3b:2e:18:48:a3:2e:72:47:c8:a2:25:88:c4:13:\
            c4:14:06:67:07:c2:d9:f4:f6:90:99:36:c2:32:0d:\
            b5:91:c3:51:b0:99:6a:ad:2f:01:e6:ef:ec:89:f9:\
            02:14:ae:dc:f4:77:81:9a:e1:10:29:e3:db:76:2f:\
            03:6c:57:31:c8:f2:e8:7f:74:b8:82:18:bb:f5:ed:\
            4b:b9:bc:43:b1:63:48:a9:35:79:ca:73:72:be:ca:\
            48:4d:de:bb:9b:d8:3f:fd:01:c3:f5:1d:55:0e:dc:\
            97:5b"
	    
	    print('string prime:', prime)
	    
	    pass
		

	def genRandom(self, bits):
		"""
		Generate a random number with the specified number of bits
		"""
		_rand = 0
		_bytes = bits // 8 + 8

		while(_rand.bit_length() < bits):
			try:
				# Python 3
				_rand = int.from_bytes(random_function(_bytes), byteorder='big')
			except:
				# Python 2
				_rand = int(OpenSSL.rand.bytes(_bytes).encode('hex'), 16)

		return _rand

	def genPrivateKey(self, bits):
		"""
		Generate a private key using a secure random number generator.
		"""
		return self.genRandom(bits)

	def genPublicKey(self):
		"""
		Generate a public key X with g**x % p.
		"""
		return pow(self.generator, self.privateKey, self.prime)

	def checkPublicKey(self, otherKey):
		"""
		Check the other party's public key to make sure it's valid.
		Since a safe prime is used, verify that the Legendre symbol == 1
		"""
		if(otherKey > 2 and otherKey < self.prime - 1):
			if(pow(otherKey, (self.prime - 1)//2, self.prime) == 1):
				return True
		return False

	def genSecret(self, privateKey, otherKey):
		"""
		Check to make sure the public key is valid, then combine it with the
		private key to generate a shared secret.
		"""
		if(self.checkPublicKey(otherKey) == True):
			sharedSecret = pow(otherKey, privateKey, self.prime)
			return sharedSecret
		else:
			raise Exception("Invalid public key.")

	def genKey(self, otherKey):
		"""
		Derive the shared secret, then hash it to obtain the shared key.
		"""
		self.sharedSecret = self.genSecret(self.privateKey, otherKey)

		# Convert the shared secret (int) to an array of bytes in network order
		# Otherwise hashlib can't hash it.
		try:
			_sharedSecretBytes = self.sharedSecret.to_bytes(
				self.sharedSecret.bit_length() // 8 + 1, byteorder="big")
		except AttributeError:
			_sharedSecretBytes = str(self.sharedSecret)

		s = hashlib.sha256()
		s.update(bytes(_sharedSecretBytes))
		self.key = s.digest()

	def getKey(self):
		"""
		Return the shared secret key
		"""
		return self.key

	def showParams(self):
		"""
		Show the parameters of the Diffie Hellman agreement.
		"""
		print("Parameters:")
		print("Prime[{0}]: {1}".format(self.prime.bit_length(), self.prime))
		print("Generator[{0}]: {1}\n".format(self.generator.bit_length(),
			self.generator))
		print("Private key[{0}]: {1}\n".format(self.privateKey.bit_length(),
			self.privateKey))
		print("Public key[{0}]: {1}".format(self.publicKey.bit_length(),
			self.publicKey))

	def showResults(self):
		"""
		Show the results of a Diffie-Hellman exchange.
		"""
		print("Results:")
		print("Shared secret[{0}]: {1}".format(self.sharedSecret.bit_length(),
			self.sharedSecret))
		print("Shared key[{0}]: {1}".format(len(self.key), hexlify(self.key)))

if __name__=="__main__":
	"""
	Run an example Diffie-Hellman exchange
	"""
	a = DiffieHellman()
	b = DiffieHellman()

	a.genKey(b.publicKey)
	b.genKey(a.publicKey)

	#a.showParams()
	#a.showResults()
	#b.showParams()
	#b.showResults()

	if(a.getKey() == b.getKey()):
		print("Shared keys match.")
		print("Key:", hexlify(a.key))
	else:
		print("Shared secrets didn't match!")
		print("Shared secret A: ", a.genSecret(b.publicKey))
		print("Shared secret B: ", b.genSecret(a.publicKey))

