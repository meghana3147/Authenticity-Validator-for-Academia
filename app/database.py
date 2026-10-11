
import os
from flask_pymongo import PyMongo

mongo = PyMongo()

def init_db(app):
    app.config["MONGO_URI"] = os.environ.get("MONGO_URL")
    mongo.init_app(app)
