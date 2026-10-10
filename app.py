from datetime import datetime
from html import escape

import matplotlib.pyplot as plt
import streamlit as st

from database import (
    obtener_registros,
    obtener_predicciones_recientes,
    obtener_zonas,
    preparar_base_datos,
    guardar_prediccion,
    registrar_residuo,
)
from ml_service import obtener_metricas_modelo, predecir_residuos

st.set_page_config(page_title="Residuos Arequipa", page_icon="♻️", layout="wide")


def mostrar_tabla(filas: list[dict]) -> None:
    """Muestra tablas sin depender de bibliotecas nativas bloqueadas en este equipo."""
    if not filas:
        st.info("No hay información disponible.")
        return

    columnas = list(filas[0])
    encabezados = "".join(f"<th>{escape(columna)}</th>" for columna in columnas)
    cuerpo = "".join(
        "<tr>"
        + "".join(f"<td>{escape(str(fila[columna]))}</td>" for columna in columnas)
        + "</tr>"
        for fila in filas
    )
    st.markdown(
        "<style>"
        "table{width:100%;border-collapse:collapse}"
        "th,td{padding:10px;text-align:left;border-bottom:1px solid #3a3d4a}"
        "th{background:#262730}"
        "</style>"
        f"<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table>",
        unsafe_allow_html=True,
    )


def conectar_base_datos() -> bool:
    try:
        preparar_base_datos()
        return True
    except Exception as error:
        st.error("No fue posible conectar con PostgreSQL.")
        st.info("Crea la base residuos_arequipa y completa DATABASE_URL en el archivo .env.")
        with st.expander("Detalle técnico"):
            st.code(str(error))
        return False


def mostrar_grafico_prediccion(acumulacion_previa: int, cantidad_estimada: int) -> None:
    figura, eje = plt.subplots(figsize=(7, 3.2))
    etiquetas = ["Acumulación previa", "Cantidad estimada"]
    valores = [acumulacion_previa, cantidad_estimada]
    colores = ["#5B8DEF", "#F05252"]
    barras = eje.bar(etiquetas, valores, color=colores, width=0.55)
    eje.set_ylabel("Kilogramos")
    eje.set_title("Comparación para la zona seleccionada")
    for barra, valor in zip(barras, valores):
        eje.text(barra.get_x() + barra.get_width() / 2, valor, f"{valor} kg", ha="center", va="bottom")
    figura.tight_layout()
    st.pyplot(figura, clear_figure=True)


st.title("♻️ Gestión Predictiva de Residuos — Arequipa")
st.caption("Primera versión funcional · Los datos iniciales son demostrativos.")

