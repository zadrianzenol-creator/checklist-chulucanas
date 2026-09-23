from database import db

ESTADOS = ("PENDIENTE", "VERIFICADA", "OBSERVADO")


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
    def verificadas(self):
        return self.mesas.filter(Mesa.estado == "VERIFICADA").count()

    @property
    def observadas(self):
        return self.mesas.filter(Mesa.estado == "OBSERVADO").count()

    @property
    def pendientes(self):
        return self.mesas.filter(Mesa.estado == "PENDIENTE").count()

    @property
    def avance(self):
        if self.total_mesas == 0:
            return 0
        return round((self.verificadas / self.total_mesas) * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "ubicacion": self.ubicacion,
            "total_mesas": self.total_mesas,
            "total_electores": self.total_electores,
            "verificadas": self.verificadas,
            "observadas": self.observadas,
            "pendientes": self.pendientes,
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

    estado = db.Column(db.String(20), default="PENDIENTE", index=True)
    observacion = db.Column(db.Text, default="")
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)

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
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }