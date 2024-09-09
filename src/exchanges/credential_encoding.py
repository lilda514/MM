from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from getpass import getpass
import os

# Function to derive a key from password
def derive_key(password: str) -> bytes:
    # Using SHA-256 to derive a 32-byte key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'',  # No salt here
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

# Function to encrypt the file
def encrypt_file(password):
    
    current_folder = os.path.dirname(os.path.abspath(__file__))
    while current_folder.split('\\')[-1] != "src":
        current_folder = current_folder = os.path.dirname(current_folder)
        
    file_path =  os.path.join(current_folder, 'exchanges', 'config.json')

    with open(file_path, 'rb') as f:
        plaintext = f.read()

    key = derive_key(password)
    iv = os.urandom(16)  # Initialization vector (IV) for AES

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Padding to ensure the plaintext fits AES block size (16 bytes)
    padder = PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Store iv and ciphertext in the encrypted file
    with open(file_path + '.enc', 'wb') as f:
        f.write(iv + ciphertext)

    print("File encrypted successfully")
    
def decrypt_config(file_path, password):
    with open(file_path, 'rb') as f:
        encrypted_data = f.read()

    # Extract the IV and ciphertext
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]

    key = derive_key(password)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove padding
    unpadder = PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext.decode()

if __name__ == "__main__":
    # Usage
    password = getpass("Enter password to encrypt the file: ")
    encrypt_file(password)
