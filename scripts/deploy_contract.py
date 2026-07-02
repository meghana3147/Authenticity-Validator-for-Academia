"""
Deploy AcadChain Smart Contract to Ethereum Sepolia Testnet
============================================================
Prerequisites:
    pip install py-solc-x web3 python-dotenv

Steps:
    1. Fill in .env (WEB3_PROVIDER_URI, DEPLOYER_ADDRESS, DEPLOYER_PRIVATE_KEY)
    2. Fund deployer wallet with Sepolia ETH from https://sepoliafaucet.com
    3. Run: python scripts/deploy_contract.py
    4. Copy CONTRACT_ADDRESS output into .env
"""
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

PROVIDER_URI      = os.getenv("WEB3_PROVIDER_URI", "")
DEPLOYER_ADDRESS  = os.getenv("DEPLOYER_ADDRESS", "")
DEPLOYER_KEY      = os.getenv("DEPLOYER_PRIVATE_KEY", "")
CONTRACT_SOL      = Path(__file__).parent.parent / "contracts" / "AcadChain.sol"
ABI_OUT           = Path(__file__).parent.parent / "contracts" / "AcadChain_ABI.json"
BYTECODE_OUT      = Path(__file__).parent.parent / "contracts" / "AcadChain_bytecode.txt"


def compile_contract():
    try:
        from solcx import compile_standard, install_solc
        install_solc("0.8.20")
        print("✅ solc 0.8.20 ready")
    except ImportError:
        print("❌ py-solc-x not installed.\n   Run: pip install py-solc-x")
        sys.exit(1)

    source = CONTRACT_SOL.read_text()
    compiled = compile_standard({
        "language": "Solidity",
        "sources":  {"AcadChain.sol": {"content": source}},
        "settings": {
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
            "optimizer": {"enabled": True, "runs": 200}
        }
    }, solc_version="0.8.20")

    data     = compiled["contracts"]["AcadChain.sol"]["AcadChain"]
    abi      = data["abi"]
    bytecode = data["evm"]["bytecode"]["object"]

    ABI_OUT.write_text(json.dumps(abi, indent=2))
    BYTECODE_OUT.write_text(bytecode)
    print(f"✅ Compiled — ABI saved to contracts/AcadChain_ABI.json")
    return abi, bytecode


def deploy(abi, bytecode):
    if not all([PROVIDER_URI, DEPLOYER_ADDRESS, DEPLOYER_KEY]):
        print("❌ Set WEB3_PROVIDER_URI, DEPLOYER_ADDRESS, DEPLOYER_PRIVATE_KEY in .env")
        sys.exit(1)

    try:
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware
    except ImportError:
        print("❌ web3 not installed. Run: pip install web3")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(PROVIDER_URI))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        print("❌ Cannot connect to Sepolia. Check WEB3_PROVIDER_URI in .env")
        sys.exit(1)

    print(f"✅ Connected — Chain ID: {w3.eth.chain_id}")
    bal = w3.from_wei(w3.eth.get_balance(DEPLOYER_ADDRESS), "ether")
    print(f"   Deployer : {DEPLOYER_ADDRESS}")
    print(f"   Balance  : {bal:.4f} ETH")

    if bal == 0:
        print("\n⚠  No ETH! Get Sepolia ETH from https://sepoliafaucet.com")
        sys.exit(1)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce    = w3.eth.get_transaction_count(DEPLOYER_ADDRESS)
    gas_est  = Contract.constructor().estimate_gas({"from": DEPLOYER_ADDRESS})

    tx = Contract.constructor().build_transaction({
        "from":     DEPLOYER_ADDRESS,
        "nonce":    nonce,
        "gas":      gas_est + 50_000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  11155111,
    })

    signed  = w3.eth.account.sign_transaction(tx, private_key=DEPLOYER_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"\n⏳ TX sent: {tx_hash.hex()}")
    print(   "   Waiting for confirmation (~30 sec)…")

    receipt  = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    addr     = receipt.contractAddress

    print(f"""
🎉 CONTRACT DEPLOYED!
   Address  : {addr}
   TX Hash  : {receipt.transactionHash.hex()}
   Block    : {receipt.blockNumber}
   Gas Used : {receipt.gasUsed:,}

👉 Add to your .env:
   CONTRACT_ADDRESS={addr}

🔗 Etherscan:
   https://sepolia.etherscan.io/address/{addr}
""")
    return addr


if __name__ == "__main__":
    print("=" * 56)
    print("  AcadChain — Sepolia Testnet Deployment")
    print("=" * 56 + "\n")
    abi, bytecode = compile_contract()
    deploy(abi, bytecode)
