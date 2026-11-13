from __future__ import annotations

import json
from pathlib import Path

from app.services.ml.minam_evaluation_service import (
    crear_markdown,
    evaluar_predicciones,
    generar_graficos,
    escribir_csv,
    leer_predicciones,
)

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "data" / "models" / "minam"
OUTPUT_DIR = MODEL_DIR / "evaluation"


def main() -> None:
    rows = leer_predicciones(MODEL_DIR / "predictions_2024.csv")
    report = evaluar_predicciones(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "evaluation_report.json").write_text(
        json.dumps(
            {key: value for key, value in report.items() if key not in {"predicciones_evaluadas", "peores_20", "mejores_20"}},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "evaluation_report.md").write_text(
        crear_markdown(report),
        encoding="utf-8",
    )
    escribir_csv(OUTPUT_DIR / "predictions_evaluated.csv", report["predicciones_evaluadas"])
    escribir_csv(OUTPUT_DIR / "department_metrics.csv", [
        {"departamento": department, **metrics}
        for department, metrics in report["metricas_departamento"].items()
    ])
    (OUTPUT_DIR / "arequipa_metrics.json").write_text(
        json.dumps(report["metricas_arequipa"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    escribir_csv(OUTPUT_DIR / "worst_predictions.csv", report["peores_20"])
    escribir_csv(OUTPUT_DIR / "best_predictions.csv", report["mejores_20"])
    generar_graficos(rows=report["predicciones_evaluadas"], department_metrics=report["metricas_departamento"], output_dir=OUTPUT_DIR)
    print(
        f"Evaluadas {report['filas']} predicciones; "
        f"MAE={report['metricas_nacionales']['mae']:.4f}"
    )


if __name__ == "__main__":
    main()
