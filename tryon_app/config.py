import os


def init_config(app):
    """Initialize configuration values from environment with sensible defaults."""
    app.config.setdefault("TRYON_API_KEY", os.getenv("TRYON_API_KEY", "ta_48b22e1d630f45cd8f492718fbe1b96d"))
    app.config.setdefault("TRYON_API_URL", os.getenv("TRYON_API_URL", "https://tryon-api.com/api/v1"))
