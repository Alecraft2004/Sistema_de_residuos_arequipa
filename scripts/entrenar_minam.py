from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import joblib

from app.services.ml.minam_training_service import (
    entrenar_y_evaluar,
    crear_metadata,
    leer_csv_minam,
)

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "data" / "models" / "minam"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0].keys()) if rows else ["modelo", "variable", "importancia", "metodo"]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    train_rows = leer_csv_minam(PROCESSED_DIR / "minam_train.csv")
    test_rows = leer_csv_minam(PROCESSED_DIR / "minam_test.csv")
    result = entrenar_y_evaluar(train_rows, test_rows)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(result["modelo"], MODEL_DIR / "best_model.joblib")
    (MODEL_DIR / "metrics.json").write_text(
        json.dumps(
            {
                "validacion_temporal": result["validacion_temporal"],
                "validacion_resumen": result["validacion_resumen"],
                "metricas_prueba": result["metricas_prueba"],
                "metricas_prueba_arequipa": result["metricas_prueba_arequipa"],
                "metricas_prueba_departamento": result["metricas_prueba_departamento"],
                "metricas_prueba_distrito": result["metricas_prueba_distrito"],
                "resumen_residuos_prueba": result["resumen_residuos_prueba"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(MODEL_DIR / "predictions_2024.csv", result["predicciones"])
    _write_csv(MODEL_DIR / "feature_importance.csv", result["importancia"])
    (MODEL_DIR / "model_metadata.json").write_text(
        json.dumps(crear_metadata(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Modelo seleccionado: {result['modelo_seleccionado']}; "
        f"MAE 2024: {result['metricas_prueba'][result['modelo_seleccionado']]['mae']:.4f}"
    )


if __name__ == "__main__":
    main()
