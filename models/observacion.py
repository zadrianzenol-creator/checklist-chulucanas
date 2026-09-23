from database import db


class Observacion(db.Model):
    __tablename__ = "observaciones"

    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id", ondelete="CASCADE"), nullable=False, index=True)
    detalle = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    fecha = db.Column(db.DateTime, default=db.func.now())
    resuelta = db.Column(db.Boolean, default=False)
    resuelta_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resuelta_en = db.Column(db.DateTime, nullable=True)

    autor = db.relationship("User", foreign_keys=[user_id], lazy="joined")
    resolutor = db.relationship("User", foreign_keys=[resuelta_por], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "mesa_id": self.mesa_id,
            "detalle": self.detalle,
            "autor": self.autor.full_name or self.autor.username if self.autor else None,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "resuelta": self.resuelta,
            "resolutor": self.resolutor.full_name or self.resolutor.username if self.resolutor else None,
            "resuelta_en": self.resuelta_en.isoformat() if self.resuelta_en else None,
        }