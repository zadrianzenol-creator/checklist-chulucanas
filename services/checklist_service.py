from database import db
from models.activity import ActivityLog
from models.observacion import Observacion
from models.local import ESTADOS, FASES, Local, Mesa

# Estado -> estados alcanzables directamente
TRANSICIONES = {
    "PENDIENTE": ("FOTO RECIBIDA",),
    "FOTO RECIBIDA": ("EN REGISTRO",),
    "EN REGISTRO": ("REGISTRADA",),
    "REGISTRADA": ("PENDIENTE DE CONTROL",),          # Recepción: llegada física
    "PENDIENTE DE CONTROL": (),                        # -> Calidad solo vía lote
    "EN CONTROL DE CALIDAD": ("CONFORME", "OBSERVADA"),
    "CONFORME": ("CERRADA",),                          # Recepción: archivo
    "OBSERVADA": ("CONFORME", "EN CONTROL DE CALIDAD"),
    "CERRADA": (),
}

# Quién marca cada estado (rol que ejecuta la acción)
ACCION_POR_ESTADO = {
    "FOTO RECIBIDA": "digitador",
    "EN REGISTRO": "digitador",
    "REGISTRADA": "digitador",
    "PENDIENTE DE CONTROL": "recepcion",
    "EN CONTROL DE CALIDAD": "recepcion",   # solo vía lote
    "CONFORME": "digitador",
    "OBSERVADA": "digitador",
    "CERRADA": "recepcion",
}

ESTADO_LABEL = {}

# Etiquetas bonitas por estado
LABELS = {
    "PENDIENTE": "Pendiente",
    "FOTO RECIBIDA": "Foto recibida",
    "EN REGISTRO": "En registro",
    "REGISTRADA": "Registrada",
    "PENDIENTE DE CONTROL": "Pend. de control",
    "EN CONTROL DE CALIDAD": "En control calidad",
    "CONFORME": "Conforme",
    "OBSERVADA": "Observada",
    "CERRADA": "Cerrada",
}


