import os
import json
import logging
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "isRegistered",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "address", "name": "submitter", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

class BlockchainClient:
    def __init__(self, provider_uri: str | None = None, contract_address: str | None = None):
        self.provider_uri = provider_uri or os.getenv("WEB3_PROVIDER_URI", "http://127.0.0.1:8545")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS", "")
        self.web3 = None
        self.contract = None

        self.connect()

    def connect(self) -> bool:
        """Connects to Hardhat JSON-RPC node."""
        try:
            self.web3 = Web3(Web3.HTTPProvider(self.provider_uri))
            if self.web3.is_connected():
                if self.contract_address and Web3.is_address(self.contract_address):
                    self.contract = self.web3.eth.contract(
                        address=Web3.to_checksum_address(self.contract_address),
                        abi=ABI
                    )
                return True
        except Exception as e:
            print(f"[Blockchain Warning] Failed to connect to node at {self.provider_uri}: {e}")
        return False

    def is_connected(self) -> bool:
        return self.web3 is not None and self.web3.is_connected() and self.contract is not None

    def _hash_to_bytes32(self, hex_hash: str) -> bytes:
        clean_hash = hex_hash.lower().replace("0x", "")
        if len(clean_hash) != 64:
            raise ValueError(f"Invalid SHA-256 hash length ({len(clean_hash)} chars). Must be 64 hex characters.")
        return bytes.fromhex(clean_hash)

    def register_hash(self, evidence_hash: str) -> dict:
        """
        Registers an evidence hash on the Hardhat smart contract.
        Note: Assumes accounts[0] unlocked pre-funded account for localnet node.
        
        Args:
            evidence_hash: SHA-256 hex string.
            
        Returns:
            dict containing transaction receipt details.
            
        Raises:
            RuntimeError: if blockchain node or contract is unavailable.
        """
        bytes32_hash = self._hash_to_bytes32(evidence_hash)

        if not self.is_connected():
            raise RuntimeError("Blockchain service unavailable: Hardhat node is offline or contract is not deployed.")

        # Idempotency Guard: Check if hash is already anchored on-chain before sending transaction
        if self.is_registered(evidence_hash):
            existing = self.get_record(evidence_hash)
            sender = accounts[0] if (accounts := self.web3.eth.accounts) else "0x0000000000000000000000000000000000000000"
            return {
                "tx_hash": "ALREADY_ANCHORED_ON_CHAIN",
                "block_number": -1,
                "contract_address": self.contract_address,
                "status": "ALREADY_REGISTERED",
                "submitter": existing.get("submitter", sender) if existing else sender,
                "already_anchored": True
            }

        accounts = self.web3.eth.accounts
        if not accounts:
            raise RuntimeError("No unlocked Ethereum accounts found on node.")
        sender = accounts[0]

        # Call register function on smart contract
        tx_hash = self.contract.functions.register(bytes32_hash).transact({"from": sender})
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        receipt_data = {
            "tx_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
            "contract_address": self.contract_address,
            "status": "SUCCESS" if receipt["status"] == 1 else "FAILED",
            "submitter": sender,
            "already_anchored": False
        }
        return receipt_data


    def is_registered(self, evidence_hash: str) -> bool:
        """Checks if hash is registered on-chain."""
        bytes32_hash = self._hash_to_bytes32(evidence_hash)

        if not self.is_connected():
            return False

        try:
            return self.contract.functions.isRegistered(bytes32_hash).call()
        except Exception as e:
            print(f"[Blockchain Call Error] {e}")
            return False

    def get_record(self, evidence_hash: str) -> dict | None:
        """Retrieves submitter and timestamp for a registered hash."""
        bytes32_hash = self._hash_to_bytes32(evidence_hash)

        if not self.is_connected():
            return None

        try:
            submitter, timestamp = self.contract.functions.getRecord(bytes32_hash).call()
            if submitter == "0x0000000000000000000000000000000000000000" or timestamp == 0:
                return None
            return {
                "submitter": submitter,
                "timestamp": timestamp
            }
        except Exception:
            return None

