"""
Local cryptography module for use in different protocols.
"""

import os
from base64 import encodebytes, decodebytes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.backends import default_backend

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

    def __init__(self):
        pass