if conectar_base_datos():
    pagina = st.sidebar.radio(
        "Menú",
        ["Inicio", "Registrar residuo", "Consultar registros", "Generar predicción"],
    )
    zonas = obtener_zonas()

    if pagina == "Inicio":
        registros = obtener_registros()
        total_registros = len(registros)
        total_kg = sum(registro["Cantidad (kg)"] for registro in registros)
        c1, c2, c3 = st.columns(3)
        c1.metric("Zonas registradas", len(zonas))
        c2.metric("Registros disponibles", total_registros)
        c3.metric("Residuos registrados", f"{total_kg:,} kg")

        st.subheader("Objetivo de esta primera entrega")
        st.write(
            "Centralizar zonas y registros de residuos para preparar el modelo predictivo "
            "que se incorporará en el siguiente avance."
        )
        st.subheader("Zonas de demostración")
        mostrar_tabla(
            [
                {
                    "Distrito": zona.distrito.nombre,
                    "Zona": zona.nombre,
                    "Población estimada": zona.poblacion_estimada,
                }
                for zona in zonas
            ]
        )
        metricas = obtener_metricas_modelo()
        st.caption(
            "Motor demostrativo: Random Forest para estimación y clasificación. "
            f"Ajuste en datos simulados: {metricas['r2']}% · Clasificación: {metricas['exactitud']}%."
        )

    elif pagina == "Registrar residuo":
        st.subheader("Registrar cantidad de residuos")
        st.caption("Este registro se guardará en PostgreSQL como información ingresada manualmente.")
        opciones_zona = {f"{zona.distrito.nombre} — {zona.nombre}": zona.id for zona in zonas}
        with st.form("formulario_residuo", clear_on_submit=True):
            zona_seleccionada = st.selectbox("Distrito y zona", list(opciones_zona))
            columna_fecha, columna_hora = st.columns(2)
            fecha = columna_fecha.date_input("Fecha", value=datetime.now().date())
            hora = columna_hora.time_input("Hora", value=datetime.now().time().replace(second=0, microsecond=0))
            cantidad_kg = st.number_input("Cantidad recolectada (kg)", min_value=1, step=10)
            dias_sin_recoleccion = st.number_input("Días sin recolección", min_value=0, step=1)
            enviar = st.form_submit_button("Guardar registro", type="primary")

        if enviar:
            registrar_residuo(
                opciones_zona[zona_seleccionada], fecha, hora, int(cantidad_kg), int(dias_sin_recoleccion)
            )
            st.success("Registro guardado correctamente.")

    elif pagina == "Consultar registros":
        st.subheader("Registros de residuos")
        registros = obtener_registros()
        if registros:
            distrito = st.selectbox(
                "Filtrar por distrito",
                ["Todos"] + sorted({registro["Distrito"] for registro in registros}),
            )
            if distrito != "Todos":
                registros = [registro for registro in registros if registro["Distrito"] == distrito]
            mostrar_tabla(registros)
        else:
            st.info("Todavía no hay registros de residuos.")

    else:
        st.subheader("Predicción de acumulación")
        st.caption(
            "Resultado generado con datos demostrativos. No debe interpretarse como una predicción oficial."
        )
        opciones_zona = {f"{zona.distrito.nombre} — {zona.nombre}": zona for zona in zonas}
        with st.form("formulario_prediccion"):
            zona_seleccionada = st.selectbox("Distrito y zona", list(opciones_zona))
            columna_fecha, columna_hora = st.columns(2)
            fecha_prediccion = columna_fecha.date_input("Fecha de evaluación", value=datetime.now().date())
            hora_prediccion = columna_hora.time_input(
                "Hora de evaluación", value=datetime.now().time().replace(second=0, microsecond=0)
            )
            acumulacion_previa = st.number_input(
                "Acumulación previa estimada (kg)", min_value=0, value=500, step=50
            )
            dias_sin_recoleccion = st.number_input("Días sin recolección", min_value=0, value=1, step=1)
            ejecutar = st.form_submit_button("Generar predicción", type="primary")

        if ejecutar:
            zona = opciones_zona[zona_seleccionada]
            resultado = predecir_residuos(
                poblacion_estimada=zona.poblacion_estimada,
                dia_semana=fecha_prediccion.weekday(),
                hora=hora_prediccion.hour,
                dias_sin_recoleccion=int(dias_sin_recoleccion),
                acumulacion_previa_kg=int(acumulacion_previa),
            )
            guardar_prediccion(
                zona.id,
                fecha_prediccion,
                hora_prediccion,
                int(resultado["cantidad_estimada_kg"]),
                str(resultado["nivel"]),
                str(resultado["prioridad"]),
                str(resultado["recomendacion"]),
            )
            st.session_state["ultima_prediccion"] = {
                **resultado,
                "acumulacion_previa": int(acumulacion_previa),
                "zona": zona_seleccionada,
            }

        if "ultima_prediccion" in st.session_state:
            resultado = st.session_state["ultima_prediccion"]
            st.divider()
            st.subheader(f"Resultado: {resultado['zona']}")
            columna_kg, columna_nivel, columna_prioridad = st.columns(3)
            columna_kg.metric("Cantidad estimada", f"{resultado['cantidad_estimada_kg']:,} kg")
            columna_nivel.metric("Nivel de acumulación", resultado["nivel"])
            columna_prioridad.metric("Prioridad de atención", resultado["prioridad"])
            st.success(resultado["recomendacion"])
            mostrar_grafico_prediccion(
                int(resultado["acumulacion_previa"]), int(resultado["cantidad_estimada_kg"])
            )

        predicciones = obtener_predicciones_recientes()
        if predicciones:
            st.subheader("Predicciones recientes")
            mostrar_tabla(predicciones)
