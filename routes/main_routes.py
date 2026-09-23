from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import db
from models.local import Local, Mesa
from models.lote import Lote
from models.observacion import Observacion
from models.user import User
from services.checklist_service import ACCION_POR_ESTADO, ChecklistService, TRANSICIONES
from services.lote_service import LoteService
from utils.decorators import role_required

main_bp = Blueprint("main", __name__)


def _acciones_mesa(mesa, user):
    """Destinos de transición disponibles según rol y asignación."""
    destinos = list(TRANSICIONES.get(mesa.estado, ()))
    if user.role == "admin":
        return destinos
    if user.role == "digitador":
        if mesa.digitador_id != user.id:
            return []
        return [d for d in destinos if ACCION_POR_ESTADO.get(d) == "digitador"]
    if user.role == "recepcion":
        return [d for d in destinos if ACCION_POR_ESTADO.get(d) == "recepcion"]
    return []


def _inicio_por_rol():
    if current_user.role == "digitador":
        return url_for("main.bandeja")
    if current_user.role == "recepcion":
        return url_for("main.recepcion")
    return url_for("main.dashboard")


@main_bp.route("/")
@login_required
def index():
    return redirect(_inicio_por_rol())


# ---------------------------------------------------------------------------
# Dashboard (Responsable / admin)
# ---------------------------------------------------------------------------
@main_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    stats = ChecklistService.stats_generales()
    por_local = ChecklistService.stats_por_local()
    max_estado = max(stats["por_estado"].values()) if stats["por_estado"] else 0

    loc_id = request.args.get("local_id", type=int)
    dig_id = request.args.get("digitador_id", type=int)
    estado = (request.args.get("estado") or "").strip().upper()
    q = (request.args.get("q") or "").strip().lower()

    query = Mesa.query.join(Local)
    if loc_id:
        query = query.filter(Mesa.local_id == loc_id)
    if dig_id:
        query = query.filter(Mesa.digitador_id == dig_id)
    if estado:
        query = query.filter(Mesa.estado == estado)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Mesa.numero.ilike(like),
                Local.nombre.ilike(like),
                Local.codigo.ilike(like),
            )
        )

    mesas = (
        query.order_by(Local.nombre.asc(), Mesa.orden.asc())
        .limit(400)
        .all()
    )
    locales = Local.query.order_by(Local.nombre.asc()).all()
    digitadores = (
        User.query.filter_by(role="digitador", is_active=True)
        .order_by(User.full_name.asc())
        .all()
    )
    return render_template(
        "dashboard.html",
        stats=stats,
        por_local=por_local,
        max_estado=max_estado,
        mesas=mesas,
        locales=locales,
        digitadores=digitadores,
        filtros={"local_id": loc_id, "digitador_id": dig_id, "estado": estado, "q": q},
    )


# ---------------------------------------------------------------------------
# Bandeja del digitador
# ---------------------------------------------------------------------------
@main_bp.route("/bandeja")
@role_required("digitador")
def bandeja():
    base = Mesa.query.filter(Mesa.digitador_id == current_user.id)

    digital = base.filter(Mesa.estado.in_(["PENDIENTE", "FOTO RECIBIDA", "EN REGISTRO"])).all()
    calidad = base.filter(Mesa.estado == "EN CONTROL DE CALIDAD").all()
    terminadas = base.filter(
        Mesa.estado.in_(["REGISTRADA", "CONFORME", "CERRADA", "OBSERVADA"])
    ).count()

    def agrupar(mesas):
        grupos = {}
        for m in mesas:
            grupos.setdefault(m.local_id, {"local": m.local, "mesas": []})["mesas"].append(m)
        orden = sorted(grupos.values(), key=lambda g: g["local"].nombre)
        return orden

    return render_template(
        "bandeja.html",
        digital=agrupar(digital),
        calidad=agrupar(calidad),
        terminadas=terminadas,
        conteo={
            "pendientes": base.filter(Mesa.estado == "PENDIENTE").count(),
            "fotos": base.filter(Mesa.estado == "FOTO RECIBIDA").count(),
            "registro": base.filter(Mesa.estado == "EN REGISTRO").count(),
            "calidad": len(calidad),
            "observadas": base.filter(Mesa.estado == "OBSERVADA").count(),
        },
    )


# ---------------------------------------------------------------------------
# Recepción y custodia
# ---------------------------------------------------------------------------
@main_bp.route("/recepcion")
@role_required("recepcion", "admin")
def recepcion():
    llegada = (
        Mesa.query.join(Local)
        .filter(Mesa.estado == "REGISTRADA")
        .order_by(Local.nombre.asc(), Mesa.orden.asc())
        .all()
    )
    preparar = (
        Mesa.query.join(Local)
        .filter(Mesa.estado == "PENDIENTE DE CONTROL")
        .order_by(Local.nombre.asc(), Mesa.orden.asc())
        .all()
    )
    archivo = (
        Mesa.query.join(Local)
        .filter(Mesa.estado == "CONFORME")
        .order_by(Local.nombre.asc(), Mesa.orden.asc())
        .all()
    )
    observadas = (
        Mesa.query.join(Local)
        .filter(Mesa.estado == "OBSERVADA")
        .order_by(Mesa.updated_at.desc())
        .all()
    )
    lotes = Lote.query.order_by(Lote.id.desc()).all()
    digitadores = (
        User.query.filter_by(role="digitador", is_active=True)
        .order_by(User.full_name.asc())
        .all()
    )
    return render_template(
        "recepcion.html",
        llegada=llegada,
        preparar=preparar,
        archivo=archivo,
        observadas=observadas,
        lotes=lotes,
        digitadores=digitadores,
    )


