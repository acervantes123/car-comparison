import streamlit as st
import pandas as pd
from pathlib import Path

# -------------------------------------------------
# Configuración general de la aplicación
# -------------------------------------------------
st.set_page_config(
    page_title="Simulador de Payback – Eléctrico vs Combustión",
    page_icon="🚗",
    layout="centered",
)

st.title("📈 Simulador de Payback: Auto Eléctrico vs. Auto a Gasolina")

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
    "Auto eléctrico",
    electric_df["Nombre"],
)

st.sidebar.header("2. Parámetros de uso")
KM_ANUALES = st.sidebar.slider("Kilómetros por año", 5_000, 40_000, 15_000, step=1_000)
ANIOS = st.sidebar.slider("Horizonte de análisis (años)", 1, 15, 10)

# -------------------------------------------------
# Extraer la fila correspondiente a cada vehículo
# -------------------------------------------------
row_gas = combustion_df[combustion_df["Nombre"] == nombre_gas].iloc[0]
row_elec = electric_df[electric_df["Nombre"] == nombre_elec].iloc[0]

precio_gas_soles = row_gas["Precio (USD)"] * TIPO_CAMBIO
precio_elec_soles = row_elec["Precio (USD)"] * TIPO_CAMBIO

consumo_km_l = row_gas["Consumo (km/l)"]
consumo_kwh_km = row_elec["Consumo (kWh/km)"]

# Validaciones básicas
if consumo_km_l <= 0 or pd.isna(consumo_km_l):
    st.error("El consumo (km/l) del vehículo a gasolina debe ser > 0.")
    st.stop()
if consumo_kwh_km <= 0 or pd.isna(consumo_kwh_km):
    st.error("El consumo (kWh/km) del vehículo eléctrico debe ser > 0.")
    st.stop()

# -------------------------------------------------
# Funciones de costo anual
# -------------------------------------------------

def costo_anual_gasolina(km):
    litros_consumidos = km / consumo_km_l
    costo_litro = PRECIO_GASOLINA / LITROS_POR_GALON
    return litros_consumidos * costo_litro


def costo_anual_electrico(km):
    return km * consumo_kwh_km * PRECIO_ELECTRICIDAD

# -------------------------------------------------
# Calcular costos acumulados
# -------------------------------------------------
resultados = []
costo_acum_gas = precio_gas_soles
costo_acum_elec = precio_elec_soles

for anio in range(ANIOS + 1):
    if anio > 0:
        costo_acum_gas += costo_anual_gasolina(KM_ANUALES)
        costo_acum_elec += costo_anual_electrico(KM_ANUALES)
    resultados.append({
        "Año": anio,
        nombre_gas: round(costo_acum_gas, 2),
        nombre_elec: round(costo_acum_elec, 2),
        "Diferencia (S/)": round(costo_acum_gas - costo_acum_elec, 2),
    })

resultados_df = pd.DataFrame(resultados)

# -------------------------------------------------
# Visualización
# -------------------------------------------------
st.subheader("Costos acumulados")
st.line_chart(resultados_df.set_index("Año")[[nombre_gas, nombre_elec]])

# Punto de equilibrio
breakeven_rows = resultados_df[resultados_df[nombre_elec] <= resultados_df[nombre_gas]]
if not breakeven_rows.empty:
    anio_equilibrio = int(breakeven_rows.iloc[0]["Año"])
    st.success(f"📌 El auto eléctrico alcanza el punto de equilibrio en el año {anio_equilibrio}.")
else:
    st.info("❕ En el horizonte seleccionado, el auto eléctrico no alcanza el punto de equilibrio.")

# Tabla detallada
with st.expander("Ver tabla de resultados"):
    st.dataframe(resultados_df, use_container_width=True)

