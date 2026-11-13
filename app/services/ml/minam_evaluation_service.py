from __future__ import annotations

import csv
import math
import struct
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

REQUIRED_COLUMNS = (
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "anio_objetivo",
    "generacion_real",
    "generacion_predicha",
)


def leer_predicciones(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = [dict(row) for row in csv.DictReader(source)]
    missing = [column for column in REQUIRED_COLUMNS if any(column not in row for row in rows)]
    if missing:
        raise ValueError(f"Faltan columnas en predicciones: {missing}")
    for row in rows:
        for column in ("anio_objetivo",):
            row[column] = int(row[column])
        for column in ("generacion_real", "generacion_predicha"):
            row[column] = float(row[column])
    return rows


def _metrics(rows: list[Mapping[str, Any]]) -> dict[str, float | int | None]:
    if not rows:
        return {"mae": None, "rmse": None, "r2": None, "observaciones": 0}
    actual = np.asarray([float(row["generacion_real"]) for row in rows])
    predicted = np.asarray([float(row["generacion_predicha"]) for row in rows])
    residuals = predicted - actual
    r2 = (
        float(1 - np.sum(residuals**2) / np.sum((actual - np.mean(actual)) ** 2))
        if len(actual) >= 2 and np.ptp(actual) > 0
        else None
    )
    return {
        "mae": float(np.mean(np.abs(residuals))),
        "rmse": float(math.sqrt(np.mean(residuals**2))),
        "r2": r2,
        "observaciones": len(rows),
    }


def _with_errors(rows: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    evaluated: list[dict[str, Any]] = []
    inconsistent = 0
    for source in rows:
        row = dict(source)
        actual = float(row["generacion_real"])
        predicted = float(row["generacion_predicha"])
        absolute = abs(actual - predicted)
        percentage = absolute / abs(actual) * 100 if actual != 0 else None
        if "error_absoluto" in row and row["error_absoluto"] not in ("", None):
            if not math.isclose(float(row["error_absoluto"]), absolute, rel_tol=1e-9, abs_tol=1e-9):
                inconsistent += 1
        row["error_absoluto"] = absolute
        row["error_porcentual"] = percentage
        row["residuo"] = predicted - actual
        evaluated.append(row)
    return evaluated, inconsistent


def _group_metrics(
    rows: list[Mapping[str, Any]],
    column: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row[column]), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for group, group_rows in sorted(groups.items()):
        metrics = _metrics(group_rows)
        residuals = [float(row["residuo"]) for row in group_rows]
        result[group] = {
            **metrics,
            "sesgo_medio": float(np.mean(residuals)),
            "sobreestimaciones": sum(value > 0 for value in residuals),
            "subestimaciones": sum(value < 0 for value in residuals),
        }
    return result


def _residual_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    residuals = np.asarray([float(row["residuo"]) for row in rows])
    absolute = np.abs(residuals)
    return {
        "media": float(np.mean(residuals)),
        "mediana": float(np.median(residuals)),
        "desviacion_estandar": float(np.std(residuals)),
        "minimo": float(np.min(residuals)),
        "maximo": float(np.max(residuals)),
        "sobreestimaciones": int(np.sum(residuals > 0)),
        "subestimaciones": int(np.sum(residuals < 0)),
        "errores_cero": int(np.sum(residuals == 0)),
        "p95_error_absoluto": float(np.percentile(absolute, 95)),
    }


def _concentracion_por_valor_real(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: float(row["generacion_real"]), reverse=True)
    cutoff = max(1, math.ceil(len(ordered) * 0.10))
    high = ordered[:cutoff]
    rest = ordered[cutoff:]
    total_error = sum(float(row["error_absoluto"]) for row in ordered)
    high_error = sum(float(row["error_absoluto"]) for row in high)
    return {
        "metodo": "10_por_ciento_superior_por_generacion_real",
        "umbral_generacion_real": float(high[-1]["generacion_real"]),
        "observaciones_superiores": len(high),
        "mae_superiores": _metrics(high)["mae"],
        "mae_resto": _metrics(rest)["mae"],
        "participacion_error_absoluto_superiores": (
            high_error / total_error * 100 if total_error else 0.0
        ),
    }


def evaluar_predicciones(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    evaluated, inconsistent = _with_errors(rows)
    arequipa = [row for row in evaluated if str(row["departamento"]).upper() == "AREQUIPA"]
    return {
        "filas": len(evaluated),
        "anios": sorted({row["anio_objetivo"] for row in evaluated}),
        "metricas_nacionales": _metrics(evaluated),
        "metricas_arequipa": _metrics(arequipa),
        "residuos": _residual_summary(evaluated),
        "metricas_departamento": _group_metrics(evaluated, "departamento"),
        "metricas_distrito": _group_metrics(evaluated, "distrito"),
        "concentracion_por_valor_real": _concentracion_por_valor_real(evaluated),
        "errores_precalculados_inconsistentes": inconsistent,
        "predicciones_evaluadas": evaluated,
        "peores_20": sorted(evaluated, key=lambda row: float(row["error_absoluto"]), reverse=True)[:20],
        "mejores_20": sorted(evaluated, key=lambda row: float(row["error_absoluto"]))[:20],
    }


def _png(path: Path, width: int, height: int, draw: Any) -> None:
    pixels = bytearray([255, 255, 255] * width * height)

    def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset : offset + 3] = bytes(color)

    def line(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx, dy = abs(x2 - x1), -abs(y2 - y1)
        sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
        error = dx + dy
        while True:
            set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            step = 2 * error
            if step >= dy:
                error += dy
                x1 += sx
            if step <= dx:
                error += dx
                y1 += sy

    def rectangle(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y1), min(height, y2)):
            for x in range(max(0, x1), min(width, x2)):
                set_pixel(x, y, color)

    draw(set_pixel, line, rectangle)
    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def generar_graficos(rows: list[Mapping[str, Any]], department_metrics: Mapping[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    margin = 40
    width, height = 1000, 520

    actual = [float(row["generacion_real"]) for row in rows]
    predicted = [float(row["generacion_predicha"]) for row in rows]
    maximum = max(actual + predicted)

    def comparison(set_pixel: Any, line: Any, rectangle: Any) -> None:
        line(margin, height - margin, width - margin, height - margin, (0, 0, 0))
        line(margin, margin, margin, height - margin, (0, 0, 0))
        for values, color in ((actual, (30, 90, 180)), (predicted, (210, 70, 50))):
            previous = None
            for index, value in enumerate(values):
                x = margin + int(index * (width - 2 * margin) / max(1, len(values) - 1))
                y = height - margin - int(value / maximum * (height - 2 * margin))
                if previous is not None:
                    line(previous[0], previous[1], x, y, color)
                previous = (x, y)

    generar = _png
    generar(output_dir / "real_vs_predicted.png", width, height, comparison)

    residuals = [float(row["residuo"]) for row in rows]
    low, high = min(residuals), max(residuals)
    bins = 30
    counts = [0] * bins
    for value in residuals:
        position = 0 if high == low else min(bins - 1, int((value - low) / (high - low) * bins))
        counts[position] += 1

    def histogram(set_pixel: Any, line: Any, rectangle: Any) -> None:
        maximum_count = max(counts)
        for index, count in enumerate(counts):
            x1 = margin + int(index * (width - 2 * margin) / bins)
            x2 = margin + int((index + 1) * (width - 2 * margin) / bins) - 1
            y = height - margin - int(count / maximum_count * (height - 2 * margin))
            rectangle(x1, y, x2, height - margin, (80, 130, 190))
        line(margin, height - margin, width - margin, height - margin, (0, 0, 0))

    generar(output_dir / "error_distribution.png", width, height, histogram)

    departments = list(department_metrics)
    values = [float(department_metrics[name]["mae"]) for name in departments]

    def department_bars(set_pixel: Any, line: Any, rectangle: Any) -> None:
        maximum_value = max(values) if values else 1
        bar_width = max(1, (width - 2 * margin) // max(1, len(values)))
        for index, value in enumerate(values):
            x1 = margin + index * bar_width
            y = height - margin - int(value / maximum_value * (height - 2 * margin))
            rectangle(x1, y, x1 + max(1, bar_width - 2), height - margin, (70, 150, 90))
        line(margin, height - margin, width - margin, height - margin, (0, 0, 0))

    generar(output_dir / "error_by_department.png", width, height, department_bars)


def escribir_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    fields = list(rows[0].keys()) if rows else list(REQUIRED_COLUMNS) + ["error_absoluto", "error_porcentual", "residuo"]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def crear_markdown(report: Mapping[str, Any]) -> str:
    national = report["metricas_nacionales"]
    arequipa = report["metricas_arequipa"]
    residuals = report["residuos"]
    concentration = report["concentracion_por_valor_real"]
    lines = [
        "# Evaluación del modelo MINAM — 2024",
        "",
        "Modelo evaluado: baseline de persistencia (`generacion_lag_1`).",
        "Esta evaluación es posterior al entrenamiento y no cambia la selección del modelo.",
        "",
        "## Métricas nacionales",
        "",
        f"- Observaciones: {national['observaciones']}",
        f"- MAE: {national['mae']:.4f} toneladas/año",
        f"- RMSE: {national['rmse']:.4f} toneladas/año",
        f"- R²: {national['r2']:.6f}",
        "",
        "## Arequipa",
        "",
        f"- Observaciones: {arequipa['observaciones']}",
        f"- MAE: {arequipa['mae']:.4f}",
        f"- RMSE: {arequipa['rmse']:.4f}",
        f"- R²: {arequipa['r2']:.6f}",
        "",
        "## Sesgo y residuos",
        "",
        f"- Sesgo medio (predicción - real): {residuals['media']:.4f}",
        f"- Mediana del residuo: {residuals['mediana']:.4f}",
        f"- Sobreestimaciones: {residuals['sobreestimaciones']}",
        f"- Subestimaciones: {residuals['subestimaciones']}",
        f"- P95 del error absoluto: {residuals['p95_error_absoluto']:.4f}",
        "",
        "## Concentración en valores reales altos",
        "",
        f"- Umbral del 10% superior: {concentration['umbral_generacion_real']:.4f}",
        f"- MAE del 10% superior: {concentration['mae_superiores']:.4f}",
        f"- MAE del resto: {concentration['mae_resto']:.4f}",
        f"- Participación del error absoluto: {concentration['participacion_error_absoluto_superiores']:.2f}%",
        "",
        "## Limitaciones",
        "",
        "- La persistencia no aprende relaciones adicionales entre población, territorio y generación.",
        "- Los distritos con historial corto tienen menos información histórica.",
        "- El error de distritos grandes puede dominar RMSE y el error absoluto agregado.",
        "- R² no debe interpretarse como única medida de calidad.",
        "- Los resultados no establecen causalidad.",
    ]
    return "\n".join(lines) + "\n"
