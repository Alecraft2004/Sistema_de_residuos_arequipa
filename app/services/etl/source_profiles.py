"""Perfiles oficiales de las fuentes iniciales del módulo ETL."""

from __future__ import annotations

from dataclasses import dataclass

from ...schemas.etl import ConfiguracionColumnasETL


@dataclass(frozen=True)
class PerfilFuenteETL:
    identificador: str
    nombre: str
    entidad: str
    separador: str | None
    codificacion: str | None
    encabezados_originales: tuple[str, ...]
    mapeo_columnas: dict[str, str]
    tipos: dict[str, str]
    columnas_obligatorias: frozenset[str]
    columnas_no_negativas: frozenset[str]
    columnas_fecha: frozenset[str]
    campos_geograficos: frozenset[str]
    campos_temporales: frozenset[str]
    unidades: dict[str, str]
    claves_duplicado: tuple[str, ...]
    categorias: dict[str, dict[str, str]]
    anio_desde: int | None = None
    anio_hasta: int | None = None
    permitir_anios_futuros: bool = True

    def configuracion(self) -> ConfiguracionColumnasETL:
        return ConfiguracionColumnasETL(
            perfil_id=self.identificador,
            fuente=self.nombre,
            entidad=self.entidad,
            mapeo_columnas=self.mapeo_columnas,
            encabezados_originales=self.encabezados_originales,
            columnas_obligatorias=self.columnas_obligatorias,
            columnas_no_negativas=self.columnas_no_negativas,
            columnas_fecha=self.columnas_fecha,
            tipos=self.tipos,
            claves_duplicado=list(self.claves_duplicado),
            categorias=self.categorias,
            campos_geograficos=self.campos_geograficos,
            campos_temporales=self.campos_temporales,
            unidades=self.unidades,
            anio_desde=self.anio_desde,
            anio_hasta=self.anio_hasta,
            permitir_anios_futuros=self.permitir_anios_futuros,
        )


def _snake_map(headers: tuple[str, ...], canonical: tuple[str, ...]) -> dict[str, str]:
    return dict(zip(headers, canonical, strict=True))


MINAM_HEADERS = (
    "FECHA_CORTE",
    "UBIGEO",
    "ANIO",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "REGION_NATURAL",
    "TIPO_MUNICIPALIDAD",
    "POB_TOTAL_INEI",
    "POB_URBANA_INEI",
    "POB_RURAL_INEI",
    "CLASIFICACION_MUNICIPAL_MEF",
    "GENERACION_PER_CAPITA_DOM",
    "GENERACION_DOM_URBANA_TDIA",
    "GENERACION_DOM URBANA_TANIO",
    "GENERACION_MUN_TANIO",
    "GENERACION_MUN_TDIA",
    "GENERACION_PER_CAPITA_MUNICIPAL",
)

MINAM_CANONICAL = (
    "fecha_corte",
    "ubigeo",
    "anio",
    "departamento",
    "provincia",
    "distrito",
    "region_natural",
    "tipo_municipalidad",
    "poblacion_total_inei",
    "poblacion_urbana_inei",
    "poblacion_rural_inei",
    "clasificacion_municipal_mef",
    "generacion_per_capita_domiciliaria",
    "generacion_domiciliaria_urbana_t_dia",
    "generacion_domiciliaria_urbana_t_anio",
    "generacion_municipal_t_anio",
    "generacion_municipal_t_dia",
    "generacion_per_capita_municipal",
)

MINAM_GENERACION_ANUAL = PerfilFuenteETL(
    identificador="MINAM_GENERACION_ANUAL",
    nombre="Generación anual de residuos sólidos domiciliarios y municipales",
    entidad="Ministerio del Ambiente (MINAM)",
    separador=";",
    codificacion="latin-1",
    encabezados_originales=MINAM_HEADERS,
    mapeo_columnas=_snake_map(MINAM_HEADERS, MINAM_CANONICAL),
    tipos={
        "fecha_corte": "date",
        "ubigeo": "string",
        "anio": "integer",
        "departamento": "string",
        "provincia": "string",
        "distrito": "string",
        "region_natural": "string",
        "tipo_municipalidad": "string",
        "poblacion_total_inei": "number",
        "poblacion_urbana_inei": "number",
        "poblacion_rural_inei": "number",
        "clasificacion_municipal_mef": "string",
        "generacion_per_capita_domiciliaria": "number",
        "generacion_domiciliaria_urbana_t_dia": "number",
        "generacion_domiciliaria_urbana_t_anio": "number",
        "generacion_municipal_t_anio": "number",
        "generacion_municipal_t_dia": "number",
        "generacion_per_capita_municipal": "number",
    },
    columnas_obligatorias=frozenset(
        {"ubigeo", "anio", "departamento", "provincia", "distrito"}
    ),
    columnas_no_negativas=frozenset(
        {
            "poblacion_total_inei",
            "poblacion_urbana_inei",
            "poblacion_rural_inei",
            "generacion_per_capita_domiciliaria",
            "generacion_domiciliaria_urbana_t_dia",
            "generacion_domiciliaria_urbana_t_anio",
            "generacion_municipal_t_anio",
            "generacion_municipal_t_dia",
            "generacion_per_capita_municipal",
        }
    ),
    columnas_fecha=frozenset({"fecha_corte"}),
    categorias={},
    campos_geograficos=frozenset(
        {"ubigeo", "departamento", "provincia", "distrito", "region_natural"}
    ),
    campos_temporales=frozenset({"fecha_corte", "anio"}),
    unidades={
        "generacion_domiciliaria_urbana_t_dia": "toneladas/día",
        "generacion_domiciliaria_urbana_t_anio": "toneladas/año",
        "generacion_municipal_t_anio": "toneladas/año",
        "generacion_municipal_t_dia": "toneladas/día",
    },
    claves_duplicado=("ubigeo", "anio"),
    anio_desde=2019,
    anio_hasta=2024,
)


