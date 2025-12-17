# # core/__init__.py
# from flask import Flask
# import config
# from .extensions import db, init_cloudinary
# from apis.clothes import clothes_bp
# from apis.jewelry import jewelry_bp
# from apis.catalog import catalog_bp
# from apis.create_category import create_category_bp

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(config.Config)

#     # init extensions
#     db.init_app(app)
#     init_cloudinary(app)

#     # register blueprints
#     app.register_blueprint(clothes_bp, url_prefix="/tryon")
#     app.register_blueprint(jewelry_bp, url_prefix="/tryon")
#     app.register_blueprint(catalog_bp, url_prefix="/catalog")
#     app.register_blueprint(create_category_bp, url_prefix="/create_category")

#     return app
