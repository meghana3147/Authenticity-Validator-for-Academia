"""
AcadChain Blockchain Service

This file is responsible for talking to the blockchain (Ethereum Sepolia testnet).

👉 If blockchain credentials are NOT set in .env:
   → It runs in "simulated mode" (fake transactions)

👉 If credentials ARE set:
   → It connects to real Ethereum network
"""

# -------------------- IMPORTS --------------------

import os, json, random

# Used to handle file paths properly
from pathlib import Path

# Used for timestamps
from datetime import datetime, timezone

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


# -------------------- CONFIGURATION --------------------

# Path to ABI file (ABI = contract structure description)
_ABI_PATH = Path(__file__).parent.parent / "contracts" / "AcadChain_ABI.json"

# These values come from .env file
PROVIDER_URI     = os.getenv("WEB3_PROVIDER_URI", "")   # Infura/Alchemy URL
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")    # deployed contract address
DEPLOYER_ADDRESS = os.getenv("DEPLOYER_ADDRESS", "")    # wallet address
DEPLOYER_KEY     = os.getenv("DEPLOYER_PRIVATE_KEY", "")# private key (secret!)


# -------------------- MAIN CLASS --------------------

class BlockchainService:
    """
    This class handles all blockchain operations.

    It uses CLASS VARIABLES (shared across all uses)
    """

    _w3        = None   # Web3 connection object
    _contract  = None   # Smart contract instance
    _simulated = True   # Default → assume fake mode
    _tried     = False  # Prevent multiple initializations


    # -------------------- INITIALIZATION --------------------

    @classmethod
    def _init(cls):
        """
        This runs ONCE to setup blockchain connection.

        Why?
        → Avoid reconnecting every time (performance)
        """

        # If already tried → do nothing
        if cls._tried:
            return

        cls._tried = True

        # If required config missing → use simulated mode
        if not PROVIDER_URI or not CONTRACT_ADDRESS:
            cls._simulated = True
            return

        try:
            # Import Web3 library (used to interact with Ethereum)
            from web3 import Web3

            # Required for some networks like Sepolia (Proof-of-Authority)
            from web3.middleware import ExtraDataToPOAMiddleware

            # Connect to Ethereum node (Infura/Alchemy)
            w3 = Web3(Web3.HTTPProvider(PROVIDER_URI, request_kwargs={"timeout": 8}))

            # Inject middleware (important for Sepolia testnet)
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            # Check if connection works
            if not w3.is_connected():
                cls._simulated = True
                return

            # Load smart contract ABI (structure of functions)
            abi = json.loads(_ABI_PATH.read_text())

            # Create contract object
            cls._contract = w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=abi
            )

            cls._w3 = w3
            cls._simulated = False

            print("✅ BlockchainService: connected to Sepolia")

        except Exception as e:
            # If anything fails → fallback to simulated mode
            print(f"⚠ BlockchainService: simulated mode ({e})")
            cls._simulated = True


    # -------------------- PUBLIC METHODS --------------------

    @classmethod
    def is_live(cls) -> bool:
        """
        Check if real blockchain is connected or not
        """
        cls._init()
        return not cls._simulated


    # -------------------- ISSUE CERTIFICATE --------------------

    @classmethod
    def issue_certificate(cls, cert_id, cert_hash_hex,
                          student_name, degree, institution) -> dict:
        """
        Store certificate on blockchain

        If live:
            → sends real transaction
        If simulated:
            → returns fake transaction
        """

        cls._init()

        # If not connected → return fake transaction
        if cls._simulated:
            return cls._fake_tx()

        try:
            from web3 import Web3

            # Convert hex string → bytes (blockchain format)
            hash_bytes = bytes.fromhex(cert_hash_hex)

            # Get transaction count (needed for uniqueness)
            nonce = cls._w3.eth.get_transaction_count(DEPLOYER_ADDRESS)

            # Prepare smart contract function call
            fn = cls._contract.functions.issueCertificate(
                cert_id, hash_bytes, student_name, degree, institution
            )

            # Estimate gas (transaction cost)
            gas = fn.estimate_gas({"from": DEPLOYER_ADDRESS})

            # Build transaction
            tx = fn.build_transaction({
                "from": DEPLOYER_ADDRESS,
                "nonce": nonce,
                "gas": gas + 30000,  # extra buffer
                "gasPrice": cls._w3.eth.gas_price,
                "chainId": 11155111  # Sepolia network ID
            })

            # Sign transaction using private key
            signed = cls._w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_KEY)

            # Send transaction to blockchain
            tx_hash = cls._w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait until transaction is mined (confirmed)
            receipt = cls._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # Get block info
            block = cls._w3.eth.get_block(receipt.blockNumber)

            # Convert timestamp
            ts = datetime.fromtimestamp(block.timestamp, tz=timezone.utc)

            # Return transaction details
            return {
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "timestamp": ts,
                "gas_used": receipt.gasUsed,
                "simulated": False,
                "etherscan_url": f"https://sepolia.etherscan.io/tx/{receipt.transactionHash.hex()}",
            }

        except Exception as e:
            print(f"⚠ on-chain issue failed: {e}")

            # fallback if error
            return cls._fake_tx()


    # -------------------- VERIFY CERTIFICATE --------------------

    @classmethod
    def verify_certificate(cls, cert_hash_hex) -> dict:
        """
        Check if certificate exists on blockchain
        """

        cls._init()

        # If not live → cannot verify
        if cls._simulated or not cls._contract:
            return {"live": False}

        try:
            # Convert hash
            hb = bytes.fromhex(cert_hash_hex)

            # Call smart contract function (read-only)
            result = cls._contract.functions.verifyCertificate(hb).call()

            # Unpack returned values
            exists, is_revoked, issuer, issued_at, student_name, degree, institution = result

            return {
                "live": True,
                "exists": exists,
                "is_revoked": is_revoked,
                "issuer": issuer,
                "issued_at": datetime.fromtimestamp(issued_at, tz=timezone.utc) if issued_at else None,
                "student_name": student_name,
                "degree": degree,
                "institution": institution,
            }

        except Exception as e:
            print(f"⚠ verify failed: {e}")
            return {"live": False}


    # -------------------- REVOKE CERTIFICATE --------------------

    @classmethod
    def revoke_on_chain(cls, cert_hash_hex) -> dict:
        """
        Mark certificate as revoked on blockchain
        """

        cls._init()

        if cls._simulated:
            return cls._fake_tx()

        try:
            from web3 import Web3

            hb = bytes.fromhex(cert_hash_hex)
            nonce = cls._w3.eth.get_transaction_count(DEPLOYER_ADDRESS)

            # Build revoke transaction
            tx = cls._contract.functions.revokeCertificate(hb).build_transaction({
                "from": DEPLOYER_ADDRESS,
                "nonce": nonce,
                "gas": 80000,
                "gasPrice": cls._w3.eth.gas_price,
                "chainId": 11155111
            })

            # Sign + send
            signed = cls._w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_KEY)
            tx_hash = cls._w3.eth.send_raw_transaction(signed.raw_transaction)

            # Wait for confirmation
            receipt = cls._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            return {
                "tx_hash": receipt.transactionHash.hex(),
                "simulated": False
            }

        except Exception as e:
            print(f"⚠ revoke failed: {e}")
            return cls._fake_tx()


    # -------------------- CONTRACT STATS --------------------

    @classmethod
    def get_contract_stats(cls) -> dict:
        """
        Get overall contract statistics
        """

        cls._init()

        if cls._simulated or not cls._contract:
            return {"live": False}

        try:
            certs, insts, owner = cls._contract.functions.getContractStats().call()

            return {
                "live": True,
                "total_certificates": certs,
                "total_institutions": insts,
                "owner": owner
            }

        except Exception:
            return {"live": False}


    # -------------------- HELPER (FAKE TRANSACTION) --------------------

    @staticmethod
    def _fake_tx() -> dict:
        """
        Generate a fake blockchain response

        Used when:
        - No internet
        - No API key
        - Testing mode
        """

        # Fake transaction hash
        fake_tx = "0x" + "".join(random.choices("0123456789abcdef", k=64))

        # Fake block number
        fake_block = random.randint(5_500_000, 6_500_000)

        return {
            "tx_hash": fake_tx,
            "block_number": fake_block,
            "timestamp": datetime.utcnow(),
            "gas_used": None,
            "simulated": True,
            "etherscan_url": f"https://sepolia.etherscan.io/tx/{fake_tx}",
        }