import secrets
import time

_TTL_SECONDS = 3600


class NonceManager:
    def __init__(self):
        self._nonces: dict[str, float] = {}

    def _prune(self):
        cutoff = time.monotonic() - _TTL_SECONDS
        expired = [n for n, t in self._nonces.items() if t < cutoff]
        for n in expired:
            del self._nonces[n]

    def issue(self) -> str:
        self._prune()
        nonce = secrets.token_urlsafe(32)
        self._nonces[nonce] = time.monotonic()
        return nonce

    def consume(self, nonce: str) -> bool:
        if nonce in self._nonces:
            del self._nonces[nonce]
            return True
        return False


nonce_manager = NonceManager()
