import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

# Configuración visual de la página
st.set_page_config(page_title="Analizador de Nómina Pro", layout="wide")

st.title("📊 Analizador de Nómina (Anti-Duplicados)")
st.markdown("Sube tus PDFs. El sistema detectará automáticamente si hay recibos repetidos y los excluirá.")

def limpiar_numero(texto):
    if not texto: return 0.0
    try:
        limpio = re.sub(r'[^\d.]', '', str(texto))
        return float(limpio)
    except:
        return 0.0

# --- CARGA DE ARCHIVOS ---
uploaded_files = st.file_uploader("Arrastra aquí tus recibos de nómina", type="pdf", accept_multiple_files=True)

if uploaded_files:
    datos_recibos = []
    folios_vistos = {} # Usamos un diccionario para saber en qué archivo apareció primero
    duplicados_encontrados = []

    for uploaded_file in uploaded_files:
        # Volvemos a leer el archivo desde el principio
        bytes_data = uploaded_file.getvalue()
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text() or ""
            
            # 1. BUSCAR FOLIO (Ajustado a tu formato SEP)
            folio_match = re.search(r'No\.\s*DE\s*COMPROBANTE\s*[\n\r]*\s*(\d+)', texto_completo, re.IGNORECASE)
            folio = folio_match.group(1) if folio_match else "Desconocido"

            # --- VALIDACIÓN DE DUPLICADOS ---
            if folio != "Desconocido":
                if folio in folios_vistos:
                    # Si ya existe, lo guardamos para avisar pero NO lo procesamos
                    duplicados_encontrados.append({
                        "folio": folio,
                        "archivo_actual": uploaded_file.name,
                        "archivo_original": folios_vistos[folio]
                    })
                    continue # <--- AQUÍ ESTÁ EL TRUCO: Salta este archivo y sigue con el siguiente
                else:
                    folios_vistos[folio] = uploaded_file.name

            # 2. BUSCAR PERCEPCIONES (Basado en tu comprobante 27601432)
            perc_match = re.search(r'PERCEPCIONES.*?\n.*?\$?\s*([\d,]+\.\d{2})', texto_completo)
            percepciones = limpiar_numero(perc_match.group(1)) if perc_match else 0.0

            # 3. BUSCAR ISR (Código 01)
            isr_match = re.search(r'IMPUESTO SOBRE LA RENTA.*?([\d,]+\.\d{2})', texto_completo, re.IGNORECASE)
            isr = limpiar_numero(isr_match.group(1)) if isr_match else 0.0

            # 4. DETECTAR AGUINALDO
            es_aguinaldo = "aguinaldo" in texto_completo.lower() or "gratificacion anual" in texto_completo.lower()

            datos_recibos.append({
                "Archivo": uploaded_file.name,
                "Folio": folio,
                "Percepciones": percepciones,
                "ISR": isr,
                "Tipo": "Aguinaldo" if es_aguinaldo else "Ordinaria"
            })

    # --- MOSTRAR ALERTAS DE DUPLICADOS ---
    if duplicados_encontrados:
        st.error("🚫 SE DETECTARON ARCHIVOS REPETIDOS")
        for d in duplicados_encontrados:
            st.warning(f"El folio **{d['folio']}** del archivo `{d['archivo_actual']}` ya existe en `{d['archivo_original']}`. **Fue ignorado para los cálculos.**")

    if datos_recibos:
        df = pd.DataFrame(datos_recibos)
        
        # --- CÁLCULOS ---
        # 1. Sin aguinaldo
        df_regular = df[df['Tipo'] == "Ordinaria"]
        # 2. Con aguinaldo
        df_aguinaldo = df[df['Tipo'] == "Aguinaldo"]
        
        # --- INTERFAZ DE RESULTADOS ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.info("🏠 **Nómina Regular**")
            st.metric("Percepciones", f"${df_regular['Percepciones'].sum():,.2f}")
            st.metric("ISR", f"${df_regular['ISR'].sum():,.2f}")

        with c2:
            st.info("🎁 **Solo Aguinaldos**")
            st.metric("Percepciones", f"${df_aguinaldo['Percepciones'].sum():,.2f}")
            st.metric("ISR", f"${df_aguinaldo['ISR'].sum():,.2f}")

        with c3:
            st.success("🌎 **Totales Globales**")
            t_perc = df['Percepciones'].sum()
            t_isr = df['ISR'].sum()
            st.metric("Total Percepciones", f"${t_perc:,.2f}")
            st.metric("Total ISR", f"${t_isr:,.2f}")

        st.divider()
        st.subheader(f"💰 Resultado Final (Resta): ${t_perc - t_isr:,.2f}")
        
        # Tabla detallada
        with st.expander("Ver detalle de archivos procesados"):
            st.table(df)
