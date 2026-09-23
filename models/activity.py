from database import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=True)
    tipo = db.Column(db.String(50), nullable=False)
    detalle = db.Column(db.Text, default="")
    ip_address = db.Column(db.String(45), default="")
    fecha = db.Column(db.DateTime, default=db.func.now())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)