class ChecklistService:
    ESTADOS = ESTADOS
    TRANSICIONES = TRANSICIONES

    @staticmethod
    def etiqueta(estado):
        return LABELS.get(estado, estado)

    @staticmethod
    def slug(estado):
        return "-".join(estado.lower().split()).replace("ó", "o").replace("á", "a")

    @staticmethod
    def puede_transicionar(mesa, destino, user):
        """Valida transición, rol y asignación según la máquina de estados."""
        destino = (destino or "").strip().upper()
        if destino not in ESTADOS:
            return False, "Estado inválido."

        if destino not in TRANSICIONES.get(mesa.estado, ()):
            return False, f"La mesa {mesa.numero} no puede pasar de '{LABELS.get(mesa.estado, mesa.estado)}' a '{LABELS.get(destino, destino)}'."

        accion = ACCION_POR_ESTADO.get(destino, "admin")
        if user.role == "admin":
            return True, ""
        if user.role != accion:
            return False, "Tu rol no permite realizar esta acción."
        if accion == "digitador" and mesa.digitador_id != user.id:
            return False, "Esta mesa no está asignada a tu bandeja."
        return True, ""

    @staticmethod
    def transicionar(mesa, destino, user=None, ip="", observacion=None):
        """Ejecuta una transición validada y registra trazabilidad."""
        destino = (destino or "").strip().upper()
        if destino not in ESTADOS:
            raise ValueError("Estado inválido.")

        ok, error = ChecklistService.puede_transicionar(mesa, destino, user)
        if not ok:
            raise ValueError(error)

        if destino == "OBSERVADA":
            detalle = (observacion or "").strip()
            if not detalle:
                raise ValueError("Para marcar una mesa como OBSERVADA es necesario escribir la observación.")
            obs = Observacion(
                mesa_id=mesa.id,
                detalle=detalle,
                user_id=user.id if user else None,
                resuelta=False,
            )
            db.session.add(obs)
            mesa.observacion = detalle

        if destino == "CONFORME":
            # Resuelve las observaciones abiertas (quedan en el historial)
            for obs in mesa.observaciones.filter_by(resuelta=False).all():
                obs.resuelta = True
                obs.resuelta_por = user.id if user else None
                obs.resuelta_en = db.func.now()
            mesa.observacion = ""

        mesa.estado = destino
        if user is not None:
            mesa.updated_by = user.id
        mesa.updated_at = db.func.now()
        db.session.add(mesa)

        log = ActivityLog(
            user_id=user.id if user else None,
            mesa_id=mesa.id,
            tipo=f"MESA_{destino.replace(' ', '_')}",
            detalle=(
                f"Mesa {mesa.numero} → {LABELS.get(destino, destino)}"
                + (f" · {detalle[:180]}" if destino == "OBSERVADA" else "")
            ),
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
    def contar_por_estado(query=None):
        q = query.filter(Mesa.estado != None) if query is not None else Mesa.query
        filas = db.session.query(Mesa.estado, db.func.count(Mesa.id)).group_by(Mesa.estado).all()
        counts = {e: 0 for e in ESTADOS}
        for estado, n in filas:
            counts[estado] = n
        return counts

    @staticmethod
    def stats_generales():
        total_locales = Local.query.count()
        total_mesas = Mesa.query.count()
        total_electores = db.session.query(db.func.sum(Mesa.electores)).scalar() or 0

        counts = ChecklistService.contar_por_estado()

        def fase_suma(fase):
            return sum(counts[e] for e in FASES.get(fase, ()))

        digital = fase_suma("digital")
        custodia = fase_suma("custodia")
        calidad = fase_suma("calidad")
        conforme = fase_suma("conforme")
        observadas = counts["OBSERVADA"]
        cerradas = counts["CERRADA"]

        # Etapa del embudo con más acumulación = cuello de botella
        encoladas = {
            "Fase digital": digital,
            "Recepción / custodia": custodia + conforme,
            "Control de calidad": calidad + observadas,
        }
        peor = max(encoladas, key=encoladas.get) if total_mesas else None

        avance = round((cerradas / total_mesas) * 100, 1) if total_mesas else 0

        urbanas = Local.query.filter_by(ubicacion="URBANA").count()
        rurales = Local.query.filter_by(ubicacion="RURAL").count()

        return {
            "total_locales": total_locales,
            "total_mesas": total_mesas,
            "total_electores": total_electores,
            "por_estado": counts,
            "digital": digital,
            "custodia": custodia,
            "calidad": calidad,
            "conforme": conforme,
            "observadas": observadas,
            "cerradas": cerradas,
            "avance": avance,
            "cuello": peor,
            "urbanas": urbanas,
            "rurales": rurales,
        }

    @staticmethod
    def stats_por_local():
        locales = Local.query.order_by(Local.nombre.asc()).all()
        resultado = []
        for l in locales:
            counts = ChecklistService.contar_por_estado(l.mesas)
            cerradas = counts["CERRADA"]
            resultado.append({
                "id": l.id,
                "nombre": l.nombre,
                "total": l.total_mesas,
                "cerradas": cerradas,
                "observadas": counts["OBSERVADA"],
                "en_control": counts["EN CONTROL DE CALIDAD"],
                "pendientes": counts["PENDIENTE"],
                "avance": round((cerradas / l.total_mesas) * 100, 1) if l.total_mesas else 0,
            })
        return resultado

    @staticmethod
    def estados_por_mesa(local_id):
        return dict(
            db.session.query(Mesa.estado, db.func.count(Mesa.id))
            .filter(Mesa.local_id == local_id)
            .group_by(Mesa.estado)
            .all()
        )

    @staticmethod
    def trazabilidad_mesa(mesa_id):
        from models.user import User

        logs = (
            ActivityLog.query.filter_by(mesa_id=mesa_id)
            .order_by(ActivityLog.fecha.desc())
            .all()
        )
        users = {u.id: (u.full_name or u.username) for u in User.query.all()}
        eventos = [
            {
                "fecha": l.fecha.isoformat() if l.fecha else None,
                "usuario": users.get(l.user_id, "Sistema"),
                "detalle": l.detalle,
            }
            for l in logs
        ]
        observaciones = [o.to_dict() for o in Observacion.query.filter_by(mesa_id=mesa_id).order_by(Observacion.fecha.desc()).all()]
        return {"eventos": eventos, "observaciones": observaciones}