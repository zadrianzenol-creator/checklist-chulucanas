from database import db
from models.activity import ActivityLog
from models.local import Mesa
from models.lote import Lote


class LoteService:
    @staticmethod
    def _proximo_codigo():
        ultimo = Lote.query.order_by(Lote.id.desc()).first()
        return f"L-{ultimo.id + 1:03d}" if ultimo else "L-001"

    @staticmethod
    def crear_lote(mesa_ids, user=None, ip=""):
        mesa_ids = [int(x) for x in (mesa_ids or [])]
        if not mesa_ids or len(mesa_ids) < 1:
            raise ValueError("Selecciona al menos una mesa para el lote.")

        mesas = Mesa.query.filter(Mesa.id.in_(mesa_ids)).all()
        if len(mesas) != len(set(mesa_ids)):
            raise ValueError("Alguna mesa seleccionada no existe.")

        invalidas = [m.numero for m in mesas if m.estado != "PENDIENTE DE CONTROL"]
        if invalidas:
            raise ValueError(
                "Solo las mesas en 'Pend. de control' pueden entrar a un lote. Inválidas: "
                + ", ".join(invalidas[:8])
            )

        lote = Lote(
            codigo=LoteService._proximo_codigo(),
            estado="ARMADO",
            creado_por=user.id if user else None,
            digitador_id=None,
        )
        db.session.add(lote)
        db.session.flush()  # obtiene lote.id para el código

        if lote.codigo != f"L-{lote.id:03d}":
            # reasigna código basado en id real
            lote.codigo = f"L-{lote.id:03d}"

        for m in mesas:
            m.lote_id = lote.id
            db.session.add(m)
            db.session.add(ActivityLog(
                user_id=user.id if user else None,
                mesa_id=m.id,
                lote_id=lote.id,
                tipo="LOTE_ARMADO",
                detalle=f"Agregada al lote {lote.codigo}",
                ip_address=ip,
            ))
        db.session.commit()
        return lote

    @staticmethod
    def entregar_lote(lote, digitador_id, user=None, ip=""):
        if lote.estado != "ARMADO":
            raise ValueError(f"El lote {lote.codigo} ya no está preparado.")
        if not digitador_id:
            raise ValueError("Debes elegir un digitador para entregar el lote.")
        from models.user import User

        dig = User.query.get(digitador_id)
        if dig is None or dig.role != "digitador":
            raise ValueError("El usuario elegido no es un digitador.")

        lote.estado = "ENTREGADO"
        lote.digitador_id = dig.id
        lote.entregado_en = db.func.now()
        db.session.add(lote)

        for m in lote.mesas.all():
            if m.estado == "PENDIENTE DE CONTROL":
                m.estado = "EN CONTROL DE CALIDAD"
                m.digitador_id = dig.id
                m.updated_by = user.id if user else None
                m.updated_at = db.func.now()
                db.session.add(m)
                db.session.add(ActivityLog(
                    user_id=user.id if user else None,
                    mesa_id=m.id,
                    lote_id=lote.id,
                    tipo="LOTE_ENTREGADO",
                    detalle=f"Lote {lote.codigo} entregado a {dig.full_name or dig.username} para control de calidad",
                    ip_address=ip,
                ))
        db.session.commit()
        return lote

    @staticmethod
    def recibir_lote(lote, user=None, ip=""):
        """El digitador devuelve el lote a custodia tras el control."""
        if lote.estado == "ARMADO":
            raise ValueError(f"El lote {lote.codigo} aún no ha sido entregado.")
        if user is not None and lote.digitador_id and user.role != "admin" and lote.digitador_id != user.id:
            raise ValueError("Solo el digitador asignado puede devolver este lote.")
        pendientes = lote.mesas.filter(Mesa.estado.in_(["EN CONTROL DE CALIDAD", "CONFORME", "OBSERVADA"])).count()
        lote.estado = "DEVUELTO"
        lote.devuelto_en = db.func.now()
        db.session.add(lote)
        db.session.add(ActivityLog(
            user_id=user.id if user else None,
            mesa_id=None,
            lote_id=lote.id,
            tipo="LOTE_DEVUELTO",
            detalle=f"Lote {lote.codigo} devuelto a custodia",
            ip_address=ip,
        ))
        db.session.commit()
        return lote

    @staticmethod
    def archivar_lote(lote, user=None, ip=""):
        """Recepción archiva las mesas CONFORME del lote (-> CERRADA)."""
        cuenta = 0
        for m in lote.mesas.all():
            if m.estado == "CONFORME":
                m.estado = "CERRADA"
                m.updated_by = user.id if user else None
                m.updated_at = db.func.now()
                db.session.add(m)
                db.session.add(ActivityLog(
                    user_id=user.id if user else None,
                    mesa_id=m.id,
                    lote_id=lote.id,
                    tipo="MESA_CERRADA",
                    detalle=f"Mesa {m.numero} archivada y cerrada (lote {lote.codigo})",
                    ip_address=ip,
                ))
                cuenta += 1
        if cuenta == 0:
            db.session.rollback()
            raise ValueError("No hay mesas CONFORME para archivar en este lote.")
        db.session.commit()
        return cuenta

    @staticmethod
    def archivar_mesa(mesa, user=None, ip=""):
        if mesa.estado != "CONFORME":
            raise ValueError("Solo se archiva una mesa CONFORME.")
        mesa.estado = "CERRADA"
        if user is not None:
            mesa.updated_by = user.id
        mesa.updated_at = db.func.now()
        db.session.add(mesa)
        db.session.add(ActivityLog(
            user_id=user.id if user else None,
            mesa_id=mesa.id,
            lote_id=mesa.lote_id,
            tipo="MESA_CERRADA",
            detalle=f"Mesa {mesa.numero} archivada y cerrada",
            ip_address=ip,
        ))
        db.session.commit()
        return mesa

    @staticmethod
    def llegada_fisica(mesa, user=None, ip=""):
        """Recepción registra que el acta original llegó físicamente al centro de cómputo."""
        if mesa.estado != "REGISTRADA":
            raise ValueError(f"La mesa {mesa.numero} no está en fase REGISTRADA.")
        mesa.estado = "PENDIENTE DE CONTROL"
        if user is not None:
            mesa.updated_by = user.id
        mesa.updated_at = db.func.now()
        db.session.add(mesa)
        db.session.add(ActivityLog(
            user_id=user.id if user else None,
            mesa_id=mesa.id,
            lote_id=mesa.lote_id,
            tipo="MESA_PENDIENTE_DE_CONTROL",
            detalle=f"Mesa {mesa.numero} recibida físicamente",
            ip_address=ip,
        ))
        db.session.commit()
        return mesa