# ⛓ AcadChain — Blockchain Academic Certificate Validator

> Tamper-proof academic credentials on Ethereum Sepolia Testnet  
> Built with Flask · MongoDB · Web3.py · Solidity · SHA-256

---

## 📸 Project Overview

AcadChain is a full-stack blockchain application that eliminates fake academic certificates. Universities issue certificates whose **SHA-256 hash is stored on the Ethereum blockchain** via a Solidity smart contract. Employers can verify any certificate instantly — no phone calls, no delays.

### Supply Chain Flow
```
University → Smart Contract (Sepolia) → Student Dashboard → Employer Verification
```

### User Roles
| Role | Responsibilities |
|------|-----------------|
| **Admin** | Approve institutions, manage users, view blockchain explorer |
| **University** | Issue certificates, view issued records |
| **Student** | View certificates, share QR codes |
| **Employer** | Verify certificates by ID, hash, or file upload |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────┐
│           Web Browser (User)            │
└──────────────┬──────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────┐
│         Flask Backend (Python)          │
│  Routes · Auth · Business Logic         │
└────────┬──────────────┬─────────────────┘
         │              │
┌────────▼──────┐  ┌────▼────────────────┐
│   MongoDB     │  │  Web3.py            │
│   Atlas       │  │  (blockchain_service)│
│  (Users,Certs)│  └────┬────────────────┘
└───────────────┘       │ JSON-RPC
                  ┌─────▼────────────────┐
                  │  Infura / Alchemy     │
                  │  (Sepolia RPC Node)  │
                  └─────┬────────────────┘
                        │
                  ┌─────▼────────────────┐
                  │  Ethereum Sepolia     │
                  │  AcadChain.sol       │
                  │  Smart Contract      │
                  └──────────────────────┘
```

---

## 🚀 Quick Start (Simulated Mode — No Blockchain Needed)

You can run the project **fully offline** without Ethereum. The system auto-detects missing config and simulates blockchain transactions with realistic hashes.

### 1. Clone & Set Up

```bash
git clone <your-repo-url>
cd acadchain

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — for simulated mode, **only MongoDB is required**:

```env
SECRET_KEY=any-random-secret-string-here
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/acadchain
```

### 3. Run the App

```bash
python run.py
```

Visit: **http://localhost:5000**

### 4. Seed Sample Data (Optional)

```bash
python scripts/seed.py
```

**Default credentials after seeding:**
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@acadchain.in | Admin@123 |
| University | iith@acadchain.in | Univ@1234 |
| Student | arjun@student.in | Student@123 |
| Employer | hr@techcorp.in | Employer@123 |

---

## ⛓ Real Blockchain Setup (Ethereum Sepolia Testnet)

### Prerequisites
- MetaMask wallet installed
- Infura or Alchemy account (free)

### Step 1: Get a Provider URL

**Infura:**
1. Go to https://infura.io → Create account → New Project
2. Copy: `https://sepolia.infura.io/v3/YOUR_PROJECT_ID`

**Alchemy:**
1. Go to https://alchemy.com → Create app → Ethereum Sepolia
2. Copy the HTTPS URL

### Step 2: Get Sepolia Test ETH

1. Open MetaMask → Switch to **Sepolia** testnet
2. Visit https://sepoliafaucet.com → Connect wallet → Claim ETH
3. Wait ~1 minute for funds to arrive

### Step 3: Export Wallet Private Key

In MetaMask: Account → Three dots → Account Details → Export Private Key

⚠️ **NEVER commit your private key to Git.**

### Step 4: Update .env

```env
WEB3_PROVIDER_URI=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
DEPLOYER_ADDRESS=0xYourWalletAddress
DEPLOYER_PRIVATE_KEY=0xYourPrivateKey
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/acadchain
```

### Step 5: Deploy the Smart Contract

```bash
pip install py-solc-x
python scripts/deploy_contract.py
```

Output will show:
```
🎉 CONTRACT DEPLOYED!
   Address : 0xABC...
   
👉 Add to your .env:
   CONTRACT_ADDRESS=0xABC...
```

Copy the address into `.env`:
```env
CONTRACT_ADDRESS=0xYourDeployedContractAddress
```

### Step 6: Run the App

```bash
python run.py
```

The app will now write real transactions to Sepolia! You can view them on:  
🔗 https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS

---

## 📁 Project Structure

