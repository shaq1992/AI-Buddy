import hashlib
import os
import base64

def generate_rabbit_hash(password):
    # 1. Generate a random 4-byte salt
    salt = os.urandom(4)
    
    # 2. Concatenate Salt + Password (utf-8)
    tmp0 = salt + password.encode('utf-8')
    
    # 3. SHA256 hash the result
    hashed_bytes = hashlib.sha256(tmp0).digest()
    
    # 4. Concatenate Salt + Hash
    salt_and_hash = salt + hashed_bytes
    
    # 5. Base64 encode the result
    pass_hash = base64.b64encode(salt_and_hash).decode('utf-8')
    
    return pass_hash

if __name__ == "__main__":
    password = "guest"
    hash_value = generate_rabbit_hash(password)
    print(f"Password: {password}")
    print(f"Hash: {hash_value}")