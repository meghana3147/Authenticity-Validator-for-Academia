"""
blockchain.py
─────────────
Dual-mode blockchain service:

  MODE A – Sepolia Testnet  (CONTRACT_ADDRESS + credentials in .env)
      • issueCertificate()  sends a real on-chain transaction
      • verifyCertificate() calls the read-only contract view

  MODE B – Local simulation  (fallback when .env keys are missing)
      • SHA-256 Proof-of-Work chain stored only in MongoDB
      • Perfect for demo / viva without spending test-ETH

Switch by setting CONTRACT_ADDRESS in .env.
"""

import hashlib, json, os, random, string, time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── optional web3 import ────────────────────────────────────────────────────
try:
    from web3 import Web3
    # web3 v6+ renamed geth_poa_middleware → ExtraDataToPOAMiddleware
    try:
        from web3.middleware import ExtraDataToPOAMiddleware as _poa_mw
    except ImportError:
        from web3.middleware import geth_poa_middleware as _poa_mw
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    _poa_mw = None

# ── load env ────────────────────────────────────────────────────────────────
SEPOLIA_RPC_URL     = os.getenv('SEPOLIA_RPC_URL', '')
DEPLOYER_PRIVATE_KEY = os.getenv('DEPLOYER_PRIVATE_KEY', '')
DEPLOYER_ADDRESS    = os.getenv('DEPLOYER_ADDRESS', '')
CONTRACT_ADDRESS    = os.getenv('CONTRACT_ADDRESS', '0x0000000000000000000000000000000000000000')

ABI_PATH = os.path.join(os.path.dirname(__file__), '..', 'contracts', 'AcadChain_ABI.json')

# ── initialise Web3 ─────────────────────────────────────────────────────────
_w3       = None
_contract = None
_sepolia_live = False

def _init_web3():
    global _w3, _contract, _sepolia_live
    if not WEB3_AVAILABLE or not SEPOLIA_RPC_URL or 'YOUR_INFURA' in SEPOLIA_RPC_URL:
        return
    try:
        _w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
        if _poa_mw:
            _w3.middleware_onion.inject(_poa_mw, layer=0)
        if _w3.is_connected() and CONTRACT_ADDRESS != '0x' + '0'*40:
            with open(ABI_PATH) as f:
                abi = json.load(f)
            _contract = _w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=abi
            )
            _sepolia_live = True
            print("✅ Connected to Sepolia Testnet")
    except Exception as e:
        print(f"⚠️  Sepolia unavailable, using local simulation: {e}")

_init_web3()


