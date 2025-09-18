# app_back.py
from flask import Flask
from db import db
from flask_cors import CORS
from config import Config

# db instance is imported from db.py

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    db.init_app(app)

    # Import routes
    from routes import register_routes
    register_routes(app)

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Import models to register them with SQLAlchemy before creating tables
        import models
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
