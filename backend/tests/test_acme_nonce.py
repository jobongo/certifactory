from app.services.acme_nonce import NonceManager


def test_issued_nonce_can_be_consumed_once():
    mgr = NonceManager()
    n = mgr.issue()
    assert mgr.consume(n) is True
    assert mgr.consume(n) is False  # already used


def test_unknown_nonce_rejected():
    mgr = NonceManager()
    assert mgr.consume("never-issued") is False


def test_nonces_are_unique():
    mgr = NonceManager()
    nonces = {mgr.issue() for _ in range(100)}
    assert len(nonces) == 100
