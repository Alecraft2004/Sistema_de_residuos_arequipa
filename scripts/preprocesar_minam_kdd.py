from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database import get_engine
from app.services.kdd.preprocessing_service import evaluar_calidad_minam
from app.services.kdd.selection_service import seleccionar_minam
from app.services.kdd.transformation_service import (
    crear_diccionario_minam,
    transformar_minam,
)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "processed"


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def _escribir_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {key: _csv_value(value) for key, value in row.items()} for row in rows
        )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with Session(get_engine()) as session:
        records = seleccionar_minam(session)

    quality_report = evaluar_calidad_minam(records)
    transformed = transformar_minam(records, quality_report)
    _escribir_csv(OUTPUT_DIR / "minam_kdd.csv", transformed)
    (OUTPUT_DIR / "minam_kdd_quality_report.json").write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "minam_kdd_dictionary.json").write_text(
        json.dumps(crear_diccionario_minam(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"MINAM KDD generado: {quality_report['filas_despues']} filas; "
        f"excluidas: {quality_report['filas_excluidas']}"
    )


if __name__ == "__main__":
    main()
