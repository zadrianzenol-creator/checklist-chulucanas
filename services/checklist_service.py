from database import db
from models.activity import ActivityLog
from models.local import ESTADOS, Local, Mesa


class ChecklistService:
    @staticmethod
    def estados():
        return ESTADOS

    @staticmethod
    def set_estado(mesa, estado, observacion="", user=None, ip=""):
        """Marca el estado de una mesa y registra la actividad."""
        estado = (estado or "").upper().strip()
        if estado not in ESTADOS:
            raise ValueError(f"Estado invalido: {estado}")

        mesa.estado = estado
        mesa.observacion = (observacion or "").strip()
        if user is not None:
            mesa.updated_by = user.id
        mesa.updated_at = db.func.now()
        db.session.add(mesa)

        log = ActivityLog(
            user_id=user.id if user else None,
            mesa_id=mesa.id,
            tipo=f"MESA_{estado}",
            detalle=f"Mesa {mesa.numero} marcada como {estado}",
            ip_address=ip,
        )
        db.session.add(log)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return mesa

    @staticmethod
    def stats_generales():
        total_locales = Local.query.count()
        total_mesas = Mesa.query.count()
        total_electores = db.session.query(db.func.sum(Mesa.electores)).scalar() or 0

        verificadas = Mesa.query.filter_by(estado="VERIFICADA").count()
        observadas = Mesa.query.filter_by(estado="OBSERVADO").count()
        pendientes = Mesa.query.filter_by(estado="PENDIENTE").count()

        avance = round((verificadas / total_mesas * 100), 1) if total_mesas else 0
        pendiente_pct = round((pendientes / total_mesas * 100), 1) if total_mesas else 0
        observado_pct = round((observadas / total_mesas * 100), 1) if total_mesas else 0
        avanzado = verificadas + observadas

        urbanas = Local.query.filter_by(ubicacion="URBANA").count()
        rurales = Local.query.filter_by(ubicacion="RURAL").count()

        return {
            "total_locales": total_locales,
            "total_mesas": total_mesas,
            "total_electores": total_electores,
            "verificadas": verificadas,
            "observadas": observadas,
            "pendientes": pendientes,
            "avance": avance,
            "pendiente_pct": pendiente_pct,
            "observado_pct": observado_pct,
            "avanzado": avanzado,
            "urbanas": urbanas,
            "rurales": rurales,
        }

    @staticmethod
    def stats_por_local():
        locales = Local.query.order_by(Local.nombre.asc()).all()
        return [
            {
                "nombre": l.nombre,
                "verificadas": l.verificadas,
                "observadas": l.observadas,
                "pendientes": l.pendientes,
                "total": l.total_mesas,
            }
            for l in locales
        ]

    @staticmethod
    def estados_por_mesa(local_id):
        return dict(
            db.session.query(Mesa.estado, db.func.count(Mesa.id))
            .filter(Mesa.local_id == local_id)
            .group_by(Mesa.estado)
            .all()
        )