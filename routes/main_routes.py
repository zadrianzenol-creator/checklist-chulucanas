from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import db
from models.local import Local, Mesa
from models.user import User
from services.checklist_service import ChecklistService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = ChecklistService.stats_generales()
    por_local = ChecklistService.stats_por_local()
    return render_template("dashboard.html", stats=stats, por_local=por_local)


@main_bp.route("/locales")
@login_required
def locales():
    q = (request.args.get("q") or "").strip().lower()
    ubicacion = (request.args.get("ubicacion") or "").strip().upper()

    query = Local.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Local.nombre.ilike(like), Local.direccion.ilike(like), Local.codigo.ilike(like))
        )
    if ubicacion in ("URBANA", "RURAL"):
        query = query.filter(Local.ubicacion == ubicacion)

    locales_list = query.order_by(Local.ubicacion.asc(), Local.nombre.asc()).all()
    stats = ChecklistService.stats_generales()
    return render_template(
        "locales.html",
        locales=locales_list,
        stats=stats,
        q=q,
        ubicacion=ubicacion,
    )


@main_bp.route("/locales/<int:local_id>")
@login_required
def detalle_local(local_id):
    local = Local.query.get_or_404(local_id)
    mesas = local.mesas.all()
    stats = ChecklistService.stats_generales()
    return render_template("detalle_local.html", local=local, mesas=mesas, stats=stats)


# ---------------------------------------------------------------------------
# API (AJAX)
# ---------------------------------------------------------------------------
@main_bp.route("/api/mesas/<int:mesa_id>/estado", methods=["POST"])
@login_required
def api_set_estado(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    data = request.get_json(silent=True) or {}
    estado = (data.get("estado") or "PENDIENTE").upper()
    observacion = data.get("observacion", "")

    try:
        mesa = ChecklistService.set_estado(
            mesa,
            estado,
            observacion,
            user=current_user,
            ip=request.remote_addr or "",
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "mesa": mesa.to_dict()})


@main_bp.route("/api/stats")
@login_required
def api_stats():
    stats = ChecklistService.stats_generales()
    por_local = ChecklistService.stats_por_local()
    return jsonify({"stats": stats, "por_local": por_local})


@main_bp.route("/ping")
def ping():
    return jsonify({"status": "ok"}), 200