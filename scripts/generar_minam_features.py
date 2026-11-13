from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.services.kdd.feature_engineering_service import (
    construir_caracteristicas,
    generar_reporte_caracteristicas,
    validar_caracteristicas,
)

BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = BASE_DIR / "data" / "processed" / "minam_kdd.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

NUMERIC_COLUMNS = {
    "anio",
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
    "generacion_municipal_t_anio",
}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows: list[dict[str, Any]] = []
        for raw in csv.DictReader(source):
            row: dict[str, Any] = dict(raw)
            for column in NUMERIC_COLUMNS:
                if column == "anio":
                    row[column] = int(row[column])
                elif row[column] == "":
                    row[column] = None
                else:
                    row[column] = float(row[column])
            rows.append(row)
        return rows


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_rows = _read_rows(INPUT_PATH)
    feature_rows = construir_caracteristicas(source_rows)
    validation = validar_caracteristicas(feature_rows)
    report = generar_reporte_caracteristicas(source_rows, feature_rows, validation)
    train_rows = [
        row for row in feature_rows if row["particion_temporal"] == "entrenamiento"
    ]
    test_rows = [
        row for row in feature_rows if row["particion_temporal"] == "prueba"
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_rows(OUTPUT_DIR / "minam_features.csv", feature_rows)
    _write_rows(OUTPUT_DIR / "minam_train.csv", train_rows)
    _write_rows(OUTPUT_DIR / "minam_test.csv", test_rows)
    (OUTPUT_DIR / "minam_features_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Características generadas: {len(feature_rows)} filas; "
        f"entrenamiento={len(train_rows)}; prueba={len(test_rows)}"
    )


if __name__ == "__main__":
    main()
