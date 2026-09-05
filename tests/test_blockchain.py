import uuid
import hashlib
import pytest
from app.blockchain.client import BlockchainClient

def test_blockchain_registration_and_verification():
    """Verifies evidence hash registration and is_registered check on BlockchainClient when connected."""
    client = BlockchainClient()
    dummy_hash = hashlib.sha256(f"test_hash_1_{uuid.uuid4()}".encode()).hexdigest()
    
    if not client.is_connected():
        with pytest.raises(RuntimeError):
            client.register_hash(dummy_hash)
        return

    # Check initially not registered
    assert client.is_registered(dummy_hash) is False

    # Register hash
    receipt = client.register_hash(dummy_hash)
    assert receipt["tx_hash"] is not None
    assert receipt["block_number"] >= 0

    # Verify is_registered returns True
    assert client.is_registered(dummy_hash) is True


def test_blockchain_double_registration_prevention():
    """Verifies double registering identical hash raises error or handles gracefully."""
    client = BlockchainClient()
    dummy_hash = hashlib.sha256(f"test_hash_2_{uuid.uuid4()}".encode()).hexdigest()

    if not client.is_connected():
        with pytest.raises(RuntimeError):
            client.register_hash(dummy_hash)
        return

    receipt1 = client.register_hash(dummy_hash)
    assert client.is_registered(dummy_hash) is True
    assert receipt1["already_anchored"] is False

    # Re-registering identical hash returns idempotency receipt without EVM revert
    receipt2 = client.register_hash(dummy_hash)
    assert receipt2["status"] == "ALREADY_REGISTERED"
    assert receipt2["already_anchored"] is True




