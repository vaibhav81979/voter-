import hashlib
import json
from datetime import datetime

class VoteBlockchain:
    def __init__(self, difficulty=2):
        self.difficulty = difficulty

    def calculate_hash(self, index, previous_hash, timestamp, data, nonce):
        """Generate SHA-256 hash for a block."""
        value = str(index) + str(previous_hash) + str(timestamp) + str(data) + str(nonce)
        return hashlib.sha256(value.encode()).hexdigest()

    def proof_of_work(self, index, previous_hash, timestamp, data):
        """Execute Proof-of-Work to secure the vote."""
        nonce = 0
        while True:
            hash_value = self.calculate_hash(index, previous_hash, timestamp, data, nonce)
            if hash_value.startswith("0" * self.difficulty):
                return nonce, hash_value
            nonce += 1
