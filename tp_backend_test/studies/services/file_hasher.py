import hashlib


class FileHasherService:
    def __init__(self):
        self.hash_func = hashlib.sha256

    def make_hash(self, data: bytes) -> str:
        return self.hash_func(data).hexdigest()