OEFA_HEADERS = (
    "UBIGEO",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "ID_DOC_MUNICIPALIDAD",
    "MUNICIPALIDAD_ADMINISTRA",
    "ID_UF",
    "DENOMINACION",
    "ZONA",
    "ESTE",
    "NORTE",
    "PERIMETRO",
    "AREA_M2",
    "AREA_HA",
    "MUNICIPALIDAD_DISPONEN",
    "CANT_MUNI_DISPONEN",
    "SEGREGACION",
    "CRIANZA_ANIMAL",
    "QUEMA_RRSS",
    "RRSS_SALUD",
    "RRSS_INDUSTRIAL",
    "NATURAL_AGUAJAL",
    "NATURAL_BOFEDAL",
    "NATURAL_PANTANO",
    "AMORTIGUAMIENTO_ANP",
    "ANP",
    "CATEGORIA",
    "ANIO_INCORPORACION",
    "DOC_RESOLUCION_INC",
    "FECHA_CORTE",
)

OEFA_CANONICAL = (
    "ubigeo",
    "departamento",
    "provincia",
    "distrito",
    "id_doc_municipalidad",
    "municipalidad_administra",
    "id_uf",
    "denominacion",
    "zona",
    "este",
    "norte",
    "perimetro",
    "area_m2",
    "area_ha",
    "municipalidad_disponen",
    "cantidad_municipalidades_disponen",
    "segregacion",
    "crianza_animal",
    "quema_rrss",
    "rrss_salud",
    "rrss_industrial",
    "natural_aguajal",
    "natural_bofedal",
    "natural_pantano",
    "amortiguamiento_anp",
    "anp",
    "categoria",
    "anio_incorporacion",
    "doc_resolucion_incorporacion",
    "fecha_corte",
)

OEFA_GENERATED_TYPES = {
    **dict.fromkeys(
        (
            "ubigeo",
            "departamento",
            "provincia",
            "distrito",
            "id_doc_municipalidad",
            "municipalidad_administra",
            "id_uf",
            "denominacion",
            "zona",
            "municipalidad_disponen",
            "categoria",
            "doc_resolucion_incorporacion",
        ),
        "string",
    ),
    **dict.fromkeys(
        ("este", "norte", "perimetro", "area_m2", "area_ha"),
        "number",
    ),
    **dict.fromkeys(
        (
            "cantidad_municipalidades_disponen",
        ),
        "number",
    ),
    **dict.fromkeys(
        (
            "segregacion",
            "crianza_animal",
            "quema_rrss",
            "rrss_salud",
            "rrss_industrial",
            "natural_aguajal",
            "natural_bofedal",
            "natural_pantano",
            "amortiguamiento_anp",
            "anp",
        ),
        "boolean",
    ),
    "anio_incorporacion": "integer",
    "fecha_corte": "date",
}

OEFA_AREAS_DEGRADADAS = PerfilFuenteETL(
    identificador="OEFA_AREAS_DEGRADADAS",
    nombre="Inventario Nacional de Áreas Degradadas por residuos sólidos municipales",
    entidad="Organismo de Evaluación y Fiscalización Ambiental (OEFA)",
    separador=None,
    codificacion=None,
    encabezados_originales=OEFA_HEADERS,
    mapeo_columnas=_snake_map(OEFA_HEADERS, OEFA_CANONICAL),
    tipos=OEFA_GENERATED_TYPES,
    columnas_obligatorias=frozenset({"denominacion"}),
    columnas_no_negativas=frozenset(
        {"perimetro", "area_m2", "area_ha", "cantidad_municipalidades_disponen"}
    ),
    columnas_fecha=frozenset({"fecha_corte"}),
    categorias={},
    campos_geograficos=frozenset(
        {"ubigeo", "departamento", "provincia", "distrito", "este", "norte", "zona"}
    ),
    campos_temporales=frozenset({"fecha_corte", "anio_incorporacion"}),
    unidades={
        "este": "coordenada",
        "norte": "coordenada",
        "perimetro": "unidad original del dataset",
        "area_m2": "m²",
        "area_ha": "ha",
    },
    claves_duplicado=("id_uf", "municipalidad_administra"),
)


PERFILES_FUENTE = {
    MINAM_GENERACION_ANUAL.identificador: MINAM_GENERACION_ANUAL,
    OEFA_AREAS_DEGRADADAS.identificador: OEFA_AREAS_DEGRADADAS,
}


def obtener_perfil(identificador: str) -> PerfilFuenteETL:
    try:
        return PERFILES_FUENTE[identificador]
    except KeyError as error:
        raise ValueError(f"Perfil ETL desconocido: {identificador}.") from error
