"""Application factory."""
import logging
import os

from flask import Flask, make_response, send_from_directory

from .config import Config
from .extensions import db, migrate


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Surface app INFO logs (e.g. the email log-fallback) in dev.
    logging.basicConfig(
        level=app.config.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("app").setLevel(app.config.get("LOG_LEVEL", "INFO"))

    db.init_app(app)
    # import models so Alembic autogenerate + create_all see the metadata
    from . import models  # noqa: F401

    migrate.init_app(app, db)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    # PWA assets at the site root so the service worker can claim full scope.
    @app.route("/manifest.json")
    def pwa_manifest():
        return send_from_directory(
            app.static_folder,
            "manifest.json",
            mimetype="application/manifest+json",
        )

    @app.route("/sw.js")
    def pwa_service_worker():
        response = make_response(
            send_from_directory(
                app.static_folder,
                "sw.js",
                mimetype="application/javascript",
            )
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/offline.html")
    def pwa_offline():
        return send_from_directory(app.static_folder, "offline.html")

    @app.route("/icons/<path:filename>")
    def pwa_icons(filename):
        return send_from_directory(os.path.join(app.static_folder, "icons"), filename)

    # Blueprints
    from .blueprints.admin import bp as admin_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.content import bp as content_bp
    from .blueprints.suggestions import bp as suggestions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(suggestions_bp)

    # CLI commands (e.g. `flask create-admin`)
    from .cli import register_cli

    register_cli(app)

    # Ensure the object-storage bucket exists (best-effort; app still boots if the
    # storage backend is unreachable, so text-only flows keep working).
    if app.config.get("STORAGE_ENDPOINT"):
        from .services.storage import ensure_bucket

        with app.app_context():
            try:
                ensure_bucket()
            except Exception:  # noqa: BLE001
                app.logger.warning("Could not ensure storage bucket at startup.")

    return app
