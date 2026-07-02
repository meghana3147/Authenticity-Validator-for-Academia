"""
AcadChain Seed Script
=====================
Creates sample data for demo/testing.
Run AFTER setting up .env with MONGO_URI.

Usage:
    python scripts/seed.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app import create_app, bcrypt
from app.database import mongo
from app.models import generate_cert_id, generate_wallet, build_cert_hash
from datetime import datetime, timedelta
from bson import ObjectId
import random

app = create_app()

UNIVERSITIES = [
    {"name": "IIT Hyderabad",    "email": "iith@acadchain.in"},
    {"name": "JNTU Hyderabad",   "email": "jntu@acadchain.in"},
    {"name": "Osmania University","email": "ou@acadchain.in"},
]

STUDENTS = [
    {"name":"Arjun Sharma",  "email":"arjun@student.in",  "degree":"B.Tech CSE",      "major":"Artificial Intelligence",     "year":"2024","cgpa":"9.1"},
    {"name":"Priya Reddy",   "email":"priya@student.in",  "degree":"B.Tech ECE",      "major":"VLSI Design",                 "year":"2024","cgpa":"8.7"},
    {"name":"Rahul Verma",   "email":"rahul@student.in",  "degree":"M.Tech CSE",      "major":"Blockchain & Distributed Systems","year":"2023","cgpa":"8.9"},
    {"name":"Sneha Patel",   "email":"sneha@student.in",  "degree":"B.Sc Mathematics","major":"Data Science",                "year":"2024","cgpa":"9.4"},
    {"name":"Karthik Naidu", "email":"karthik@student.in","degree":"MBA",             "major":"Finance & Technology",        "year":"2023","cgpa":"8.2"},
]

def seed():
    with app.app_context():
        db = mongo.db
        print("\n🌱 Seeding AcadChain...\n")

        # Wipe seeded data
        for coll in [db.users, db.universities, db.students, db.certificates, db.verification_logs]:
            coll.delete_many({"seeded": True})

        def pw(plain):
            return bcrypt.generate_password_hash(plain).decode()

        # ── Admin ──────────────────────────────────────────
        db.users.insert_one({
            "name":"System Admin","email":"admin@acadchain.in",
            "password":pw("Admin@123"),"role":"admin","is_approved":True,
            "seeded":True,"created_at":datetime.utcnow()
        })
        print("  ✅ Admin       → admin@acadchain.in   / Admin@123")

        # ── Employer ───────────────────────────────────────
        db.users.insert_one({
            "name":"TechCorp HR","email":"hr@techcorp.in",
            "password":pw("Employer@123"),"role":"employer","is_approved":True,
            "seeded":True,"created_at":datetime.utcnow()
        })
        print("  ✅ Employer    → hr@techcorp.in        / Employer@123")

        # ── Universities ───────────────────────────────────
        uni_ids = []
        for u in UNIVERSITIES:
            uid = db.users.insert_one({
                "name":u["name"],"email":u["email"],
                "password":pw("Univ@1234"),"role":"university","is_approved":True,
                "seeded":True,"created_at":datetime.utcnow()
            }).inserted_id
            wallet = generate_wallet()
            uni_id = db.universities.insert_one({
                "user_id":uid,"institution_name":u["name"],
                "wallet_address":wallet,"is_verified":True,
                "seeded":True,"created_at":datetime.utcnow()
            }).inserted_id
            uni_ids.append((uni_id, u["name"], wallet))
            print(f"  ✅ University  → {u['email']:30s} / Univ@1234")

        # ── Students + Certificates ────────────────────────
        for i, s in enumerate(STUDENTS):
            uid = db.users.insert_one({
                "name":s["name"],"email":s["email"],
                "password":pw("Student@123"),"role":"student","is_approved":True,
                "seeded":True,"created_at":datetime.utcnow()
            }).inserted_id
            stu_id_str = f"STU{str(uid)[-5:].upper()}"
            stu_id = db.students.insert_one({
                "user_id":uid,"student_id":stu_id_str,
                "seeded":True,"created_at":datetime.utcnow()
            }).inserted_id

            uni_id, uni_name, wallet = uni_ids[i % len(uni_ids)]
            cert_id = generate_cert_id()
            cert_data = {
                "student_name":s["name"],"student_email":s["email"],
                "degree":s["degree"],"major":s["major"],
                "graduation_year":s["year"],"cgpa":s["cgpa"],"institution":uni_name
            }
            cert_hash = build_cert_hash(cert_data)
            fake_tx = "0x" + "".join(random.choices("0123456789abcdef", k=64))

            db.certificates.insert_one({
                "certificate_id":cert_id,"student_id":stu_id,"university_id":uni_id,
                "student_name":s["name"],"degree":s["degree"],"major":s["major"],
                "graduation_year":s["year"],"cgpa":s["cgpa"],
                "cert_hash":cert_hash,"tx_hash":fake_tx,
                "block_number":random.randint(5_000_000,5_999_999),
                "issuer_wallet":wallet,"on_chain":False,"is_revoked":False,
                "etherscan_url":f"https://sepolia.etherscan.io/tx/{fake_tx}",
                "seeded":True,"issued_at":datetime.utcnow()-timedelta(days=random.randint(1,90))
            })
            print(f"  ✅ Student     → {s['email']:30s} / Student@123  [{cert_id}]")

        print(f"""
{"="*54}
  SEED COMPLETE — Login Credentials
{"="*54}
  Admin      : admin@acadchain.in    / Admin@123
  University : iith@acadchain.in     / Univ@1234
  Student    : arjun@student.in      / Student@123
  Employer   : hr@techcorp.in        / Employer@123
{"="*54}
""")

if __name__ == "__main__":
    seed()
