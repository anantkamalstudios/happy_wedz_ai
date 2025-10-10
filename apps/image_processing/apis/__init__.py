from apps.image_processing.apis.makeup_image_apis import (
    images_bp,
    products_bp,
    product_categories_bp
    )

def register_image_processing_routes(app):
    app.register_blueprint(images_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(product_categories_bp)