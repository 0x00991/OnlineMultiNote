from Crypto.Cipher import AES
import hashlib
import os
class EncryptEngine:
    def __init__(self, key) -> None:
        if not type(key) in [bytes, str]:
            raise ValueError("key: only str, byte types are accepted")
        key_length = 32
        
        if len(key) > key_length:
            raise ValueError("Key is too long! ( >= 32)")
        if type(key) == str:
            while len(key) < key_length:
                key += "0"

            self.key = key.encode("utf-8")
            
        elif type(key) != bytes:
            raise ValueError("key must be bytes or str.")
        
        else:
            if len(key) != key_length:
                raise ValueError("byte key length is must be 32 bytes.")
            
            self.key = key
    
    def write_file(self, filename, ciphertext, tag, nonce):
        with open(filename, "wb") as f:
            [ f.write(x) for x in (nonce, tag, ciphertext) ]

    def encrypt(self, data: bytes):

        cipher = AES.new(self.key, AES.MODE_EAX)

        ciphertext, tag = cipher.encrypt_and_digest(data)

        return ciphertext, tag, cipher.nonce

    def decrypt(self, ciphertext):
        if not type(ciphertext) in [bytes, str]:
            raise ValueError("only str, byte types are accepted")
            
        if type(ciphertext) == str:
            encfile = open(ciphertext, "rb")
            nonce, tag, ciphertext = [ encfile.read(x) for x in (16, 16, -1) ]
            encfile.close()

            cipher = AES.new(self.key, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)
            return data
        nonce = ciphertext[:16]
        tag = ciphertext[16:32]
        ciphertext = ciphertext[32:]
        cipher = AES.new(self.key, AES.MODE_EAX, nonce)
        data = cipher.decrypt_and_verify(ciphertext, tag)
        return data
def blank(text):
    if isinstance(text, str):
        return len(text.replace(" ", "")) == 0
    elif isinstance(text, bytes):
        return len(text.replace(b" ", b"")) == 0

def sha2(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def checkncreatedir(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)