# ════════════════════════════════════════════════════════════════════════════
class BlockchainService:
    """Public API used by Flask routes."""

    # ── hashing ─────────────────────────────────────────────────────────
    @staticmethod
    def generate_certificate_hash(data: dict) -> str:
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def hex_to_bytes32(hex_str: str) -> bytes:
        """Convert 64-char hex hash to bytes32 for Solidity."""
        return bytes.fromhex(hex_str)

    # ── wallet helpers ───────────────────────────────────────────────────
    @staticmethod
    def generate_wallet_address() -> str:
        chars = string.hexdigits.lower()
        return '0x' + ''.join(random.choices(chars, k=40))

    @staticmethod
    def generate_tx_hash() -> str:
        return '0x' + ''.join(random.choices(string.hexdigits.lower(), k=64))

    @staticmethod
    def generate_certificate_id() -> str:
        ts   = int(time.time())
        rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f'CERT-{ts}-{rand}'

    # ── Sepolia: issue ───────────────────────────────────────────────────
    @staticmethod
    def issue_on_sepolia(cert_hash: str, cert_id: str,
                         student_name: str, degree: str,
                         institution: str) -> dict:
        """Send issueCertificate tx to Sepolia. Returns tx receipt dict."""
        if not _sepolia_live:
            raise RuntimeError("Sepolia not configured")

        cert_bytes = BlockchainService.hex_to_bytes32(cert_hash)
        nonce      = _w3.eth.get_transaction_count(DEPLOYER_ADDRESS)
        gas_price  = _w3.eth.gas_price

        txn = _contract.functions.issueCertificate(
            cert_bytes, cert_id, student_name, degree, institution
        ).build_transaction({
            'from':     DEPLOYER_ADDRESS,
            'nonce':    nonce,
            'gas':      300_000,
            'gasPrice': gas_price,
        })
        signed  = _w3.eth.account.sign_transaction(txn, DEPLOYER_PRIVATE_KEY)
        tx_hash = _w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = _w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            'tx_hash':     tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'gas_used':    receipt['gasUsed'],
            'status':      receipt['status'],   # 1 = success
        }

    # ── Sepolia: verify ──────────────────────────────────────────────────
    @staticmethod
    def verify_on_sepolia(cert_hash: str) -> dict:
        """Call verifyCertificate (read-only). Returns dict or None."""
        if not _sepolia_live:
            return None
        cert_bytes = BlockchainService.hex_to_bytes32(cert_hash)
        result = _contract.functions.verifyCertificate(cert_bytes).call()
        keys   = ['exists', 'isRevoked', 'issuer', 'issuedAt',
                  'studentName', 'degree', 'institution', 'certificateId']
        return dict(zip(keys, result))

    # ── Sepolia: revoke ──────────────────────────────────────────────────
    @staticmethod
    def revoke_on_sepolia(cert_hash: str) -> str:
        if not _sepolia_live:
            raise RuntimeError("Sepolia not configured")
        cert_bytes = BlockchainService.hex_to_bytes32(cert_hash)
        nonce = _w3.eth.get_transaction_count(DEPLOYER_ADDRESS)
        txn   = _contract.functions.revokeCertificate(cert_bytes).build_transaction({
            'from': DEPLOYER_ADDRESS, 'nonce': nonce,
            'gas': 100_000, 'gasPrice': _w3.eth.gas_price,
        })
        signed  = _w3.eth.account.sign_transaction(txn, DEPLOYER_PRIVATE_KEY)
        tx_hash = _w3.eth.send_raw_transaction(signed.rawTransaction)
        _w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        return tx_hash.hex()

    # ── local PoW simulation ─────────────────────────────────────────────
    DIFFICULTY = 3

    @classmethod
    def mine_block_local(cls, block_number: int, previous_hash: str,
                          cert_hash: str, issuer: str) -> dict:
        ts     = datetime.utcnow().isoformat()
        nonce  = 0
        target = '0' * cls.DIFFICULTY
        while True:
            raw = f"{block_number}{previous_hash}{cert_hash}{issuer}{ts}{nonce}"
            bh  = hashlib.sha256(raw.encode()).hexdigest()
            if bh.startswith(target):
                break
            nonce += 1
            if nonce > 200_000:
                break
        return {
            'block_number':   block_number,
            'block_hash':     bh,
            'previous_hash':  previous_hash,
            'cert_hash':      cert_hash,
            'issuer':         issuer,
            'timestamp':      ts,
            'nonce':          nonce,
            'tx_hash':        cls.generate_tx_hash(),
        }

    # ── unified issue entry-point ────────────────────────────────────────
    @classmethod
    def record_certificate(cls, db, cert_hash: str, cert_id: str,
                            student_name: str, degree: str,
                            institution: str, issuer_wallet: str) -> dict:
        """
        Try Sepolia first; fall back to local simulation.
        Always writes a record to db.blockchain_records.
        Returns info dict with tx_hash, block_number, mode.
        """
        result = {'mode': 'local'}

        if _sepolia_live:
            try:
                r = cls.issue_on_sepolia(cert_hash, cert_id, student_name, degree, institution)
                result.update(r)
                result['mode'] = 'sepolia'
                # store minimal record in Mongo for explorer
                db.blockchain_records.insert_one({
                    'block_number':    r['block_number'],
                    'tx_hash':         r['tx_hash'],
                    'cert_hash':       cert_hash,
                    'certificate_id':  cert_id,
                    'issuer_address':  issuer_wallet,
                    'timestamp':       datetime.utcnow(),
                    'network':         'Sepolia Testnet',
                    'gas_used':        r.get('gas_used'),
                })
                return result
            except Exception as e:
                print(f"⚠️  Sepolia tx failed, falling back to local: {e}")

        # Local PoW fallback
        last = db.blockchain_records.find_one(sort=[('block_number', -1)])
        prev_hash  = last['block_hash'] if last else '0' * 64
        block_num  = (last['block_number'] + 1) if last else 1
        mined = cls.mine_block_local(block_num, prev_hash, cert_hash, issuer_wallet)
        db.blockchain_records.insert_one({
            'block_number':   mined['block_number'],
            'block_hash':     mined['block_hash'],
            'previous_hash':  mined['previous_hash'],
            'cert_hash':      cert_hash,
            'certificate_id': cert_id,
            'issuer_address': issuer_wallet,
            'timestamp':      datetime.utcnow(),
            'nonce':          mined['nonce'],
            'tx_hash':        mined['tx_hash'],
            'network':        'Local Simulation',
        })
        result.update(mined)
        return result

    # ── QR helper ────────────────────────────────────────────────────────
    @staticmethod
    def generate_qr_url(cert_id: str, cert_hash: str, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/verify?cert_id={cert_id}&h={cert_hash[:16]}"

    # ── status ────────────────────────────────────────────────────────────
    @staticmethod
    def is_sepolia_live() -> bool:
        return _sepolia_live
