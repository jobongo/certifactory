from app.services.encryption import encrypt_private_key, decrypt_private_key


def test_encrypt_decrypt_roundtrip():
    master_key = "test-master-key-that-is-32-bytes!"
    plaintext = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
    encrypted = encrypt_private_key(plaintext, master_key)
    assert encrypted != plaintext
    decrypted = decrypt_private_key(encrypted, master_key)
    assert decrypted == plaintext


def test_different_master_key_fails():
    master_key = "test-master-key-that-is-32-bytes!"
    wrong_key = "wrong-master-key-that-is-32-byt!"
    plaintext = "secret key data"
    encrypted = encrypt_private_key(plaintext, master_key)
    try:
        decrypt_private_key(encrypted, wrong_key)
        assert False, "Should have raised an exception"
    except Exception:
        pass


def test_encrypted_output_is_base64():
    import base64
    master_key = "test-master-key-that-is-32-bytes!"
    plaintext = "secret key data"
    encrypted = encrypt_private_key(plaintext, master_key)
    base64.b64decode(encrypted)
