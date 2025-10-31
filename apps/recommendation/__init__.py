# from flask import Flask
# from flask_cors import CORS
# from db import db
# from config import Config
# from .apis import api_bp
# from .services.cache import reload_data

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)
    
#     CORS(app)
#     db.init_app(app)
    
#     # Register blueprints
#     app.register_blueprint(api_bp, url_prefix='/api')
    
#     # Load cache data
#     with app.app_context():
#         reload_data(db)
    
#     return app