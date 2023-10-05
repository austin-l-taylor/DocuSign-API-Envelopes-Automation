from cryptography.hazmat.primitives.ciphers import algorithms, modes, Cipher
from cryptography.hazmat.backends import default_backend
from base64 import b64decode
from keeper_secrets_manager_core import SecretsManager
from keeper_secrets_manager_core.storage import FileKeyValueStorage
import os

def decrypt_data(data, encryption_key):
    key = b64decode(encryption_key)
    iv = b'\x00' * 16  # 16 bytes for AES block size, set to zeros to match the C# example
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()

    decrypted_data = decryptor.update(data) + decryptor.finalize()

    # Read padding length and remove padding
    padding_length = decrypted_data[-1]
    return decrypted_data[:-padding_length]

# Using token only to generate the config 
# requires at least one access operation to bind the token
def get_secrets(uids):
    # Retrieve the encryption key from the environment variable
    encryption_key = os.environ.get('KEEPER_ENCRYPTION_KEY')

    # Read the encrypted file path from the environment variable
    encrypted_file_path = os.environ.get('KEEPER_CONFIG_FILE_PATH')

    if not encryption_key or not encrypted_file_path:
        raise FileNotFoundError("Unable to locate Keeper configuration file! Have you configured this user for Keeper Secrets Manager?")

    # Read the encrypted configuration file
    with open(encrypted_file_path, 'rb') as file:
        encrypted_data = file.read()

    # Decrypt the data
    # try:
        decrypted_data = decrypt_data(encrypted_data, encryption_key)
    # except Exception as e:
    #     raise Exception(f"Unable to decrypt configuration file! Installation may be corrupt. Please re-configure this user for Keeper Secrets Manager. {str(e)}")

    # Write the unencrypted file to the drive temporarily
    # This is a security vulnerability in my opinion, but I'm assuming Keeper SDK for Python offers no way to initialize a LocalStorageConfig from memory
    unencrypted_file_path = 'ksm-config.json'
    with open(unencrypted_file_path, 'wb') as file:
        file.write(decrypted_data)

    # Use the unencrypted file to initialize Keeper's local storage
    secrets_manager = SecretsManager(
        config=FileKeyValueStorage(unencrypted_file_path)
    )

    # Fetch secret from the Keeper vault, using internal Keeper Secrets Manager API
    secret = secrets_manager.get_secrets(uids)

    # Delete the unencrypted file ASAP - REMOVED BECAUSE SECRETSMANAGER OBJECT CACHES THE FILE PATH INSTEAD OF THE JWT CONTENT
    # TODO: overwrite file before deletion for security
    os.remove(unencrypted_file_path)

    # Configure Keeper's options
    return secret
