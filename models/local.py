from database import db

ESTADOS = (
    "PENDIENTE",
    "FOTO RECIBIDA",
    "EN REGISTRO",
    "REGISTRADA",
    "PENDIENTE DE CONTROL",
    "EN CONTROL DE CALIDAD",
    "CONFORME",
    "OBSERVADA",
    "CERRADA",
)

# Etapas del embudo para el dashboard
FASES = {
    "digital": ("PENDIENTE", "FOTO RECIBIDA", "EN REGISTRO", "REGISTRADA"),
    "custodia": ("PENDIENTE DE CONTROL",),
    "calidad": ("EN CONTROL DE CALIDAD",),
    "conforme": ("CONFORME",),
    "observada": ("OBSERVADA",),
    "cerrada": ("CERRADA",),
}


class Local(db.Model):
    __tablename__ = "locales"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.String(255), default="")
    ubicacion = db.Column(db.String(20), default="URBANA")
    pabellon = db.Column(db.String(50), default="")
    numero_ca = db.Column(db.String(20), default="")
    total_electores = db.Column(db.Integer, default=0)
    total_mesas = db.Column(db.Integer, default=0)

    mesas = db.relationship(
        "Mesa",
        backref="local",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Mesa.orden",
    )

    @property
    def cerradas(self):
        return self.mesas.filter(Mesa.estado == "CERRADA").count()

    @property
    def observadas(self):
        return self.mesas.filter(Mesa.estado == "OBSERVADA").count()

    @property
    def avance(self):
        if self.total_mesas == 0:
            return 0
        return round((self.cerradas / self.total_mesas) * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "ubicacion": self.ubicacion,
            "total_mesas": self.total_mesas,
            "total_electores": self.total_electores,
            "cerradas": self.cerradas,
            "observadas": self.observadas,
            "avance": self.avance,
        }


class Mesa(db.Model):
    __tablename__ = "mesas"

    id = db.Column(db.Integer, primary_key=True)
    local_id = db.Column(db.Integer, db.ForeignKey("locales.id", ondelete="CASCADE"), nullable=False, index=True)
    orden = db.Column(db.Integer, default=0)
    numero = db.Column(db.String(20), nullable=False)
    aula = db.Column(db.String(30), default="")
    piso = db.Column(db.String(30), default="")
    pabellon = db.Column(db.String(30), default="")
    electores = db.Column(db.Integer, default=0)
    electores_discapacidad = db.Column(db.Integer, default=0)

    estado = db.Column(db.String(24), default="PENDIENTE", index=True)
    observacion = db.Column(db.Text, default="")
    digitador_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=True, index=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)

    digitador = db.relationship(
        "User",
        foreign_keys=[digitador_id],
        backref="mesas_asignadas",
        lazy="joined",
    )
    lote = db.relationship("Lote", back_populates="mesas", lazy="joined")
    observaciones = db.relationship(
        "Observacion",
        backref="mesa",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Observacion.fecha.desc()",
    )

    @property
    def fase(self):
        for nombre, estados in FASES.items():
            if self.estado in estados:
                return nombre
        return "digital"

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "orden": self.orden,
            "aula": self.aula,
            "piso": self.piso,
            "pabellon": self.pabellon,
            "electores": self.electores,
            "electores_discapacidad": self.electores_discapacidad,
            "estado": self.estado,
            "observacion": self.observacion,
            "local_id": self.local_id,
            "local_nombre": self.local.nombre if self.local else "",
            "digitador_id": self.digitador_id,
            "digitador": self.digitador.full_name or self.digitador.username if self.digitador else None,
            "lote_id": self.lote_id,
            "lote_codigo": self.lote.codigo if self.lote else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }