import os
from dotenv import load_dotenv
import logging
from config import create_app
from apps.image_processing.models.makeup_image_model import db
from flask import got_request_exception



# ----------------------------
# Ensure rembg can find the U2NET model
# ----------------------------
os.environ["U2NET_HOME"] = "/root/.u2net"

model_path = os.path.join(os.environ["U2NET_HOME"], "u2net.onnx")
if not os.path.isfile(model_path):
    raise FileNotFoundError(f"U2NET model not found at {model_path}. Please download it.")

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

# ----------------------------
# Determine environment
# ----------------------------
env = os.getenv("FLASK_ENV", "production").lower()
debug = env == "development"

print(f"🔧 Environment: {env.upper()} | Debug: {debug}")

# ----------------------------
# Create Flask app
# ----------------------------
app = create_app()

# ----------------------------
# Create logs directory
# ----------------------------
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# ----------------------------
# Setup Python logging (console + file)
# ----------------------------
log_file = os.path.join(log_dir, "error.log")

# Formatter
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler (only for development)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# ----------------------------
# Log Flask internal exceptions
# ----------------------------
def log_exception(sender, exception, **extra):
    logging.error("Exception occurred", exc_info=exception)

got_request_exception.connect(log_exception, app)

# ----------------------------
# Integrate with Gunicorn logging (if running under Gunicorn)
# ----------------------------
if "gunicorn.error" in logging.Logger.manager.loggerDict:
    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_error_logger.handlers
    app.logger.setLevel(gunicorn_error_logger.level)

# ----------------------------
# Initialize database inside app context
# ----------------------------
with app.app_context():
    db.create_all()

# ----------------------------
# Run Flask app (only used if running directly)
# ----------------------------
if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", 5001))

    print(f"🚀 Starting Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=debug)












# import os
# from dotenv import load_dotenv

# from config import create_app
# from apps.image_processing.models.makeup_image_model import db

# # Ensure rembg can find the U2NET model
# os.environ["U2NET_HOME"] = "/root/.u2net"

# # Optional: check if model exists
# model_path = os.path.join(os.environ["U2NET_HOME"], "u2net.onnx")
# if not os.path.isfile(model_path):
#     raise FileNotFoundError(f"U2NET model not found at {model_path}. Please download it.")

# # Load environment variables from .env
# load_dotenv()

# app = create_app()

# # Initialize database inside app context
# with app.app_context():
#     db.create_all()

# if __name__ == "__main__":
#     # Read host, port, and debug values from .env
#     host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
#     port = int(os.getenv("FLASK_RUN_PORT", 5001))
#     debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

#     app.run(host=host, port=port, debug=debug)
