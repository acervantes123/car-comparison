import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# -------------------------------------------------
# Configuración general de la aplicación
# -------------------------------------------------
st.set_page_config(
    page_title="Simulador de Plazo de Recuperación",
    layout="centered",
)

st.title("Simulador de Plazo de Recuperación")

# -------------------------------------------------
# Ruta del archivo Excel dentro del repositorio
# -------------------------------------------------
DATA_FILE = Path(__file__).parent / "DB_Car comparison.xlsx"

@st.cache_data(show_spinner="Cargando base de datos …")
def cargar_datos(path: Path):
    """Carga las hojas 'Vehículos' y 'Configuración' del Excel."""
    xls = pd.ExcelFile(path)
    vehiculos = xls.parse("Vehículos")
    config = (
        xls.parse("Configuración")
        .set_index("Parámetro")
        ["Valor"]
        .to_dict()
    )
    return vehiculos, config

# Comprobar que el archivo existe
if not DATA_FILE.exists():
    st.error(
        f"No se encontró el archivo de datos: {DATA_FILE}. "
        "Asegúrate de clonar el repositorio completo o de colocar el Excel en la misma carpeta que este script."
    )
    st.stop()

vehiculos_df, config = cargar_datos(DATA_FILE)

# -------------------------------------------------
# Parámetros globales desde la hoja Configuración
# -------------------------------------------------
TIPO_CAMBIO = config.get("Tipo de cambio (S/ a USD)", 3.75)
PRECIO_GASOLINA = config.get("Costo gasolina (PEN/gal)", 15.99)
PRECIO_ELECTRICIDAD = config.get("Costo electricidad (PEN/kWh)", 0.5634)
LITROS_POR_GALON = 3.78541

# -------------------------------------------------
# Preparar los dataframes de autos
# -------------------------------------------------
vehiculos_df["Nombre"] = vehiculos_df["Marca"].str.strip() + " " + vehiculos_df["Modelo"].str.strip()

combustion_df = vehiculos_df[vehiculos_df["Tipo"] == "Combustión"].copy()
electric_df = vehiculos_df[vehiculos_df["Tipo"] == "Eléctrico"].copy()

if combustion_df.empty or electric_df.empty:
    st.error("La base de datos debe contener al menos un vehículo de combustión y uno eléctrico.")
    st.stop()

# -------------------------------------------------
# Sidebar – selección de autos y parámetros de uso
# -------------------------------------------------
st.sidebar.header("1. Selecciona los modelos para comparar")

nombre_gas = st.sidebar.selectbox(
    "Auto a gasolina",
    combustion_df["Nombre"],
)
nombre_elec = st.sidebar.selectbox(
    "Auto híbrido/eléctrico",
    electric_df["Nombre"],
)

st.sidebar.header("2. Parámetros de uso")
KM_ANUALES = st.sidebar.slider("Recorrido anual estimado (km)", 5_000, 40_000, 15_000, step=1_000)
ANIOS = st.sidebar.slider("Horizonte de análisis (años)", 1, 15, 10)

# Botón para activar el cálculo
ejecutar = st.sidebar.button("Consultar")

if ejecutar:
    # -------------------------------------------------
    # Extraer la fila correspondiente a cada vehículo
    # -------------------------------------------------
    row_gas = combustion_df[combustion_df["Nombre"] == nombre_gas].iloc[0]
    row_elec = electric_df[electric_df["Nombre"] == nombre_elec].iloc[0]

    precio_gas_usd = row_gas["Precio (USD)"]
    precio_elec_usd = row_elec["Precio (USD)"]

    consumo_km_l = row_gas["Consumo (km/l)"]
    consumo_kwh_km = row_elec["Consumo (kWh/km)"]

    # Validaciones básicas
    if consumo_km_l <= 0 or pd.isna(consumo_km_l):
        st.error("El consumo (km/l) del vehículo a gasolina debe ser > 0.")
        st.stop()
    if consumo_kwh_km <= 0 or pd.isna(consumo_kwh_km):
        st.error("El consumo (kWh/km) del vehículo eléctrico debe ser > 0.")
        st.stop()

    # Mostrar los precios iniciales como indicadores (quitar esta sección en caso esté muy saturada la página)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
        f"""
        <div style='text-align: center; font-size: 0.8em;'>
            <strong>Precio inicial - {nombre_gas}:</strong> ${precio_gas_usd:,.0f} &nbsp;&nbsp;&nbsp;
            <strong>{nombre_elec}:</strong> ${precio_elec_usd:,.0f}
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------
    # Funciones de costo anual
    # -------------------------------------------------
    def costo_anual_gasolina(km):
        litros_consumidos = km / consumo_km_l
        costo_litro = PRECIO_GASOLINA / LITROS_POR_GALON
        return litros_consumidos * costo_litro / TIPO_CAMBIO

    def costo_anual_electrico(km):
        return (km * consumo_kwh_km * PRECIO_ELECTRICIDAD) / TIPO_CAMBIO

    # -------------------------------------------------
    # Calcular costos acumulados
    # -------------------------------------------------
    resultados = []
    costo_acum_gas = precio_gas_usd
    costo_acum_elec = precio_elec_usd

    for anio in range(ANIOS + 1):
        if anio > 0:
            costo_acum_gas += costo_anual_gasolina(KM_ANUALES)
            costo_acum_elec += costo_anual_electrico(KM_ANUALES)
        resultados.append({
            "Año": anio,
            nombre_gas: round(costo_acum_gas, 2),
            nombre_elec: round(costo_acum_elec, 2),
            "Diferencia (USD)": round(costo_acum_gas - costo_acum_elec, 2),
        })

    resultados_df = pd.DataFrame(resultados)

    # -------------------------------------------------
    # Visualización interactiva
    # -------------------------------------------------
    st.subheader("Evolucion de costos acumulados")
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=resultados_df["Año"],
        y=resultados_df[nombre_gas],
        mode='lines+markers',
        name=nombre_gas,
        marker=dict(size=5, color='#1f77b4')
    ))
    fig.add_trace(go.Scatter(
        x=resultados_df["Año"],
        y=resultados_df[nombre_elec],
        mode='lines+markers',
        name=nombre_elec,
        marker=dict(size=5, color='#2ca02c')
    ))

    fig.update_layout(
        xaxis_title="Años",
        yaxis_title="Costo (USD)",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=40, t=20, b=40),
        showlegend=True,
    )
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(tickformat=",.0f")

    st.plotly_chart(fig, use_container_width=True)

    # Punto de equilibrio
    breakeven = resultados_df[resultados_df["Diferencia (USD)"] <= 0]
    if not breakeven.empty:
        x1 = breakeven.iloc[0 - 1]["Año"]
        x2 = breakeven.iloc[0]["Año"]
        y1 = breakeven.iloc[0 - 1]["Diferencia (USD)"]
        y2 = breakeven.iloc[0]["Diferencia (USD)"]
        pendiente = (y2 - y1) / (x2 - x1)
        interseccion = x2 - (y2 / pendiente)
        st.success(f"Se alcanza el punto de equilibrio en {interseccion:.1f} años.")
    else:
        st.info("❕ En el horizonte seleccionado, el auto eléctrico no alcanza el punto de equilibrio.")

    # Tabla detallada
    with st.expander("Tabla de resultados"):
        st.dataframe(resultados_df, use_container_width=True)
else:
    st.info("Usa el botón de la izquierda para ejecutar la simulación.")
