from Crypto.Cipher import AES
from Crypto import Random
from base64 import b64encode, b64decode
from Crypto.Util import Counter
from binascii import hexlify

class Cryptography(object):
    def __init__(self):

        # TODO: need to create a random key
        original_key = 'This is my k\u00eay!! The extra stuff will be truncated before using it.'
        self.key = original_key.encode('utf-8')[0:32]

        self.ctr_iv = int(hexlify(Random.new().read(AES.block_size)), 16)
        self.ctr_decrypt_counter = Counter.new(128, initial_value=self.ctr_iv)
        self.ctr_encrypt_counter = Counter.new(128, initial_value=self.ctr_iv)

        self.ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
        self.ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
        

    def encrypt(plaintext):
        message = plaintext.encode('utf-8')
        ctr_padded_message = self.ctr_pad_message(message)
        ctr_msg_encrypt = b64encode(ctr_cipher_encrypt.encrypt(ctr_padded_message))

    def decrypt(ciphertext):
        ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(ciphertext))
        ctr_unpadded_message = self.ctr_unpad_message(ctr_msg_decrypt)

    def ctr_pad_message(self, in_message):
        # http://stackoverflow.com/questions/14179784/python-encrypting-with-pycrypto-aes
        # We use PKCS7 padding
        length = 16 - (len(in_message) % 16)
        return (in_message + bytes([length])*length)

    def ctr_unpad_message(self, in_message):
        return in_message[:-in_message[-1]]


print('```GENERAL```')
print('AES block size: {0}'.format(AES.block_size))
original_key = 'This is my k\u00eay!! The extra stuff will be truncated before using it.'
key = original_key.encode('utf-8')[0:32]
print('Original Key: {0}'.format(original_key))
print('Usable Key: {0}'.format(key))
print('Base64 Encoded key: {0}'.format(b64encode(key).decode('utf-8')))
message = '0123456789'.encode('utf-8')
print('Original Message: {0}'.format(message))

# MODE CTR
print('```MODE CTR```')
def ctr_pad_message(in_message):
    # http://stackoverflow.com/questions/14179784/python-encrypting-with-pycrypto-aes
    # We use PKCS7 padding
    length = 16 - (len(in_message) % 16)
    return (in_message + bytes([length])*length)
def ctr_unpad_message(in_message):
    return in_message[:-in_message[-1]]


ctr_iv = int(hexlify(Random.new().read(AES.block_size)), 16)
print('CTR IV (int): {0}'.format(ctr_iv))
ctr_encrypt_counter = Counter.new(128, initial_value=ctr_iv)
ctr_decrypt_counter = Counter.new(128, initial_value=ctr_iv)


# ENCRYPT FIRST MESSAGE
ctr_padded_message = ctr_pad_message(message)
print('Mode CTR, Padded message: {0}'.format(ctr_padded_message))
ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
ctr_msg_encrypt = b64encode(ctr_cipher_encrypt.encrypt(ctr_padded_message))
print('Mode CTR, Base64 Encoded, Encrypted message: {0}'.format( ctr_msg_encrypt.decode('utf-8')))


# DECRYPT FIRST MESSAGE
ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(ctr_msg_encrypt))
ctr_unpadded_message = ctr_unpad_message(ctr_msg_decrypt)
print('Mode CTR, Decrypted message: {0}'.format(ctr_msg_decrypt))
print('Mode CTR, Unpadded, Decrypted message: {0}'.format(ctr_unpadded_message))

# ENCRYPT SECOND MESSAGE
new_msg = 'derpy message'.encode('utf-8')
padded_msg = ctr_pad_message(new_msg)
print('Mode CTR, Padded message: {0}'.format(padded_msg))
ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
ctr_msg_encrypt = b64encode(ctr_cipher_encrypt.encrypt(padded_msg))
print('Mode CTR, Base64 Encoded, Encrypted message: {0}'.format( ctr_msg_encrypt.decode('utf-8')))

# DECRYPT SECOND MESSAGE
ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(ctr_msg_encrypt))
ctr_unpadded_message = ctr_unpad_message(ctr_msg_decrypt)
print('Mode CTR, Decrypted message: {0}'.format(ctr_msg_decrypt))
print('Mode CTR, Unpadded, Decrypted message: {0}'.format(ctr_unpadded_message))


