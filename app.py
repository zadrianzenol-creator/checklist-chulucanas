import os
import json
import traceback

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user

from config import Config
from database import db, init_db
from models.user import User
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = ""
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    ENDPOINTS_PERMITIDOS_OPERADOR = {
        "auth.login",
        "auth.logout",
        "main.dashboard",
        "main.locales",
        "main.detalle_local",
        "main.api_set_estado",
        "main.api_stats",
        "main.ping",
        "static",
    }

    @app.before_request
    def reglas_globales():
        # Actualiza el registro de actividad del usuario autenticado
        if current_user.is_authenticated:
            try:
                current_user.last_active = db.func.now()
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Restricción de roles: operador solo puede ver y marcar mesas
        if current_user.is_authenticated and current_user.role == "operador":
            endpoint = request.endpoint
            if endpoint and endpoint not in ENDPOINTS_PERMITIDOS_OPERADOR:
                abort(403)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        try:
            from models.activity import ActivityLog

            entry = ActivityLog(
                tipo="ERROR_500",
                detalle=f"{request.method} {request.path} - {e}"[:2000],
                ip_address=request.remote_addr or "",
            )
            db.session.add(entry)
            db.session.commit()
        except Exception:
            db.session.rollback()
        app.logger.error(
            "Error 500 en %s %s:\n%s",
            request.method,
            request.path,
            traceback.format_exc(),
        )
        return render_template("errors/500.html"), 500

    return app


def seed_from_json():
    from models.local import Local, Mesa

    if Local.query.first() is not None:
        return

    seed_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if not os.path.exists(seed_path):
        print(">> seed_data.json no encontrado, saltando seed.")
        return

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    locales = data.get("locales", [])
    for item in locales:
        local = Local(
            codigo=item.get("codigo", ""),
            nombre=item.get("nombre", ""),
            direccion=item.get("direccion", ""),
            ubicacion=item.get("ubicacion", "URBANA"),
            pabellon=item.get("pabellon", ""),
            numero_ca=item.get("numero_ca", ""),
            total_electores=item.get("total_electores", 0),
            total_mesas=item.get("total_mesas", 0),
        )
        db.session.add(local)
        db.session.flush()

        for m in item.get("mesas", []):
            mesa = Mesa(
                local_id=local.id,
                orden=m.get("orden", 0),
                numero=m.get("numero", ""),
                aula=m.get("aula", ""),
                piso=m.get("piso", ""),
                pabellon=m.get("pabellon", ""),
                electores=m.get("electores", 0),
                electores_discapacidad=m.get("electores_discapacidad", 0),
                estado="PENDIENTE",
            )
            db.session.add(mesa)

    db.session.commit()
    print(f">> {len(locales)} locales y sus mesas creados desde seed_data.json")


def seed_admin():
    if User.query.filter_by(username="admin").first() is not None:
        return

    admin = User(
        username="admin",
        full_name="Administrador",
        role="admin",
        is_active=True,
    )
    admin.set_password(os.getenv("ADMIN_PASSWORD", "admin123"))
    db.session.add(admin)
    db.session.commit()
    print(">> Admin creado (user: admin / pass: admin123)")


app = create_app()

with app.app_context():
    init_db()
    seed_from_json()
    seed_admin()

if __name__ == "__main__":
    print(">> Checklist Electoral Chulucanas 2026: http://localhost:5050")
    app.run(debug=True, host="0.0.0.0", port=5050)