# ---------------------------------------------------------------------------
# Lotes
# ---------------------------------------------------------------------------
@main_bp.route("/lotes")
@role_required("recepcion", "admin")
def lotes():
    lotes = Lote.query.order_by(Lote.id.desc()).all()
    return render_template("lotes.html", lotes=lotes)


@main_bp.route("/lotes/<int:lote_id>")
@role_required("recepcion", "admin")
def detalle_lote(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    mesas = lote.mesas.all()
    digitadores = (
        User.query.filter_by(role="digitador", is_active=True)
        .order_by(User.full_name.asc())
        .all()
    )
    return render_template("lotes_detalle.html", lote=lote, mesas=mesas, digitadores=digitadores)


# ---------------------------------------------------------------------------
# Locales y mesas
# ---------------------------------------------------------------------------
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
    for m in mesas:
        m.acciones = _acciones_mesa(m, current_user)
    stats = ChecklistService.stats_generales()
    digitadores = (
        User.query.filter_by(role="digitador", is_active=True)
        .order_by(User.full_name.asc())
        .all()
    )
    return render_template(
        "detalle_local.html",
        local=local,
        mesas=mesas,
        stats=stats,
        digitadores=digitadores,
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@main_bp.route("/api/mesas/<int:mesa_id>/transicion", methods=["POST"])
@login_required
def api_transicion(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    data = request.get_json(silent=True) or {}
    destino = (data.get("estado") or "").upper().strip()
    observacion = data.get("observacion", "")

    try:
        mesa = ChecklistService.transicionar(
            mesa,
            destino,
            user=current_user,
            ip=request.remote_addr or "",
            observacion=observacion,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "mesa": mesa.to_dict()})


@main_bp.route("/api/mesas/<int:mesa_id>/trazabilidad")
@login_required
def api_trazabilidad(mesa_id):
    Mesa.query.get_or_404(mesa_id)
    data = ChecklistService.trazabilidad_mesa(mesa_id)
    return jsonify({"ok": True, **data})


@main_bp.route("/api/mesas/<int:mesa_id>/asignar", methods=["POST"])
@role_required("admin")
def api_asignar(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    data = request.get_json(silent=True) or {}
    dig_id = data.get("digitador_id")
    dig_id = int(dig_id) if dig_id else None

    if dig_id is not None:
        dig = User.query.get(dig_id)
        if dig is None or dig.role != "digitador":
            return jsonify({"ok": False, "error": "El usuario elegido no es un digitador."}), 400

    mesa.digitador_id = dig_id
    mesa.updated_by = current_user.id
    mesa.updated_at = db.func.now()
    db.session.add(mesa)
    db.session.commit()
    nombre = mesa.digitador.full_name if mesa.digitador else None
    return jsonify({"ok": True, "digitador": nombre})


@main_bp.route("/api/mesas/<int:mesa_id>/llegada", methods=["POST"])
@role_required("recepcion", "admin")
def api_llegada(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    try:
        mesa = LoteService.llegada_fisica(mesa, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "mesa": mesa.to_dict()})


@main_bp.route("/api/mesas/<int:mesa_id>/archivar", methods=["POST"])
@role_required("recepcion", "admin")
def api_archivar(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    try:
        mesa = LoteService.archivar_mesa(mesa, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "mesa": mesa.to_dict()})


# --- Lotes ---
@main_bp.route("/api/lotes/crear", methods=["POST"])
@role_required("recepcion", "admin")
def api_lotes_crear():
    data = request.get_json(silent=True) or {}
    mesa_ids = data.get("mesa_ids") or []
    try:
        lote = LoteService.crear_lote(mesa_ids, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "lote": lote.to_dict()})


@main_bp.route("/api/lotes/<int:lote_id>/entregar", methods=["POST"])
@role_required("recepcion", "admin")
def api_lotes_entregar(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    data = request.get_json(silent=True) or {}
    dig_id = data.get("digitador_id") or data.get("digitador")
    try:
        lote = LoteService.entregar_lote(lote, dig_id, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "lote": lote.to_dict()})


@main_bp.route("/api/lotes/<int:lote_id>/recibir", methods=["POST"])
@role_required("digitador", "recepcion", "admin")
def api_lotes_recibir(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    try:
        lote = LoteService.recibir_lote(lote, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "lote": lote.to_dict()})


@main_bp.route("/api/lotes/<int:lote_id>/archivar", methods=["POST"])
@role_required("recepcion", "admin")
def api_lotes_archivar(lote_id):
    lote = Lote.query.get_or_404(lote_id)
    try:
        cuenta = LoteService.archivar_lote(lote, user=current_user, ip=request.remote_addr or "")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "cuenta": cuenta})


@main_bp.route("/api/stats")
@login_required
def api_stats():
    stats = ChecklistService.stats_generales()
    por_local = ChecklistService.stats_por_local()
    return jsonify({"stats": stats, "por_local": por_local})


@main_bp.route("/ping")
def ping():
    return jsonify({"status": "ok"}), 200