```
acadchain/
├── app/
│   ├── __init__.py              # Flask factory
│   ├── database.py              # MongoDB (PyMongo)
│   ├── models.py                # User class, helpers
│   ├── blockchain_service.py    # Web3.py + Sepolia
│   ├── routes/
│   │   ├── auth.py              # Login, Register, Logout
│   │   ├── admin.py             # Admin panel
│   │   ├── university.py        # Issue certificates
│   │   ├── student.py           # View + QR
│   │   ├── employer.py          # Verify
│   │   └── main.py              # Landing, public verify
│   ├── templates/
│   │   ├── base.html            # Shared layout
│   │   ├── auth/                # Login, Register
│   │   ├── admin/               # 6 admin pages
│   │   ├── university/          # 4 pages
│   │   ├── student/             # 2 pages
│   │   ├── employer/            # 2 pages
│   │   └── main/                # Landing, Verify, Explorer
│   └── static/
│       └── uploads/certificates/  # Uploaded PDFs/images
├── contracts/
│   ├── AcadChain.sol            # Solidity smart contract
│   └── AcadChain_ABI.json       # Contract ABI
├── scripts/
│   ├── deploy_contract.py       # Sepolia deployment
│   └── seed.py                  # Sample data seeder
├── docs/
├── run.py                       # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔐 Security Features

| Feature | Implementation |
|---------|---------------|
| Password Hashing | Flask-Bcrypt (bcrypt) |
| Session Management | Flask-Login with secure cookies |
| Certificate Integrity | SHA-256 hash on all certificate fields |
| Immutable Storage | Ethereum blockchain (cannot be altered) |
| Tamper Detection | Hash comparison on verification |
| Role-Based Access | Decorator-enforced on every route |
| Revocation | On-chain revocation flag |

---

## 🧠 Smart Contract — AcadChain.sol

### Key Functions

```solidity
// Issue a certificate (approved universities only)
function issueCertificate(string certId, bytes32 certHash, 
                           string studentName, string degree, 
                           string institution) external

// Verify by hash — pure read, no gas
function verifyCertificate(bytes32 certHash) external view 
    returns (bool exists, bool isRevoked, address issuer, ...)

// Quick authentic check
function isAuthentic(bytes32 certHash) external view returns (bool)

// Admin revokes institution access
function revokeInstitution(address wallet) external onlyOwner
```

### Deployed On
- **Network:** Ethereum Sepolia Testnet (Chain ID: 11155111)
- **Solidity Version:** ^0.8.20
- **License:** MIT

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, Bootstrap 5.3, JavaScript, Google Fonts |
| Backend | Python 3.10+, Flask 3.0 |
| Database | MongoDB Atlas (via Flask-PyMongo) |
| Blockchain | Ethereum Sepolia, Solidity 0.8.20 |
| Web3 | Web3.py 6.x |
| Auth | Flask-Login, Flask-Bcrypt |
| QR Code | qrcode + Pillow |
| Hashing | hashlib SHA-256 |

---

## 📊 MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `users` | All user accounts (admin/uni/student/employer) |
| `universities` | Institution profiles & wallet addresses |
| `students` | Student profiles linked to users |
| `certificates` | Issued certificates with blockchain data |
| `verification_logs` | Every verification attempt (audit trail) |

---

## ❓ Troubleshooting

**MongoDB connection fails:**  
→ Check MONGO_URI in .env. Whitelist your IP in MongoDB Atlas Network Access.

**Web3 connection fails (auto falls to simulated):**  
→ Check WEB3_PROVIDER_URI. Verify Infura project is on Sepolia network.

**deploy_contract.py fails — "py-solc-x not found":**  
→ Run: `pip install py-solc-x`

**Insufficient funds error on deploy:**  
→ Get Sepolia ETH from https://sepoliafaucet.com

**QR code not generating:**  
→ Run: `pip install qrcode[pil] Pillow`

---

## 🎯 Demo Flow (for Viva / Presentation)

1. **Login as University** (iith@acadchain.in) → Issue certificate to arjun@student.in
2. **Login as Student** (arjun@student.in) → View certificate → Show QR code
3. **Login as Employer** (hr@techcorp.in) → Verify by Certificate ID → See blockchain proof
4. **Login as Admin** → Approve institutions → View blockchain explorer → Revoke certificate
5. **Public Verify** (no login) → Enter cert ID at /verify → See full blockchain proof

---

## 👨‍💻 Author

**AcadChain Project** — 3rd Year Mini Project  
Blockchain & Supply Chain · Authenticity Validator for Academia

---

## 📄 License

MIT License — Free to use for educational purposes.
