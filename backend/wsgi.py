"""WSGI entrypoint. `flask run` and gunicorn both import `app` from here."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
