# -------------------- IMPORTS --------------------

# UserMixin gives default login-related methods (like is_authenticated)
from flask_login import UserMixin

# MongoDB connection object
from app.database import mongo

# Used to convert string IDs into MongoDB ObjectId
from bson import ObjectId

# Built-in libraries
import hashlib   # used for hashing (secure fingerprints)
import json      # used to convert data into string format
import random    # for generating random values
import string    # contains letters, digits etc.
import time      # for timestamps


# -------------------- USER CLASS --------------------

class User(UserMixin):
    """
    This class represents a logged-in user in your app.

    It wraps a MongoDB document (dictionary) and provides
    easy access to user data.
    """

    def __init__(self, doc):
        # Store the full MongoDB document
        self._doc = doc

    # Flask-Login requires an 'id' property
    @property
    def id(self):
        # Convert MongoDB ObjectId → string
        return str(self._doc["_id"])

    # Get user's name (if not present, return empty string)
    @property
    def name(self):
        return self._doc.get("name", "")

    # Get user's email
    @property
    def email(self):
        return self._doc.get("email", "")

    # Get user's role (admin, student, etc.)
    @property
    def role(self):
        return self._doc.get("role", "")

    # Check if user is approved (default = False)
    @property
    def is_approved(self):
        return self._doc.get("is_approved", False)

    # Required by Flask-Login
    def get_id(self):
        return self.id


# -------------------- USER LOADER (VERY IMPORTANT) --------------------

from app import login_manager

@login_manager.user_loader
def load_user(user_id):
    """
    This function is used by Flask-Login.

    When a user is logged in, Flask stores their ID in session.
    Later, it calls this function to reload the user from DB.

    Example:
    session → user_id → this function → fetch user from MongoDB
    """
    try:
        # Find user in database using ObjectId
        doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})

        # If found → return User object
        # If not → return None
        return User(doc) if doc else None

    except Exception:
        # If invalid ID or error → return None (safe fallback)
        return None


# -------------------- PASSWORD FUNCTIONS --------------------

def hash_password(pw: str) -> str:
    """
    Convert plain password → hashed password

    WHY?
    Never store plain passwords in database (security risk)
    """
    from app import bcrypt

    # Generate hashed password and convert bytes → string
    return bcrypt.generate_password_hash(pw).decode("utf-8")


def check_password(hashed: str, pw: str) -> bool:
    """
    Compare entered password with stored hashed password

    Returns True if match, else False
    """
    from app import bcrypt
    return bcrypt.check_password_hash(hashed, pw)


# -------------------- CERTIFICATE HELPERS --------------------

def generate_cert_id() -> str:
    """
    Create a unique certificate ID

    Format example:
    CERT-1711623456-AB12CD
    """

    # Current timestamp (seconds)
    ts = int(time.time())

    # Random 6-character string (A-Z + 0-9)
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return f"CERT-{ts}-{rand}"


def generate_wallet() -> str:
    """
    Generate a fake blockchain wallet address

    Format:
    0x + 40 hex characters
    """

    return "0x" + "".join(
        random.choices(string.hexdigits.lower()[:16], k=40)
    )


def build_cert_hash(data: dict) -> str:
    """
    Create a secure hash of certificate data

    WHY?
    - Ensures data integrity
    - If data changes → hash changes

    Steps:
    1. Convert data → JSON string
    2. Sort keys (consistent order)
    3. Apply SHA-256 hashing
    """

    # Convert dictionary → string
    payload = json.dumps(data, sort_keys=True, default=str)

    # Generate SHA-256 hash
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------- DATABASE CREATE HELPERS --------------------

from datetime import datetime


def create_user(name: str, email: str, password: str, role: str, is_approved: bool = False):
    """
    Create a new user in database

    Steps:
    1. Build user dictionary
    2. Insert into MongoDB
    3. Return created document
    """

    doc = {
        'name': name,
        'email': email,
        'password': password,   # should already be hashed!
        'role': role,
        'is_approved': is_approved,
        'created_at': datetime.utcnow(),  # store current time
    }

    # Insert into "users" collection
    result = mongo.db.users.insert_one(doc)

    # Add generated _id to document
    doc['_id'] = result.inserted_id

    return doc


def create_university(user_id: str, institution_name: str):
    """
    Create university record linked to a user
    """

    from bson import ObjectId

    doc = {
        'user_id': ObjectId(user_id),  # link to user
        'institution_name': institution_name,
        'is_verified': False,          # default = not verified
        'created_at': datetime.utcnow(),
    }

    mongo.db.universities.insert_one(doc)
    return doc


def create_student(user_id: str, student_id: str):
    """
    Create student record linked to a user
    """

    from bson import ObjectId

    doc = {
        'user_id': ObjectId(user_id),  # link to user
        'student_id': student_id,
        'created_at': datetime.utcnow(),
    }

    mongo.db.students.insert_one(doc)
    return doc