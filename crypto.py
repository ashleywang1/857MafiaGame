"""
Local cryptography module for use in different protocols.
"""

import os
from base64 import encodebytes, decodebytes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric.dh import *
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet



ENCODING = 'UTF-8'

class CommutativeCipher:
    """
    Encryption and decryption using a commutative cipher.
    """
    def __init__(self):
        key = os.urandom(32)
        iv = os.urandom(16)
        self.cipher = Cipher(algorithms.AES(key), modes.OFB(iv), backend=default_backend())


    def encrypt(self, plaintext, base64=False):
        """
        Encrypts a plaintext message and returns base 64 encoded ciphertext.
        If base64 is specified, decodes from base64 first.
        """
        plaintext = plaintext.encode(ENCODING)
        if base64: plaintext = decodebytes(plaintext)

        encryptor = self.cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return encodebytes(ciphertext).decode(ENCODING)

    def decrypt(self, ciphertext, base64=False):
        """
        Decrypts base 64 encoded ciphertext and returns the plaintext message.

        If base64 is specified, provides result base64 encoded.
        """
        ciphertext = decodebytes(ciphertext.encode(ENCODING))

        decryptor = self.cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        if base64: plaintext = encodebytes(plaintext)
        return plaintext.decode(ENCODING)


# TODO: Figure out how to set this up (assuming we plan to use g idea for mafia protocol)
class DiffieHellman:
    """
    A Diffie-Hellman setup.
    """

    def __init__(self, p, g, y, x):
        self.parameter_numbers = DHParameterNumbers(p, g)
        self.pub_numbers = DHPublicNumbers(y, self.parameter_numbers)
        self.priv_numbers = DHPrivateNumbers(x, self.pub_numbers)
        self.private_key = DHParameters.generate_private_key() #this is None

    def get_private_key(self):
        return self.private_key


class SymmetricCrypto:
    """
    Encryption and decryption using Fernet scheme
    """

    def __init__(self, key):
        self.fernet = Fernet(key)

    def encrypt(self, plaintext):
        """
        Encrypts a plaintext message and returns a token
        """
        return self.fernet.encrypt(plaintext.encode('UTF-8'))

    def decrypt(self, token):
        """
        Decrypts a given token into a plaintext message
        """
        return self.fernet.decrypt(token)


# Testing stuff
if __name__ == '__main__':
    pass
