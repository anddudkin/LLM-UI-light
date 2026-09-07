import base64
import hashlib
import os

# Required environment variable — the app must not start with a default/publicly known key,
# otherwise anyone could forge user_info for /api/sso and log in as an arbitrary email.
# Generate your own: `openssl rand -hex 32`.
SECRET_KEY = os.environ["SSO_SECRET_KEY"]

class SimpleCipher:
    def __init__(self):
        self.key = SECRET_KEY.encode()
        self.block_size = 32

    def _generate_keystream(self, counter: int, length: int) -> bytes:
        result = bytearray()
        while len(result) < length:
            h = hashlib.sha256()
            h.update(self.key)
            h.update(counter.to_bytes(16, 'big'))
            result.extend(h.digest())
            counter += 1
        return bytes(result[:length])

    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode()
        nonce = os.urandom(16)
        counter = int.from_bytes(nonce, 'big')
        keystream = self._generate_keystream(counter, len(data))
        encrypted = bytes(a ^ b for a, b in zip(data, keystream))
        combined = nonce + encrypted
        return base64.urlsafe_b64encode(combined).decode()

    def decrypt(self, token: str) -> str:
        combined = base64.urlsafe_b64decode(token)
        nonce = combined[:16]
        encrypted = combined[16:]
        counter = int.from_bytes(nonce, 'big')
        keystream = self._generate_keystream(counter, len(encrypted))
        decrypted = bytes(a ^ b for a, b in zip(encrypted, keystream))
        return decrypted.decode()

# Create a single instance for reuse
cipher = SimpleCipher()