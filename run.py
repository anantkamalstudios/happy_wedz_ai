# from apps.image_processing import create_app
# from apps.image_processing.models.makeup_image_model import db

# app = create_app()

# with app.app_context():
#     db.create_all()

# if __name__ == "__main__":
#     app.run(debug=True)



import os
from dotenv import load_dotenv

from config import create_app
from apps.image_processing.models.makeup_image_model import db

# Load environment variables from .env
load_dotenv()

app = create_app()

# Initialize database inside app context
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Read host, port, and debug values from .env
    # host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    # port = int(os.getenv("FLASK_RUN_PORT", 5001))
    # debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # app.run(host=host, port=port, debug=debug)

    app.run(debug=True)
