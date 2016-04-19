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


# print('```GENERAL```')
# print('AES block size: {0}'.format(AES.block_size))
original_key = 'This is my k\u00eay!! The extra stuff will be truncated before using it.'
original_key2 = 'this is my derpy key!! now for some random sstuff'
key = original_key.encode('utf-8')[0:32]
key2 = original_key2.encode('utf-8')[0:32]

print('Original Key: {0}'.format(original_key))
print('Usable Key: {0}'.format(key))

print('Original Key2: {0}'.format(original_key2))
print('Usable Key2: {0}'.format(key2))

print('Base64 Encoded key: {0}'.format(b64encode(key).decode('utf-8')))
message = '01234567890123456789012345678901'.encode('utf-8')
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
ctr_iv2 = int(hexlify(Random.new().read(AES.block_size)), 16)
print(len(bytes(hexlify(Random.new().read(AES.block_size)))))
print('CTR IV (int): {0}'.format(ctr_iv))
ctr_encrypt_counter = Counter.new(128, initial_value=ctr_iv)
ctr_decrypt_counter = Counter.new(128, initial_value=ctr_iv)

ctr_encrypt_counter2 = Counter.new(128, initial_value=ctr_iv2)
ctr_decrypt_counter2 = Counter.new(128, initial_value=ctr_iv2)
print()


# ENCRYPT FIRST MESSAGE
ctr_padded_message = message #ctr_pad_message(message)
print('Mode CTR, Padded message: {0}'.format(ctr_padded_message))
print('length of pt:', len(bytes(ctr_padded_message)))
ctr_cipher_encrypt = AES.new(key, AES.MODE_CTR, counter=ctr_encrypt_counter)
ctr_msg_encrypt1 = b64encode(ctr_cipher_encrypt.encrypt(ctr_padded_message))
print('ctr_msg_encrypt1', ctr_msg_encrypt1)
print('length:', len(ctr_msg_encrypt1))
print('type:', type(ctr_msg_encrypt1))

msg = ctr_msg_encrypt1[:-8]
mac = ctr_msg_encrypt1[-8:]
print(mac)
print(msg)
print('mac length:', len(mac))

print('Mode CTR, Base64 Encoded, Encrypted message: {0}'.format( ctr_msg_encrypt1.decode('utf-8')))
print()

# DECRYPT FIRST MESSAGE
ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(msg+bytes('a'.encode('utf-8')*100)))
ctr_unpadded_message = ctr_unpad_message(ctr_msg_decrypt)
print('Mode CTR, Decrypted message: {0}'.format(ctr_msg_decrypt))
print('Mode CTR, Unpadded, Decrypted message: {0}'.format(ctr_unpadded_message))
print(len(ctr_msg_decrypt))
print(len(ctr_padded_message))

# ENCRYPT SECOND MESSAGE

# padded_msg = ctr_msg_encrypt1 #ctr_pad_message(ctr_msg_encrypt1)
# print('Padded message: {0}'.format(padded_msg))
# ctr_cipher_encrypt2 = AES.new(key2, AES.MODE_CTR, counter=ctr_encrypt_counter2)
# ctr_msg_encrypt2 = b64encode(ctr_cipher_encrypt2.encrypt(padded_msg))
# print('ctr_msg_encrypt2:', ctr_msg_encrypt2)
# print(len(ctr_msg_encrypt2))
# print(type(ctr_msg_encrypt2))
# print(ctr_msg_encrypt2.decode('utf-8'))
# print('Encrypted message second layer: {0}'.format( ctr_msg_encrypt2.decode('utf-8')))
# print()


# DECRYPT COMMUTATIVE LAYER 1
# ctr_cipher_decrypt = AES.new(key2, AES.MODE_CTR, counter=ctr_decrypt_counter2)
# ctr_msg_decrypt1 = ctr_cipher_decrypt.decrypt(b64decode(ctr_msg_encrypt2))
# print('ctr_msg_decrypt1:', ctr_msg_decrypt1)
# ctr_unpadded_message1 = ctr_unpad_message(ctr_msg_decrypt1)
# # TODO: ctr_unpadded_message1 is...empty..?
# print('ctr_unpadded_message1:', ctr_unpadded_message1)
# print('Decrypted message first layer: {0}'.format(ctr_msg_decrypt1))
# # line below gives error
# print('Unpadded, Decrypted message first layer: {0}'.format(ctr_unpadded_message1))
# print()


# DECRYPT COMMUTATIVE LAYER 2
# ctr_cipher_decrypt2 = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
# ctr_msg_decrypt2 = ctr_cipher_decrypt2.decrypt(b64decode(ctr_msg_decrypt1))
# ctr_unpadded_message2 = ctr_unpad_message(ctr_msg_decrypt2)
# print('ctr_unpadded_message2:', ctr_unpadded_message2)
# print('Decrypted message second layer: {0}'.format(ctr_msg_decrypt2))
# print('Unpadded, Decrypted message second layer: {0}'.format(ctr_unpadded_message2))

# DECRYPT SECOND MESSAGE
# ctr_cipher_decrypt = AES.new(key, AES.MODE_CTR, counter=ctr_decrypt_counter)
# ctr_msg_decrypt = ctr_cipher_decrypt.decrypt(b64decode(ctr_msg_encrypt))
# ctr_unpadded_message = ctr_unpad_message(ctr_msg_decrypt)
# print('Mode CTR, Decrypted message: {0}'.format(ctr_msg_decrypt))
# print('Mode CTR, Unpadded, Decrypted message: {0}'.format(ctr_unpadded_message))


# HERE WE WILL TEST OFB MODE
key = b'Sixteen byte key'
iv = Random.new().read(AES.block_size)
cipher = AES.new(key, AES.MODE_OFB, iv)
message = b'0123456789012345'

enc_msg = iv +cipher.encrypt(message)
print(enc_msg)

dec_msg = cipher.decrypt(enc_msg)
print(dec_msg)



# key = b'Sixteen byte key'
# iv = Random.new().read(AES.block_size)
# cipher = AES.new(key, AES.MODE_CFB, iv)
# msg = iv + cipher.encrypt(b'Attack at dawn')

# msg2 = cipher.decrypt(msg)[len(iv):]

# print(msg)
# print(msg2)