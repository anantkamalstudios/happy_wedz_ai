from apps.image_processing import create_app
from apps.image_processing.models.makeup_image_model import db

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
