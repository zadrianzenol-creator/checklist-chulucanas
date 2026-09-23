from sqlalchemy import text

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db():
    db.create_all()
    migrate()
    remap_legacy()


def _dialect():
    return db.engine.dialect.name


def _columnas(table):
    if _dialect() == "sqlite":
        rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {r[1] for r in rows}
    rows = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
    ), {"t": table}).fetchall()
    return {r[0] for r in rows}


def _add_columna(table, columna, sql):
    if columna not in _columnas(table):
        db.session.execute(sql)
        db.session.commit()


def migrate():
    """Agrega columnas nuevas a tablas existentes (no altera las que ya existen)."""
    if _dialect() == "sqlite":
        _add_columna(
            "mesas", "digitador_id",
            text("ALTER TABLE mesas ADD COLUMN digitador_id INTEGER"),
        )
        _add_columna(
            "mesas", "lote_id",
            text("ALTER TABLE mesas ADD COLUMN lote_id INTEGER"),
        )
        _add_columna(
            "mesas", "observacion",
            text("ALTER TABLE mesas ADD COLUMN observacion TEXT DEFAULT ''"),
        )
        _add_columna(
            "mesas", "updated_by",
            text("ALTER TABLE mesas ADD COLUMN updated_by INTEGER"),
        )
        _add_columna(
            "mesas", "updated_at",
            text("ALTER TABLE mesas ADD COLUMN updated_at DATETIME"),
        )
        _add_columna(
            "activity_logs", "lote_id",
            text("ALTER TABLE activity_logs ADD COLUMN lote_id INTEGER"),
        )
    else:
        _add_columna(
            "mesas", "digitador_id",
            text("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS digitador_id INTEGER REFERENCES users(id)"),
        )
        _add_columna(
            "mesas", "lote_id",
            text("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS lote_id INTEGER REFERENCES lotes(id)"),
        )
        _add_columna(
            "mesas", "observacion",
            text("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS observacion TEXT DEFAULT ''"),
        )
        _add_columna(
            "mesas", "updated_by",
            text("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS updated_by INTEGER"),
        )
        _add_columna(
            "mesas", "updated_at",
            text("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"),
        )
        _add_columna(
            "activity_logs", "lote_id",
            text("ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS lote_id INTEGER"),
        )


def remap_legacy():
    """Convierte datos del flujo anterior (VERIFICADA/OBSERVADO/operador) al nuevo."""
    try:
        n = db.session.execute(
            text("UPDATE mesas SET estado='REGISTRADA' WHERE estado='VERIFICADA'")
        ).rowcount
        n2 = db.session.execute(
            text("UPDATE mesas SET estado='OBSERVADA' WHERE estado='OBSERVADO'")
        ).rowcount
        n3 = db.session.execute(
            text("UPDATE users SET role='digitador' WHERE role='operador'")
        ).rowcount
        db.session.commit()
        if n or n2 or n3:
            print(f">> Datos legacy migrados (mesas: {n}+{n2}, usuarios: {n3})")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        print(f">> remap_legacy omitido: {exc}")