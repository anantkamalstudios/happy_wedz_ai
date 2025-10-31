# from apps.image_processing import create_app
# from apps.image_processing.models.makeup_image_model import db

# app = create_app()

# with app.app_context():
#     db.create_all()

# if __name__ == "__main__":
#     app.run(debug=True)


# 30/10/2025
# import os
# from dotenv import load_dotenv

# from config import create_app
# from apps.image_processing.models.makeup_image_model import db

# # Load environment variables from .env
# load_dotenv()

# app = create_app()

# print("------------------------server is running----------------------------")

# # Initialize database inside app context
# with app.app_context():
#     db.create_all()

# if __name__ == "__main__":
#     # Read host, port, and debug values from .env
#     # host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
#     # port = int(os.getenv("FLASK_RUN_PORT", 5001))
#     # debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

#     # app.run(host=host, port=port, debug=debug)

#     app.run(debug=True)



# Today 4:36PM
# import os
# from dotenv import load_dotenv
# from config import create_app
# from apps.image_processing.models.makeup_image_model import db

# # Load environment variables
# load_dotenv()

# # Create Flask app instance
# app = create_app()

# print("------------------------ Server is running ----------------------------")

# # Initialize database
# with app.app_context():
#     db.create_all()

# # Optional root route for testing
# @app.route("/")
# def index():
#     return "ðŸŽ‰ HappyWedz AI Backend is Live!"

# # Expose app for Gunicorn / WSGI
# application = app

# if __name__ == "__main__":
#     # Read configuration from environment variables (or fallback)
#     host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
#     port = int(os.getenv("FLASK_RUN_PORT", 5000))
#     debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

#     # Run Flask app directly (for local development)
#     app.run(host=host, port=port, debug=debug)




import os
from dotenv import load_dotenv
from config import create_app
from apps.image_processing.models.makeup_image_model import db
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Create Flask app instance
app = create_app()

# ---------------- Add logging setup here ---------------- #
# Ensure logs directory exists
if not os.path.exists("logs"):
    os.mkdir("logs")

# Create formatter
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s"
)

# File handler (for saving logs)
file_handler = RotatingFileHandler("logs/error.log", maxBytes=5_000_000, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Console handler (for terminal output)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add both handlers
app.logger.addHandler(file_handler)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)

# Log startup message
app.logger.info("------------------------ Server is running ----------------------------")

# Initialize database
with app.app_context():
    db.create_all()

# Optional root route for testing
@app.route("/")
def index():
    return "🎉 HappyWedz AI Backend is Live!"


# Example of logging requests/responses
from flask import request

@app.before_request
def log_request():
    app.logger.info(f"➡️  {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response(response):
    app.logger.info(f"⬅️  {response.status} for {request.method} {request.path}")
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception("🔥 Unhandled Exception occurred:")
    return {"error": str(e)}, 500

# Expose app for Gunicorn / WSGI
application = app

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Run Flask app directly (for local development)
    app.run(host=host, port=port, debug=debug)
