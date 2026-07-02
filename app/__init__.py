# -------------------- STEP 1: LOAD ENVIRONMENT VARIABLES --------------------

# This loads variables from a file named ".env"
# Example of .env:
# MONGO_URI=mongodb://localhost:27017/acadchain
# SECRET_KEY=mysecret

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")  
# IMPORTANT: This must run BEFORE using os.getenv()


# -------------------- STEP 2: FIX SSL ISSUE (MAINLY FOR macOS) --------------------

# Some systems (especially macOS) don’t automatically trust SSL certificates.
# This can cause errors when connecting to MongoDB Atlas (cloud database).
# certifi gives us a trusted certificate bundle.

import certifi, os

# Set SSL certificate file if not already set
# These help Python verify secure connections (HTTPS / TLS)
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


# -------------------- STEP 3: IMPORT REQUIRED LIBRARIES --------------------

from flask import Flask

# Flask-Login → handles login sessions (who is logged in)
from flask_login import LoginManager  

# Flask-Bcrypt → used to hash passwords securely
from flask_bcrypt import Bcrypt        

# Import MongoDB connection object from your project
from app.database import mongo


# -------------------- STEP 4: CREATE EXTENSION OBJECTS --------------------

# These are created globally but connected to app later
login_manager = LoginManager()
bcrypt = Bcrypt()


# -------------------- STEP 5: HELPER FUNCTION TO GET DATABASE --------------------

def get_db():
    # This returns the MongoDB database object
    # You can use it like: db = get_db()
    return mongo.db


# -------------------- STEP 6: FIX MONGODB URI IF NEEDED --------------------

def _ensure_db_in_uri(uri: str, db_name: str = "acadchain") -> str:
    """
    WHY THIS FUNCTION EXISTS:

    MongoDB connection string (URI) MUST include a database name.

    Example:
    ❌ Wrong: mongodb://localhost:27017/
    ✅ Correct: mongodb://localhost:27017/acadchain

    Some cloud URIs (like MongoDB Atlas) may miss the DB name.
    This function checks and adds it if needed.
    """

    from urllib.parse import urlparse, urlunparse

    # Break the URI into parts
    p = urlparse(uri)

    # If no database is mentioned (path is empty or just '/')
    if not p.path or p.path == '/':
        # Add "/acadchain" (or given db_name)
        fixed = p._replace(path=f'/{db_name}')
        return urlunparse(fixed)

    # If already correct, return as-is
    return uri


# -------------------- STEP 7: CREATE THE FLASK APP --------------------

def create_app():
    """
    This is the MAIN function that builds and configures your Flask app.
    Flask calls this to create your application.
    """

    # Create Flask app object
    app = Flask(__name__)


    # -------------------- STEP 8: DATABASE CONFIG --------------------

    # Get MongoDB URI from .env file
    # If not found, use local MongoDB as default
    raw_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/acadchain")

    # Make sure database name exists in URI
    mongo_uri = _ensure_db_in_uri(raw_uri)

    # Print URI (for debugging)
    print("Mongo URI:", mongo_uri)


    # -------------------- STEP 9: APP CONFIGURATION --------------------

    # Secret key is used for:
    # - Sessions
    # - Login security
    # - Flash messages
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "acadchain-dev-secret-2024"  # default (not safe for production)
    )

    # MongoDB settings
    app.config["MONGO_URI"] = mongo_uri
    app.config["MONGO_DBNAME"] = "acadchain"


    # -------------------- STEP 10: FILE UPLOAD SETTINGS --------------------

    # This is where uploaded certificate files will be stored
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(__file__),   # current folder
        "static",                   # inside static
        "uploads",
        "certificates"
    )

    # Maximum file size allowed (default = 16 MB)
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )

    # Create the folder if it doesn’t exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


    # -------------------- STEP 11: CONNECT EXTENSIONS TO APP --------------------

    # Now we attach earlier-created objects to this app
    mongo.init_app(app)          # connect MongoDB
    bcrypt.init_app(app)         # enable password hashing
    login_manager.init_app(app)  # enable login system

    # If user tries to access protected page → redirect here
    login_manager.login_view = "auth.login"

    # Message category (used in flash messages)
    login_manager.login_message_category = "info"


    # -------------------- STEP 12: IMPORT ROUTES (BLUEPRINTS) --------------------

    # Blueprints = separate modules for different parts of app
    from app.routes.auth       import auth_bp
    from app.routes.admin      import admin_bp
    from app.routes.university import university_bp
    from app.routes.student    import student_bp
    from app.routes.employer   import employer_bp
    from app.routes.main       import main_bp


    # -------------------- STEP 13: REGISTER ROUTES --------------------

    # This tells Flask: "use these route modules"
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(university_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(employer_bp)


    # -------------------- STEP 14: RETURN APP --------------------

    # Finally return the ready-to-run Flask app
    return app