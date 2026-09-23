from database import db

ESTADOS_LOTE = ("ARMADO", "ENTREGADO", "DEVUELTO")


class Lote(db.Model):
    __tablename__ = "lotes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(12), unique=True, nullable=False, index=True)
    estado = db.Column(db.String(20), default="ARMADO", index=True)
    digitador_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    creado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=db.func.now())
    entregado_en = db.Column(db.DateTime, nullable=True)
    devuelto_en = db.Column(db.DateTime, nullable=True)

    digitador = db.relationship("User", foreign_keys=[digitador_id], lazy="joined")
    creador = db.relationship("User", foreign_keys=[creado_por], lazy="joined")
    mesas = db.relationship(
        "Mesa",
        back_populates="lote",
        lazy="dynamic",
        order_by="Mesa.orden",
    )

    @property
    def total_mesas(self):
        return self.mesas.count()

    @property
    def conformes(self):
        from models.local import Mesa

        return self.mesas.filter(Mesa.estado == "CONFORME").count()

    @property
    def observadas(self):
        from models.local import Mesa

        return self.mesas.filter(Mesa.estado == "OBSERVADA").count()

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "estado": self.estado,
            "digitador_id": self.digitador_id,
            "digitador": self.digitador.full_name or self.digitador.username if self.digitador else None,
            "creado_por": self.creador.full_name if self.creador else None,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "entregado_en": self.entregado_en.isoformat() if self.entregado_en else None,
            "devuelto_en": self.devuelto_en.isoformat() if self.devuelto_en else None,
            "total_mesas": self.total_mesas,
            "conformes": self.conformes,
            "observadas": self.observadas,
        }