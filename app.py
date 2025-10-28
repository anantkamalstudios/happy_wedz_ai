"""Top-level run script — uses application factory in `tryon_app` package."""

from tryon_app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
