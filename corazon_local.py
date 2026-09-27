"""
Aplicación de Registro de Salud Personal
Autor: Asistente de IA para el Prof. Justo
Descripción: Interfaz web para registrar y consultar mediciones de presión arterial, 
             pulso, SpO2 y peso, con almacenamiento permanente en SQLite.
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS (SQLite)
# ==============================================================================

DB_NAME = "registro_salud_justo.db"

def init_db():
    """
    Inicializa la base de datos SQLite y crea la tabla de mediciones si no existe.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            sistolica INTEGER NOT NULL,
            diastolica INTEGER NOT NULL,
            pulsaciones INTEGER NOT NULL,
            spo2 INTEGER,
            peso REAL,
            observaciones TEXT
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_mediciones_fecha_hora ON mediciones (fecha_hora)')
    conn.commit()
    conn.close()

def insertar_medicion(fecha_hora, sistolica, diastolica, pulsaciones, spo2, peso, observaciones):
    """
    Inserta un nuevo registro de medición en la base de datos.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mediciones (fecha_hora, sistolica, diastolica, pulsaciones, spo2, peso, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (fecha_hora, sistolica, diastolica, pulsaciones, spo2, peso, observaciones))
    conn.commit()
    conn.close()

def obtener_mediciones():
    """
    Recupera todas las mediciones de la base de datos y las retorna como un DataFrame de pandas.
    """
    conn = sqlite3.connect(DB_NAME)
    # Se consulta ordenando por fecha_hora de forma descendente (más recientes primero)
    df = pd.read_sql_query("SELECT * FROM mediciones ORDER BY fecha_hora DESC", conn)
    conn.close()
    return df

def importar_excel(ruta_excel):
    """
    Importa la hoja Justo del Excel y evita duplicados por fecha y hora.
    Retorna la cantidad de registros nuevos y filas omitidas.
    """
    columnas = {
        "Fecha": "fecha",
        "Hora": "hora",
        "Sistólica": "sistolica",
        "Diastólica": "diastolica",
        "Pulsaciones": "pulsaciones",
        "SpO2": "spo2",
        "Peso": "peso",
        "OBSERVACIONES ": "observaciones",
    }
    df = pd.read_excel(ruta_excel, sheet_name="Justo")
    faltantes = set(columnas) - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}")

    df = df.rename(columns=columnas)
    df["fecha_hora"] = pd.to_datetime(
        df["fecha"].astype(str) + " " + df["hora"].astype(str), errors="coerce"
    )
    requeridas = ["fecha_hora", "sistolica", "diastolica", "pulsaciones"]
    filas_omitidas = int(df[requeridas].isna().any(axis=1).sum())
    df = df.dropna(subset=requeridas)

    registros = []
    for fila in df.itertuples(index=False):
        registros.append((
            fila.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
            int(fila.sistolica),
            int(fila.diastolica),
            int(fila.pulsaciones),
            None if pd.isna(fila.spo2) else int(fila.spo2),
            None if pd.isna(fila.peso) else float(fila.peso),
            None if pd.isna(fila.observaciones) else str(fila.observaciones),
        ))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR IGNORE INTO mediciones
        (fecha_hora, sistolica, diastolica, pulsaciones, spo2, peso, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', registros)
    nuevos = cursor.rowcount
    conn.commit()
    conn.close()
    return nuevos, filas_omitidas

# ==============================================================================
# 2. INTERFAZ DE USUARIO (Streamlit)
# ==============================================================================

def main():
    """
    Función principal que renderiza la interfaz gráfica de la aplicación.
    """
    # Inicializar base de datos al cargar la app
    init_db()

    st.set_page_config(page_title="Registro de Salud", page_icon="❤️", layout="wide")
    st.title("❤️ Registro y Control de Salud Personal")
    st.markdown("Sistema para el seguimiento de presión arterial, pulso, SpO2 y peso.")

    # Crear pestañas para organizar la interfaz
    tab1, tab2 = st.tabs(["📝 Registrar Nueva Medición", "📊 Historial y Estadísticas"])

    # --------------------------------------------------------------------------
    # PESTAÑA 1: FORMULARIO DE REGISTRO
    # --------------------------------------------------------------------------
    with tab1:
        st.header("Nueva Medición")

        archivo_excel = st.file_uploader(
            "Importar registros desde Excel",
            type=["xlsx"],
            help="Selecciona la hoja Justo de tu archivo Corazón.xlsx.",
        )
        if archivo_excel is not None and st.button("Importar datos", type="primary"):
            try:
                nuevos, omitidos = importar_excel(archivo_excel)
                st.success(f"Importación completada: {nuevos} registros nuevos.")
                if omitidos:
                    st.warning(f"Se omitieron {omitidos} filas incompletas.")
                st.rerun()
            except (ValueError, KeyError) as error:
                st.error(f"No se pudo importar el archivo: {error}")
        
        with st.form("form_medicion"):
            # Campos de entrada organizados en columnas
            col1, col2 = st.columns(2)
            
            with col1:
                fecha = st.date_input("Fecha", value=datetime.today())
                hora = st.time_input("Hora", value=datetime.now().time())
                sistolica = st.number_input("Presión Sistólica (mmHg)", min_value=50, max_value=250, step=1)
                diastolica = st.number_input("Presión Diastólica (mmHg)", min_value=30, max_value=150, step=1)
            
            with col2:
                pulsaciones = st.number_input("Pulsaciones (lpm)", min_value=30, max_value=200, step=1)
                spo2 = st.number_input("SpO2 (%)", min_value=50, max_value=100, step=1)
                peso = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, step=0.1, format="%.1f")
                observaciones = st.text_area("Observaciones (Medicamentos, dieta, síntomas, etc.)", height=150)
            
            # Botón de envío
            submitted = st.form_submit_button("Guardar Medición", use_container_width=True)
            
            if submitted:
                # Combinar fecha y hora en un solo string ISO
                fecha_hora_str = datetime.combine(fecha, hora).strftime("%Y-%m-%d %H:%M:%S")
                
                # Guardar en la base de datos
                insertar_medicion(fecha_hora_str, int(sistolica), int(diastolica), 
                                  int(pulsaciones), int(spo2), float(peso), observaciones)
                
                st.success("✅ Medición guardada exitosamente en la base de datos permanente.")
                st.balloons()

    # --------------------------------------------------------------------------
    # PESTAÑA 2: HISTORIAL Y VISUALIZACIÓN
    # --------------------------------------------------------------------------
    with tab2:
        st.header("Historial de Mediciones")
        
        # Obtener datos
        df = obtener_mediciones()
        
        if df.empty:
            st.info("No hay mediciones registradas aún. Por favor, registre su primera medición en la pestaña anterior.")
        else:
            # Mostrar tabla de datos
            st.dataframe(df, use_container_width=True)
            
            st.subheader("Descarga de Datos")
            # Opción para exportar a CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Historial en CSV",
                data=csv,
                file_name="historial_salud.csv",
                mime="text/csv",
            )
            
            # Gráficas básicas de tendencia
            st.subheader("Tendencias")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.line_chart(df[['fecha_hora', 'sistolica', 'diastolica']].set_index('fecha_hora'), 
                              color=["#ff4b4b", "#ffa500"], 
                              y_label="mmHg")
                st.caption("Tendencia de Presión Arterial")
                
            with col_g2:
                st.line_chart(df[['fecha_hora', 'pulsaciones']].set_index('fecha_hora'), 
                              color=["#0000ff"], 
                              y_label="lpm")
                st.caption("Tendencia de Pulsaciones")

if __name__ == "__main__":
    main()