import streamlit as st
import pandas as pd
from pathlib import Path

# -------------------------------
# Configuración general
# -------------------------------
st.set_page_config(page_title="Simulador de Payback", page_icon="🚗", layout="centered")
st.title("📈 Simulador de Payback: Eléctrico vs Combustión")

# -------------------------------
# Cargar datos desde Excel
# -------------------------------

def cargar_datos_excel(ruta_excel):
    xls = pd.ExcelFile(ruta_excel)
    vehiculos = xls.parse("Vehículos")
    config = xls.parse("Configuración")
    return vehiculos, config

ruta_excel = st.file_uploader("Sube el archivo de datos", type=[".xlsx"])

if ruta_excel is not None:
    vehiculos_df, config_df = cargar_datos_excel(ruta_excel)

    # -------------------------------
    # Extraer configuración
    # -------------------------------
    config_dict = config_df.set_index("Parámetro").to_dict()["Valor"]
    tipo_cambio = config_dict.get("Tipo de cambio (S/ a USD)", 3.75)
    precio_gasolina = config_dict.get("Costo gasolina (PEN/gal)", 15.99)
    precio_electricidad = config_dict.get("Costo electricidad (PEN/kWh)", 0.5634)

    # -------------------------------
    # Separar vehículos por tipo
    # -------------------------------
    autos_combustion = vehiculos_df[vehiculos_df["Tipo"] == "Combustión"]
    autos_electricos = vehiculos_df[vehiculos_df["Tipo"] == "Eléctrico"]

    # -------------------------------
    # Selección de autos
    # -------------------------------
    st.sidebar.header("1. Selecciona los modelos")

    auto_gas = st.sidebar.selectbox("Auto a gasolina", autos_combustion["Marca"])
    auto_elec = st.sidebar.selectbox("Auto eléctrico", autos_electricos["Marca"])

    # -------------------------------
    # Parámetros de simulación
    # -------------------------------
    st.sidebar.header("2. Parámetros de uso")
    km_anuales = st.sidebar.slider("Kilómetros por año", 5000, 40000, 15000, step=1000)
    años = st.sidebar.slider("Años de análisis", 1, 15, 10)

    # -------------------------------
    # Extraer datos de cada auto
    # -------------------------------
    datos_gas = autos_combustion[vehiculos_df["Marca"] == auto_gas].iloc[0]
    datos_elec = autos_electricos[vehiculos_df["Marca"] == auto_elec].iloc[0]

    precio_gas = datos_gas["Precio USD"] * tipo_cambio
    precio_elec = datos_elec["Precio USD"] * tipo_cambio

    consumo_gas_km_l = datos_gas["Consumo (km/l)"]
    consumo_elec_kwh_km = datos_elec["Consumo (kWh/km)"]

    galon_litros = 3.78541
    costo_combustible_anual = lambda km: (km / consumo_gas_km_l) * (precio_gasolina / galon_litros)
    costo_electrico_anual = lambda km: km * consumo_elec_kwh_km * precio_electricidad

    # -------------------------------
    # Calcular costos acumulados
    # -------------------------------
    costos = []
    total_gas = precio_gas
    total_elec = precio_elec

    for año in range(años + 1):
        if año > 0:
            total_gas += costo_combustible_anual(km_anuales)
            total_elec += costo_electrico_anual(km_anuales)
        costos.append({
            "Año": año,
            auto_gas: total_gas,
            auto_elec: total_elec,
            "Diferencia acumulada (S/)": total_gas - total_elec
        })

    df_resultados = pd.DataFrame(costos)

    # -------------------------------
    # Mostrar resultados
    # -------------------------------
    st.subheader("Comparación de costos acumulados")
    st.line_chart(df_resultados.set_index("Año")[[auto_gas, auto_elec]])

    breakeven = df_resultados[df_resultados[auto_elec] <= df_resultados[auto_gas]]
    if not breakeven.empty:
        año_equilibrio = int(breakeven.iloc[0]["Año"])
        st.success(f"📌 El punto de equilibrio se alcanza en el año {año_equilibrio}.")
    else:
        st.info("❕ Dentro del horizonte seleccionado, el auto eléctrico no alcanza el punto de equilibrio.")

    with st.expander("Ver tabla de resultados"):
        st.dataframe(df_resultados, use_container_width=True)
else:
    st.info("Por favor, sube el archivo Excel con las hojas 'Vehículos' y 'Configuración'.")
