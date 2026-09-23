import json
import os
import sys

import openpyxl


DEFAULT_EXCEL = os.path.join(
    os.path.expanduser("~"), "Downloads", "LOCALES_Y_MESAS_DISTRITO_CHULUCANAS_OCTUBRE_2026.xlsx"
)

COLS = {
    "n_ord": 0,
    "odpe": 1,
    "ubigeo": 2,
    "departamento": 3,
    "provincia": 4,
    "distrito": 5,
    "localidad": 6,
    "codigo_lv": 7,
    "nombre_local": 8,
    "direccion": 9,
    "orden_ca": 10,
    "numero_ca": 11,
    "orden_mesa": 12,
    "mesa_sufragio": 13,
    "aula": 14,
    "piso": 15,
    "pabellon": 16,
    "electores": 17,
    "electores_discapacidad": 18,
    "ubicacion": 19,
}


def first_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def first_text(value):
    if value is None:
        return str(value)
    return str(value).strip()


def build(excel_path=None):
    excel_path = excel_path or DEFAULT_EXCEL
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"No se encontro el Excel: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb["data de mesas"]

    locales = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not first_text(row[COLS["nombre_local"]]):
            continue

        codigo = first_text(row[COLS["codigo_lv"]])
        nombre = first_text(row[COLS["nombre_local"]])
        direccion = first_text(row[COLS["direccion"]])
        ubicacion = first_text(row[COLS["ubicacion"]]) or "URBANA"
        pabellon = first_text(row[COLS["pabellon"]])
        numero_ca = first_text(row[COLS["numero_ca"]])

        local = locales.setdefault(
            codigo,
            {
                "codigo": codigo,
                "nombre": nombre,
                "direccion": direccion,
                "ubicacion": ubicacion,
                "pabellon": pabellon,
                "numero_ca": numero_ca,
                "mesas": [],
            },
        )

        local["mesas"].append(
            {
                "orden": first_int(row[COLS["orden_mesa"]]),
                "numero": first_text(row[COLS["mesa_sufragio"]]),
                "aula": first_text(row[COLS["aula"]]),
                "piso": first_text(row[COLS["piso"]]),
                "pabellon": pabellon,
                "electores": first_int(row[COLS["electores"]]),
                "electores_discapacidad": first_int(row[COLS["electores_discapacidad"]]),
            }
        )

    for local in locales.values():
        local["mesas"].sort(key=lambda m: m["orden"])
        local["total_electores"] = sum(m["electores"] for m in local["mesas"])
        local["total_mesas"] = len(local["mesas"])

    data = {
        "distrito": "CHULUCANAS",
        "provincia": "MORROPON",
        "departamento": "PIURA",
        "unidad_min": "MORROPON",
        "locales": list(locales.values()),
    }

    total_mesas = sum(l["total_mesas"] for l in data["locales"])
    total_electores = sum(l["total_electores"] for l in data["locales"])

    print("== Resumen ==")
    print(f"Locales: {len(data['locales'])}")
    print(f"Mesas: {total_mesas}")
    print(f"Electores: {total_electores}")
    return data


def main():
    excel_path = sys.argv[1] if len(sys.argv) > 1 else None
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_data.json"
    )
    data = build(excel_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Escribi {out_path}")


if __name__ == "__main__":
    main()