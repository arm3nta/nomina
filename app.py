import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

# Configuración de la página
st.set_page_config(page_title="Analizador de Nómina", layout="centered")

st.title("📊 Analizador de Recibos de Nómina")
st.markdown("Sube tus archivos PDF para obtener un resumen detallado.")

def limpiar_numero(texto):
    if not texto: return 0.0
    try:
        limpio = re.sub(r'[^\d.]', '', str(texto))
        return float(limpio)
    except:
        return 0.0

# --- LÓGICA DE PROCESAMIENTO ---
uploaded_files = st.file_uploader("Elige tus recibos de nómina (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    datos_recibos = []
    folios_vistos = set()
    alertas = []

    for uploaded_file in uploaded_files:
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text() or ""
            
            # Busqueda de Folio
            folio_match = re.search(r'No\.\s*DE\s*COMPROBANTE\s*[\n\r]*\s*(\d+)', texto_completo, re.IGNORECASE)
            folio = folio_match.group(1) if folio_match else "Desconocido"

            # Busqueda de Percepciones
            perc_match = re.search(r'PERCEPCIONES.*?\n.*?\$?\s*([\d,]+\.\d{2})', texto_completo)
            percepciones = limpiar_numero(perc_match.group(1)) if perc_match else 0.0

            # Busqueda de ISR
            isr_match = re.search(r'IMPUESTO SOBRE LA RENTA.*?([\d,]+\.\d{2})', texto_completo, re.IGNORECASE)
            isr = limpiar_numero(isr_match.group(1)) if isr_match else 0.0

            # Detectar Aguinaldo
            es_aguinaldo = "aguinaldo" in texto_completo.lower() or "gratificacion anual" in texto_completo.lower()

            if folio != "Desconocido":
                if folio in folios_vistos:
                    alertas.append(f"⚠️ El folio **{folio}** está repetido y no se sumó.")
                    continue
                folios_vistos.add(folio)

            datos_recibos.append({
                "Archivo": uploaded_file.name,
                "Folio": folio,
                "Percepciones": percepciones,
                "ISR": isr,
                "Es_Aguinaldo": es_aguinaldo
            })

    if datos_recibos:
        df = pd.DataFrame(datos_recibos)
        
        # Cálculos
        sin_aguinaldo = df[df['Es_Aguinaldo'] == False]
        con_aguinaldo = df[df['Es_Aguinaldo'] == True]

        # Interfaz de la Web-App
        if alertas:
            for a in alertas: st.warning(a)

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏠 Nómina Regular")
            st.metric("Total Percepciones", f"${sin_aguinaldo['Percepciones'].sum():,.2f}")
            st.metric("Total ISR", f"${sin_aguinaldo['ISR'].sum():,.2f}")

        with col2:
            st.subheader("🎁 Aguinaldos")
            st.metric("Total Percepciones", f"${con_aguinaldo['Percepciones'].sum():,.2f}")
            st.metric("Total ISR", f"${con_aguinaldo['ISR'].sum():,.2f}")

        st.divider()
        st.subheader("🌎 Resumen Global")
        t_perc = df['Percepciones'].sum()
        t_isr = df['ISR'].sum()
        
        st.write(f"**Gran Total Percepciones:** ${t_perc:,.2f}")
        st.write(f"**Gran Total ISR:** ${t_isr:,.2f}")
        st.success(f"### 💰 Resta Final: ${t_perc - t_isr:,.2f}")
        
        # Botón para descargar a Excel
        st.download_button("Descargar tabla en Excel", df.to_csv(index=False), "nomina.csv", "text/csv")