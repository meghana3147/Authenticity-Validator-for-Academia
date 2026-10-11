
# -------------------- STEP 1: LOAD ENVIRONMENT VARIABLES --------------------

import os
import certifi
from dotenv import load_dotenv

load_dotenv()

# SSL certificate configuration for secure MongoDB Atlas connections
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


# -------------------- STEP 2: IMPORT LIBRARIES --------------------

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from app.database import mongo


# -------------------- STEP 3: INITIALIZE EXTENSIONS --------------------

login_manager = LoginManager()
bcrypt = Bcrypt()


# -------------------- STEP 4: DATABASE HELPER --------------------

def get_db():
    return mongo.db


# -------------------- STEP 5: ENSURE DATABASE NAME --------------------

def _ensure_db_in_uri(uri: str, db_name: str = "acadchain") -> str:
    from urllib.parse import urlparse, urlunparse

    parsed_uri = urlparse(uri)

    if not parsed_uri.path or parsed_uri.path == "/":
        parsed_uri = parsed_uri._replace(path=f"/{db_name}")

    return urlunparse(parsed_uri)


# -------------------- STEP 6: CREATE FLASK APPLICATION --------------------

def create_app():
    app = Flask(__name__)

    # Read the Render environment variable first.
    # MONGO_URI is supported as a fallback.
    raw_uri = os.getenv("MONGO_URL") or os.getenv("MONGO_URI")

    if not raw_uri:
        raise RuntimeError(
            "MongoDB connection string is missing. "
            "Set MONGO_URL in Render Environment settings."
        )

    mongo_uri = _ensure_db_in_uri(raw_uri)

    # Application secret
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY is missing. Set it in Render Environment settings."
        )

    # MongoDB configuration
    app.config["MONGO_URI"] = mongo_uri
    app.config["MONGO_DBNAME"] = "acadchain"

    # Certificate upload configuration
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(__file__),
        "static",
        "uploads",
        "certificates"
    )

    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize Flask extensions
    mongo.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # -------------------- STEP 7: IMPORT BLUEPRINTS --------------------

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.university import university_bp
    from app.routes.student import student_bp
    from app.routes.employer import employer_bp
    from app.routes.main import main_bp

    # -------------------- STEP 8: REGISTER BLUEPRINTS --------------------

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(university_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(employer_bp)

    return app
