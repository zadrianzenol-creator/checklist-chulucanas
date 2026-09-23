from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from database import db
from models.user import ROLES, User
from utils.decorators import admin_required

auth_bp = Blueprint("auth", __name__)

ROLES_VALIDOS = ROLES


def landig_url(user):
    """Página inicial según el rol."""
    if user.role == "digitador":
        return url_for("main.bandeja")
    if user.role == "recepcion":
        return url_for("main.recepcion")
    return url_for("main.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(landig_url(current_user))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            error = "Usuario o contraseña incorrectos."
        elif not user.is_active:
            error = "La cuenta está desactivada. Contacta al administrador."
        else:
            login_user(user, remember=True)
            user.last_active = db.func.now()
            db.session.commit()
            return redirect(landig_url(user))

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Gestión de usuarios (solo admin)
# ---------------------------------------------------------------------------
@auth_bp.route("/usuarios")
@admin_required
def usuarios():
    from models.local import Mesa

    users = User.query.order_by(User.created_at.desc()).all()
    asignados = (
        db.session.query(Mesa.digitador_id, db.func.count(Mesa.id))
        .filter(Mesa.digitador_id != None)  # noqa: E711
        .group_by(Mesa.digitador_id)
        .all()
    )
    conteo = {u_id: n for u_id, n in asignados}
    return render_template(
        "usuarios.html",
        users=users,
        roles=ROLES_VALIDOS,
        conteo_mesas=conteo,
    )


@auth_bp.route("/usuarios/crear", methods=["POST"])
@admin_required
def crear_usuario():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    full_name = (request.form.get("full_name") or "").strip()
    role = request.form.get("role") or "digitador"

    if not username or not password:
        flash("Usuario y contraseña son obligatorios.", "error")
        return redirect(url_for("auth.usuarios"))

    if role not in ROLES_VALIDOS:
        role = "digitador"

    if User.query.filter_by(username=username).first():
        flash(f"El usuario '{username}' ya existe.", "error")
        return redirect(url_for("auth.usuarios"))

    user = User(username=username, full_name=full_name, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"Usuario '{username}' creado correctamente.", "success")
    return redirect(url_for("auth.usuarios"))


@auth_bp.route("/usuarios/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_usuario(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"ok": False, "error": "No puedes desactivar tu propia cuenta."}), 400
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({"ok": True, "is_active": user.is_active})


@auth_bp.route("/usuarios/<int:user_id>/reset", methods=["POST"])
@admin_required
def reset_usuario(user_id):
    user = User.query.get_or_404(user_id)
    password = (request.form.get("password") or "").strip()
    if len(password) < 4:
        return jsonify({"ok": False, "error": "La contraseña debe tener al menos 4 caracteres."}), 400
    user.set_password(password)
    db.session.commit()
    return jsonify({"ok": True, "message": "Contraseña actualizada."})