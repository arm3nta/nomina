import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import base64
from PIL import Image

# 1. CONFIGURACIÓN DE PESTAÑA
try:
    img_favicon = Image.open("DGCFT.png")
except:
    img_favicon = "💵"

st.set_page_config(
    page_title="Control de Nómina", 
    page_icon=img_favicon, 
    layout="wide"
)

# 2. FUNCIÓN PARA EL FONDO
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    try:
        bin_str = get_base64(png_file)
        page_bg_img = f'''
        <style>
        .stMarkdown {
    background-color: rgba(255, 255, 255, 0.8);
    padding: 10px;
    border-radius: 5px;
}
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        st.sidebar.error("No se pudo cargar la imagen de fondo. Revisa el nombre en GitHub.")

# 3. ACTIVAR EL FONDO (Asegúrate de que el nombre sea exacto al de GitHub)
set_background('SCEO_VER.png')

st.title("📊 Calculadora de Nómina Anual")

# ... (Acá inicia el código de funciones y procesado de PDF)
def limpiar_numero(texto):
    if not texto: return 0.0
    try:
        # Quita todo lo que no sea número o punto
        limpio = re.sub(r'[^\d.]', '', str(texto))
        return float(limpio)
    except: return 0.0

def extraer_folio(texto):
    # Intento 1: Buscar después de "No. DE COMPROBANTE" (incluyendo saltos de línea)
    match = re.search(r'COMPROBANTE\s*[\n\r]*\s*(\d+)', texto, re.IGNORECASE)
    if match: return match.group(1)
    
    # Intento 2: Buscar cualquier número de 8 dígitos (formato común de comprobante)
    match_ocho = re.search(r'\b\d{8}\b', texto)
    if match_ocho: return match_ocho.group(0)
    
    return "Desconocido"

uploaded_files = st.file_uploader("Sube tus recibos PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    datos_recibos = []
    folios_vistos = {} 
    duplicados_encontrados = []

    for uploaded_file in uploaded_files:
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text() or ""
            
            # --- LOCALIZACIÓN DE DATOS ---
            folio = extraer_folio(texto_completo)

            # --- DETECCIÓN DE DUPLICADOS ---
            if folio != "Desconocido":
                if folio in folios_vistos:
                    duplicados_encontrados.append({
                        "folio": folio,
                        "archivo": uploaded_file.name
                    })
                    continue # SALTA EL ARCHIVO REPETIDO
                folios_vistos[folio] = uploaded_file.name

            # Búsqueda de Percepciones e ISR
            p_match = re.search(r'PERCEPCIONES.*?\n.*?\$?\s*([\d,]+\.\d{2})', texto_completo)
            percepciones = limpiar_numero(p_match.group(1)) if p_match else 0.0

            i_match = re.search(r'IMPUESTO SOBRE LA RENTA.*?([\d,]+\.\d{2})', texto_completo, re.IGNORECASE)
            isr = limpiar_numero(i_match.group(1)) if i_match else 0.0

            es_aguinaldo = "aguinaldo" in texto_completo.lower() or "gratificacion anual" in texto_completo.lower()

            datos_recibos.append({
                "Folio": folio,
                "Tipo": "Aguinaldo" if es_aguinaldo else "Ordinaria",
                "Percepciones": percepciones,
                "ISR": isr,
                "Archivo": uploaded_file.name
            })

    # --- MOSTRAR ALERTAS ---
    if duplicados_encontrados:
        for d in duplicados_encontrados:
            st.warning(f"⚠️ **Omitido:** El folio {d['folio']} ya estaba en el sistema (Archivo: {d['archivo']})")

    if datos_recibos:
        df = pd.DataFrame(datos_recibos)
        
        # TABLAS DE RESULTADOS
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        reg = df[df['Tipo'] == "Ordinaria"]
        agu = df[df['Tipo'] == "Aguinaldo"]

        with col1:
            st.info("🏠 **Ordinaria**")
            st.write(f"Perc: ${reg['Percepciones'].sum():,.2f}")
            st.write(f"ISR: ${reg['ISR'].sum():,.2f}")

        with col2:
            st.info("🎁 **Aguinaldo**")
            st.write(f"Perc: ${agu['Percepciones'].sum():,.2f}")
            st.write(f"ISR: ${agu['ISR'].sum():,.2f}")

        with col3:
            st.success("🌎 **Global**")
            t_p = df['Percepciones'].sum()
            t_i = df['ISR'].sum()
            st.write(f"Perc: ${t_p:,.2f}")
            st.write(f"ISR: ${t_i:,.2f}")

        st.success(f"### 💰 RESTA FINAL: ${t_p - t_i:,.2f}")
        
        st.subheader("📋 Detalle de archivos (Revisa que el Folio NO sea Desconocido)")
        st.dataframe(df)
