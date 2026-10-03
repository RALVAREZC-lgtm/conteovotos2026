import os
import io
import re
import random
import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA RESPONSIVA (MÓVIL Y WEB)
# ==============================================================================
st.set_page_config(
    page_title="Sistema de Conteo de Votos e IA - Tacna 2026",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1B3B6F 100%);
        color: white;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
    }
    .main-header h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 700;
    }
    .main-header p {
        margin: 2px 0 0 0;
        font-size: 12px;
        opacity: 0.85;
    }
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        text-align: center;
    }
    .badge-ok {
        background-color: #DCFCE7;
        color: #15803D;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 6px;
    }
    .badge-obs {
        background-color: #FEE2E2;
        color: #B91C1C;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 6px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CARGA Y REPARACIÓN AUTOMÁTICA DE LA BASE DE DATOS DE MESAS
# ==============================================================================
@st.cache_data
def cargar_base_mesas():
    archivo_origen = "EMR_MESAS_TACNA_AN.xlsx"
    archivo_fixed = "EMR_MESAS_TACNA_AN_fixed.xlsx"
    
    # Intentar cargar el archivo reparado o crearlo si no existe
    if os.path.exists(archivo_fixed):
        df = pd.read_excel(archivo_fixed)
    elif os.path.exists(archivo_origen):
        import zipfile
        with zipfile.ZipFile(archivo_origen, 'r') as zin:
            with zipfile.ZipFile(archivo_fixed, 'w') as zout:
                for item in zin.infolist():
                    buffer = zin.read(item.filename)
                    if item.filename.endswith('.xml'):
                        content = buffer.decode('utf-8', errors='ignore')
                        content = re.sub(r'<autoFilter.*?</autoFilter>', '', content, flags=re.DOTALL)
                        content = re.sub(r'<autoFilter.*?/>', '', content, flags=re.DOTALL)
                        content = re.sub(r'<conditionalFormatting.*?</conditionalFormatting>', '', content, flags=re.DOTALL)
                        buffer = content.encode('utf-8')
                    zout.writestr(item, buffer)
        df = pd.read_excel(archivo_fixed)
    else:
        # Dataframe por defecto si no están los archivos
        df = pd.DataFrame({
            "DEPARTAMENTO": ["TACNA"],
            "PROVINCIA": ["TACNA"],
            "DISTRITO": ["TACNA"],
            "NOMBRE DE LOCAL DE VOTACIÓN": ["IE 42015 ZOILA SABEL CACERES"],
            "DIRECCION DEL LOCAL DE VOTACIÓN": ["CALLE SAN MARCOS 810"],
            "MESA DE SUFRAGIO": [78981],
            "ELECTORES": [300]
        })

    df["MESA_STR"] = df["MESA DE SUFRAGIO"].fillna(0).astype(int).astype(str).str.zfill(6)
    return df

df_mesas = cargar_base_mesas()

# Inicializar Base de Datos de Actas en Sesión
if "db_actas" not in st.session_state:
    st.session_state.db_actas = []

PARTIDOS_POLITICOS = [
    "MOVIMIENTO REGIONAL TACNA UNIDA",
    "ALIANZA PARA EL PROGRESO",
    "PARTIDO FRENTE ESPERANZA",
    "ACCION POPULAR",
    "FUERZA POPULAR",
    "PARTIDO SOMOS PERU"
]

# ==============================================================================
# 3. MOTOR SIMULADO DE IA / OCR (LECTURA DE ACTAS)
# ==============================================================================
def procesar_acta_con_ia(imagen_bytes, electores_habiles):
    # Simula la extracción OCR realizada por el modelo de IA
    random.seed(len(imagen_bytes))
    
    total_ciudadanos = int(electores_habiles * random.uniform(0.65, 0.88))
    votos_restantes = total_ciudadanos
    
    resultados = {}
    for i, partido in enumerate(PARTIDOS_POLITICOS):
        if i == len(PARTIDOS_POLITICOS) - 1:
            voto = max(0, int(votos_restantes * random.uniform(0.4, 0.7)))
        else:
            voto = random.randint(5, max(6, int(votos_restantes * 0.35)))
        votos_restantes -= voto
        resultados[partido] = voto

    blancos = random.randint(2, 12)
    nulos = max(0, votos_restantes - blancos)
    
    resultados["VOTOS BLANCOS"] = blancos
    resultados["VOTOS NULOS"] = nulos
    
    suma_total = sum(resultados.values())
    confianza = round(random.uniform(93.5, 99.2), 1)
    
    # Validación matemática
    es_valida = (suma_total == total_ciudadanos) and (suma_total <= electores_habiles)
    
    return {
        "resultados": resultados,
        "total_concursantes": suma_total,
        "total_ciudadanos_votaron": total_ciudadanos,
        "confianza_ocr": confianza,
        "estado": "VÁLIDA" if es_valida else "OBSERVADA",
        "observacion": "Suma matemática correcta" if es_valida else "Diferencia entre total emitido y votos contados"
    }

# ==============================================================================
# 4. ENCABEZADO Y MENÚ PRINCIPAL
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <h2>🗳️ SISTEMA DE CONTEO Y ESCANEO DE ACTAS CON IA</h2>
        <p>Elecciones Municipales y Regionales - Tacna 2026</p>
    </div>
    """,
    unsafe_allow_html=True,
)

menu = st.option_menu if hasattr(st, "option_menu") else None
opcion = st.radio(
    "Selecciona Módulo:",
    ["📷 Captura de Acta (Móvil/Web)", "📊 Dashboard de Conteo", "🗄️ Base de Datos de Actas"],
    horizontal=True
)

st.divider()

# ==============================================================================
# MÓDULO 1: CAPTURA Y PROCESAMIENTO DE ACTAS
# ==============================================================================
if opcion == "📷 Captura de Acta (Móvil/Web)":
    st.subheader("📸 Captura y Procesamiento de Acta por IA")
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        distrito_sel = st.selectbox("1. Distrito", sorted(df_mesas["DISTRITO"].unique()))
    with col_sel2:
        df_dist = df_mesas[df_mesas["DISTRITO"] == distrito_sel]
        local_sel = st.selectbox("2. Local de Votación", sorted(df_dist["NOMBRE DE LOCAL DE VOTACIÓN"].unique()))
    
    df_loc = df_dist[df_dist["NOMBRE DE LOCAL DE VOTACIÓN"] == local_sel]
    mesa_sel = st.selectbox("3. Número de Mesa de Sufragio", df_loc["MESA_STR"].tolist())
    
    datos_mesa = df_loc[df_loc["MESA_STR"] == mesa_sel].iloc[0]
    electores = int(datos_mesa.get("ELECTORES", 300))
    
    st.info(f"📍 **Local:** {local_sel} | **Dirección:** {datos_mesa.get('DIRECCION DEL LOCAL DE VOTACIÓN', 'N/A')} | 👥 **Electores Hábiles:** {electores}")

    st.write("---")
    st.write("**Capturar o Cargar Foto del Acta:**")
    
    origen_foto = st.radio("Fuente de Imagen:", ["Cámara del Dispositivo", "Subir Archivo de Imagen"], horizontal=True)
    
    imagen_capturada = None
    if origen_foto == "Cámara del Dispositivo":
        foto_cam = st.camera_input("Toma una foto clara del acta de escrutinio")
        if foto_cam:
            imagen_capturada = foto_cam.getvalue()
    else:
        foto_file = st.file_uploader("Cargar imagen del acta (.jpg, .png)", type=["jpg", "jpeg", "png"])
        if foto_file:
            imagen_capturada = foto_file.getvalue()

    if imagen_capturada:
        col_img, col_proc = st.columns([1, 1])
        
        with col_img:
            st.image(imagen_capturada, caption=f"Acta Mesa N° {mesa_sel}", use_column_width=True)
            
        with col_proc:
            st.markdown("### 🤖 Análisis del Motor IA (OCR)")
            with st.spinner("Procesando imagen, detectando números y validando sumas..."):
                res_ia = procesar_acta_con_ia(imagen_capturada, electores)
            
            st.metric("Grado de Confianza OCR", f"{res_ia['confianza_ocr']}%")
            
            if res_ia["estado"] == "VÁLIDA":
                st.markdown(f"<span class='badge-ok'>Estatus: {res_ia['estado']}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='badge-obs'>Estatus: {res_ia['estado']}</span>", unsafe_allow_html=True)
            
            st.caption(f"Detalle: {res_ia['observacion']}")
            
            st.write("#### Votos Detectados por Organización:")
            df_res = pd.DataFrame(list(res_ia["resultados"].items()), columns=["Agrupación / Opción", "Votos"])
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            st.write(f"**Total Votos Válidos + Blancos/Nulos:** {res_ia['total_concursantes']}")
            st.write(f"**Total Ciudadanos que Votaron:** {res_ia['total_ciudadanos_votaron']}")
            
            if st.button("💾 Registrar y Guardar Acta en Base de Datos", use_container_width=True):
                # Guardar registro
                registro = {
                    "mesa": mesa_sel,
                    "distrito": distrito_sel,
                    "local": local_sel,
                    "electores": electores,
                    "confianza": res_ia["confianza_ocr"],
                    "estado": res_ia["estado"],
                    "votos": res_ia["resultados"],
                    "total_emitido": res_ia["total_concursantes"],
                    "imagen": imagen_capturada
                }
                st.session_state.db_actas.append(registro)
                st.success(f"¡Acta de la Mesa {mesa_sel} registrada correctamente!")

# ==============================================================================
# MÓDULO 2: DASHBOARD ESTADÍSTICO DE RESULTADOS
# ==============================================================================
elif opcion == "📊 Dashboard de Conteo":
    st.subheader("📊 Avance del Conteo y Resultados Consolidados")
    
    total_mesas = len(df_mesas)
    actas_ingresadas = len(st.session_state.db_actas)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mesas Totales (Padrón)", f"{total_mesas:,}")
    m2.metric("Actas Procesadas", f"{actas_ingresadas:,}")
    m3.metric("% Avance", f"{(actas_ingresadas / total_mesas * 100):.2f}%" if total_mesas > 0 else "0%")
    
    actas_obs = sum(1 for a in st.session_state.db_actas if a["estado"] == "OBSERVADA")
    m4.metric("Actas Observadas", f"{actas_obs}")

    st.write("---")
    
    if st.session_state.db_actas:
        # Consolidar votos totales
        conteo_partidos = {p: 0 for p in PARTIDOS_POLITICOS}
        conteo_partidos["VOTOS BLANCOS"] = 0
        conteo_partidos["VOTOS NULOS"] = 0
        
        for acta in st.session_state.db_actas:
            for k, v in acta["votos"].items():
                conteo_partidos[k] = conteo_partidos.get(k, 0) + v
                
        df_totales = pd.DataFrame(list(conteo_partidos.items()), columns=["Agrupación", "Total Votos"]).sort_values(by="Total Votos", ascending=False)
        
        c_graf1, c_graf2 = st.columns([1.2, 0.8])
        
        with c_graf1:
            fig_bar = px.bar(
                df_totales,
                x="Total Votos",
                y="Agrupación",
                orientation="h",
                text="Total Votos",
                title="Resultados Consolidados por Organización Polítca",
                color="Total Votos",
                color_continuous_scale="Viridis"
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c_graf2:
            fig_pie = px.pie(
                df_totales,
                names="Agrupación",
                values="Total Votos",
                title="Distribución de Votos",
                hole=0.4
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("Aún no se han registrado actas. Utiliza el módulo de **Captura de Acta** para registrar las primeras lecturas.")

# ==============================================================================
# MÓDULO 3: BASE DE DATOS Y AUDITORÍA DE ACTAS
# ==============================================================================
elif opcion == "🗄️ Base de Datos de Actas":
    st.subheader("🗄️ Registro Histórico y Auditoría de Actas Digitalizadas")
    
    if st.session_state.db_actas:
        tabla_data = []
        for a in st.session_state.db_actas:
            tabla_data.append({
                "Mesa": a["mesa"],
                "Distrito": a["distrito"],
                "Local": a["local"],
                "Confianza IA": f"{a['confianza']}%",
                "Total Votos": a["total_emitido"],
                "Estado": a["estado"]
            })
            
        st.dataframe(pd.DataFrame(tabla_data), use_container_width=True)
        
        st.write("---")
        st.write("**Visualizar Ficha de Acta Específica:**")
        
        mesas_reg = [a["mesa"] for a in st.session_state.db_actas]
        mesa_ver = st.selectbox("Seleccione Mesa a Inspeccionar:", mesas_reg)
        
        acta_obj = next(a for a in st.session_state.db_actas if a["mesa"] == mesa_ver)
        
        col_img_v, col_dat_v = st.columns(2)
        with col_img_v:
            st.image(acta_obj["imagen"], caption=f"Imagen almacenada - Mesa {mesa_ver}", use_column_width=True)
        with col_dat_v:
            st.write(f"**Distrito:** {acta_obj['distrito']}")
            st.write(f"**Local:** {acta_obj['local']}")
            st.write(f"**Estado:** {acta_obj['estado']}")
            st.write(f"**Confianza OCR:** {acta_obj['confianza']}%")
            st.write("**Desglose de Votos:**")
            st.json(acta_obj["votos"])
    else:
        st.info("No hay actas registradas en la base de datos.")