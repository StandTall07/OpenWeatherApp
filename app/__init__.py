
from flask import Flask
from .routes import main_bp
from dotenv import load_dotenv
import os

def create_app():
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    
    return app
