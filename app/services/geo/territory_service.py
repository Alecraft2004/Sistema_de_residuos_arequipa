
"""Consulta y exposición de límites distritales oficiales."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd


BASE_DIR = Path(__file__).resolve().parents[3]

DISTRICTS_PATH = (
    BASE_DIR
    / "data"
    / "staging"
    / "grupo_a"
    / "DISTRITOS_LIMITES"
    / "DISTRITOS.shp"
)


class TerritoryServiceError(Exception):
    """Error controlado al consultar la cartografía."""


@lru_cache(maxsize=2)
def _cargar_geojson(tolerancia: float = 0.0) -> dict[str, Any]:
    if not DISTRICTS_PATH.is_file():
        raise TerritoryServiceError(
            "No se encontró el shapefile de límites distritales."
        )

    try:
        gdf = gpd.read_file(DISTRICTS_PATH)

        if gdf.crs is None:
            raise TerritoryServiceError(
                "La cartografía no tiene sistema de coordenadas definido."
            )

        if gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        required = {
            "UBIGEO",
            "DEPARTAMEN",
            "PROVINCIA",
            "DISTRITO",
            "geometry",
        }

        if not required.issubset(set(gdf.columns)):
            raise TerritoryServiceError(
                "El shapefile no contiene los campos territoriales requeridos."
            )

        if gdf.geometry.isna().any() or gdf.geometry.is_empty.any():
            raise TerritoryServiceError(
                "La cartografía contiene geometrías vacías o nulas."
            )

        if not gdf.geometry.is_valid.all():
            raise TerritoryServiceError(
                "La cartografía contiene geometrías inválidas."
            )

        gdf = gdf.copy()
        if tolerancia > 0:
            gdf["geometry"] = gdf.geometry.simplify(
                tolerance=tolerancia,
                preserve_topology=True,
            )
        gdf["UBIGEO"] = (
            gdf["UBIGEO"].astype(str).str.strip().str.zfill(6)
        )

        if gdf["UBIGEO"].duplicated().any():
            raise TerritoryServiceError(
                "La cartografía contiene UBIGEO duplicados."
            )

        features = []

        for _, row in gdf.iterrows():
            geometry = row.geometry.__geo_interface__

            features.append({
                "type": "Feature",
                "id": row["UBIGEO"],
                "properties": {
                    "ubigeo": row["UBIGEO"],
                    "departamento": str(row["DEPARTAMEN"]).strip(),
                    "provincia": str(row["PROVINCIA"]).strip(),
                    "distrito": str(row["DISTRITO"]).strip(),
                },
                "geometry": geometry,
            })

        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                },
            },
            "features": features,
        }

    except TerritoryServiceError:
        raise
    except Exception as error:
        raise TerritoryServiceError(
            "No se pudo procesar la cartografía distrital."
        ) from error


def obtener_distritos(
    departamento: str | None = None,
    ubigeo: str | None = None,
    tolerancia: float = 0.0,
) -> dict[str, Any]:
    geojson = _cargar_geojson(tolerancia)

    features = geojson["features"]

    if departamento:
        features = [
            feature for feature in features
            if feature["properties"]["departamento"].casefold()
            == departamento.strip().casefold()
        ]

    if ubigeo:
        codigo = ubigeo.strip().zfill(6)
        features = [
            feature for feature in features
            if feature["properties"]["ubigeo"] == codigo
        ]

    return {
        "type": "FeatureCollection",
        "crs": geojson["crs"],
        "total": len(features),
        "features": features,
    }


def limpiar_cache_territorial() -> None:
    """Permite recargar la cartografía después de actualizarla."""
    _cargar_geojson.cache_clear()
