import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Indicadores y seguimiento de calidad de venta -Autociel", layout="wide")

URL_MARCA = "https://docs.google.com/spreadsheets/d/1p2xd-SNGEDZ_sT8P4xAjdLQEZ5uuEx57c3NhGOaBNTo/edit#gid=567460007"
URL_INTERNA = "https://docs.google.com/spreadsheets/d/1p2xd-SNGEDZ_sT8P4xAjdLQEZ5uuEx57c3NhGOaBNTo/edit#gid=1131519764"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1p2xd-SNGEDZ_sT8P4xAjdLQEZ5uuEx57c3NhGOaBNTo/edit#gid=863634651"
URL_BASE = "https://docs.google.com/spreadsheets/d/1p2xd-SNGEDZ_sT8P4xAjdLQEZ5uuEx57c3NhGOaBNTo/edit#gid=0"
URL_DUV = "https://docs.google.com/spreadsheets/d/1-ziHRIEWQZUxFUBGqoweX6PvY6sDgoaXGcueSUd9370/edit#gid=1482583153"

# --- NLP BASADO EN REGLAS PARA COMENTARIOS ---
def categorizar_comentario(texto):
    if pd.isna(texto) or str(texto).strip() == "" or str(texto).upper() == "NAN":
        return "SIN COMENTARIO"
    t = str(texto).lower()
    
    if any(w in t for w in ["vendedor", "atencion", "amable", "cordial", "asesor", "excelente", "trato", "predisposicion"]):
        return "ATENCIÓN Y ASESORAMIENTO"
    elif any(w in t for w in ["entrega", "entregaron", "plazo", "retirar", "dia", "fecha", "demora", "tarde"]):
        return "PROCESO DE ENTREGA / TIEMPOS"
    elif any(w in t for w in ["precio", "financiacion", "cuota", "pago", "banco", "tasa", "caro", "descuento"]):
        return "PRECIO Y FINANCIACIÓN"
    elif any(w in t for w in ["limpieza", "sucio", "lavado", "raya", "detalle", "impecable", "presentacion"]):
        return "ESTADO Y LIMPIEZA DEL VEHÍCULO"
    elif any(w in t for w in ["papeleo", "gestor", "patente", "tramite", "firma", "documentacion", "titulo"]):
        return "GESTORÍA Y ADMINISTRACIÓN"
    elif any(w in t for w in ["test drive", "manejo", "probar", "prueba", "testdrive"]):
        return "TEST DRIVE"
    
    return "OTROS / GENERAL"

# --- FUNCIONES DE DATOS Y CÁLCULOS ---
def limpiar_comas_a_numerico(serie):
    """Convierte strings con comas a números flotantes legibles por Python"""
    if serie is None or serie.empty:
        return pd.Series(dtype=float)
    return pd.to_numeric(serie.astype(str).str.replace(',', '.'), errors='coerce')

@st.cache_data(ttl=600)
def load_data(url, tipo_base):
    try:
        csv_url = url.replace("/edit#gid=", "/export?format=csv&gid=").replace("/edit?gid=", "/export?format=csv&gid=").replace("#gid=", "&gid=")
        df = pd.read_csv(csv_url)
        
        # --- NORMALIZACIÓN ENCUESTAS DE MARCA ---
        if tipo_base == "Encuestas de Marca":
            df["Fecha de ultimo contacto"] = pd.to_datetime(df["Fecha de ultimo contacto"], dayfirst=True, errors='coerce')
            if "Vendedor" in df.columns:
                df["Vendedor"] = df["Vendedor"].astype(str).str.strip().str.upper()
            
            if "Q13 - Satisfacción Entrega General" not in df.columns:
                col_q13 = next((c for c in df.columns if 'q13' in c.lower() or 'entrega general' in c.lower()), None)
                if col_q13: df["Q13 - Satisfacción Entrega General"] = df[col_q13]
            if "Q3 - Verbalización" in df.columns:
                df["Categoria_Comentario"] = df["Q3 - Verbalización"].apply(categorizar_comentario)
            else:
                df["Categoria_Comentario"] = "SIN COMENTARIO"
                
        # --- NORMALIZACIÓN ENCUESTAS INTERNAS ---
        elif tipo_base == "Encuestas Internas":
            col_fecha = "Fecha de último contacto" if "Fecha de último contacto" in df.columns else "Fecha de ultimo contacto"
            df["Fecha de ultimo contacto"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
            df["MARCA"] = df["MARCA"]
            df["Canal de Venta"] = df["CANAL DE VENTA"]
            
            if "VENDEDOR" in df.columns:
                df["Vendedor"] = df["VENDEDOR"].astype(str).str.strip().str.upper()
            else:
                df["Vendedor"] = "SIN VENDEDOR"
            
            if "Cliente" in df.columns:
                df["Nombre de cliente"] = df["Cliente"]
            elif "Nombre de cliente" not in df.columns:
                df["Nombre de cliente"] = "Cliente Autociel"
            
            if "COMENTARIO DEL CLIENTE" in df.columns:
                df["Categoria_Comentario"] = df["COMENTARIO DEL CLIENTE"].apply(categorizar_comentario)
            else:
                df["Categoria_Comentario"] = "SIN COMENTARIO"
                
        # --- NORMALIZACIÓN GESTIÓN DE QUEJAS ---
        elif tipo_base == "Gestión de Quejas":
            col_fecha = next((c for c in df.columns if 'fech' in c.lower()), "Fecha de Gestión")
            col_categorizacion = next((c for c in df.columns if 'categorizac' in c.lower() or 'categorí' in c.lower()), "Categorizacion del Reclamo")
            col_sector = next((c for c in df.columns if 'sector' in c.lower() or 'afect' in c.lower()), "Sector Afectado")
            
            df["Fecha_Filtro"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
            
            df = df[df["Fecha_Filtro"].dt.year >= 2025].copy()
            df["Anio"] = df["Fecha_Filtro"].dt.year
            df["Mes_Num"] = df["Fecha_Filtro"].dt.month
            
            df["Categorizacion del Reclamo"] = df[col_categorizacion].astype(str).str.strip().str.upper() if col_categorizacion in df.columns else "SIN CATEGORIZAR"
            df["Sector Afectado"] = df[col_sector].astype(str).str.strip().str.upper() if col_sector in df.columns else "SIN SECTOR"
            
            df["tipo de queja"] = df[next((c for c in df.columns if 'tipo' in c.lower()), df.columns[1])].astype(str).str.strip().str.upper()
            df["marca"] = df[next((c for c in df.columns if 'marc' in c.lower()), df.columns[2])].astype(str).str.strip().str.upper()
            df["cliente"] = df[next((c for c in df.columns if 'client' in c.lower() or 'nombre' in c.lower()), df.columns[3])].astype(str).str.strip().str.upper()
            df["vendedor"] = df[next((c for c in df.columns if 'vend' in c.lower() or 'ases' in c.lower()), df.columns[4])].astype(str).str.strip().str.upper()
            df["canal de venta"] = df[next((c for c in df.columns if 'canal' in c.lower()), df.columns[5])].astype(str).str.strip().str.upper()
            df["comentario"] = df[next((c for c in df.columns if 'coment' in c.lower() or 'descrip' in c.lower() or 'detalle' in c.lower() or 'motivo' in c.lower()), df.columns[6])].astype(str).str.strip()
            df["Reporte tratado por"] = df[next((c for c in df.columns if 'report' in c.lower() or 'tratad' in c.lower() or 'estad' in c.lower()), df.columns[7])].astype(str).str.strip().str.upper()
            
        # --- NUEVA FUENTE: PRIMA DE CALIDAD ---
        elif tipo_base == "Prima de Calidad":
            df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            col_fecha = next((c for c in df.columns if 'fecha de ultimo contacto' in c.lower()), None)
            
            if col_fecha:
                df["Fecha de ultimo contacto"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
                df["Anio"] = df["Fecha de ultimo contacto"].dt.year
            else:
                df["Anio"] = pd.NA
                
            col_marca = next((c for c in df.columns if 'marca' in c.lower() or 'mar ca' in c.lower()), None)
            if col_marca:
                mapeo_marcas = {"AP": "PEUGEOT", "AC": "CITROEN"}
                df["Marca_Normalizada"] = df[col_marca].astype(str).str.strip().str.upper().map(mapeo_marcas).fillna(df[col_marca].astype(str).str.strip().str.upper())
            else:
                df["Marca_Normalizada"] = "SIN MARCA"

        # --- NORMALIZACIÓN BASE DE CORREOS ---
        elif tipo_base == "Base de Correos":
            col_fecha = next((c for c in df.columns if 'fecha de importación' in c.lower() or 'importacion' in c.lower()), None)
            if col_fecha:
                df["Fecha de Importación"] = pd.to_datetime(df[col_fecha], dayfirst=True, errors='coerce')
                df["Anio"] = df["Fecha de Importación"].dt.year
                df["Mes_Num"] = df["Fecha de Importación"].dt.month
            else:
                df["Anio"] = pd.NA
                df["Mes_Num"] = pd.NA
            
            col_marca = next((c for c in df.columns if 'marca' in c.lower()), None)
            if col_marca:
                df["Marca_Normalizada"] = df[col_marca].astype(str).str.strip().str.upper()
            else:
                df["Marca_Normalizada"] = "SIN MARCA"
                
        # --- NORMALIZACIÓN ANALISIS DUV WG ---
        elif tipo_base == "Análisis DUV":
            df.columns = df.columns.astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
            
            col_pat = next((c for c in df.columns if 'fecha' in c.lower() and 'patenta' in c.lower()), None)
            col_ho = next((c for c in df.columns if 'h.o' in c.lower() or 'hand over' in c.lower()), None)
            col_marca = next((c for c in df.columns if 'marca' in c.lower()), None)
            
            # --- EXTRACCIÓN DE PRECIO FACTURADO PARA MATEMÁTICA ---
            col_precio = next((c for c in df.columns if 'precio facturad' in c.lower() or 'precio' in c.lower()), None)
            if col_precio:
                precio_str = df[col_precio].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
                precio_str = precio_str.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                df["Precio Facturado"] = pd.to_numeric(precio_str, errors='coerce').fillna(0.0)
            else:
                df["Precio Facturado"] = 0.0
            
            if col_pat and col_ho:
                df["Fecha de Patentamiento"] = pd.to_datetime(df[col_pat].astype(str).str.strip(), dayfirst=True, errors='coerce')
                df["FECHA DE H.O."] = pd.to_datetime(df[col_ho].astype(str).str.strip(), dayfirst=True, errors='coerce')
                df["Anio_Patentamiento"] = df["Fecha de Patentamiento"].dt.year
                df["Mes_Patentamiento"] = df["Fecha de Patentamiento"].dt.month
            else:
                df["Anio_Patentamiento"] = pd.NA
                df["Mes_Patentamiento"] = pd.NA
            
            if col_marca and col_marca in df.columns:
                marca_str = df[col_marca].astype(str).str.strip().str.upper()
                df["Marca_Normalizada"] = np.where(marca_str.str.contains("PEUGEOT", na=False), "PEUGEOT",
                                          np.where(marca_str.str.contains("CITRO", na=False), "CITROEN", "OTRA"))
            else:
                df["Marca_Normalizada"] = "SIN MARCA"
            
        return df
    except Exception as e:
        st.error(f"Error al cargar datos ({tipo_base}): {e}")
        return pd.DataFrame()

def calcular_nps_detallado(serie):
    serie_limpia = limpiar_comas_a_numerico(serie).dropna()
    total = len(serie_limpia)
    if total == 0: return 0, 0, 0, 0, 0
    promotores = (serie_limpia >= 9).sum()
    neutros = ((serie_limpia >= 7) & (serie_limpia <= 8)).sum()
    detractores = (serie_limpia <= 6).sum()
    nps = ((promotores - detractores) / total) * 100
    return nps, promotores, neutros, detractores, total

def calcular_csi_directo_porcentaje(serie):
    serie_limpia = limpiar_comas_a_numerico(serie).dropna()
    total = len(serie_limpia)
    if total == 0: return 0.0, 0
    average_val = serie_limpia.mean()
    promedio_porcentaje = average_val * 10 if average_val <= 10 else average_val
    return promedio_porcentaje, total

def calcular_faltante_94(promotores, detractores, total):
    if total == 0: return "Sin datos"
    nps_actual = ((promotores - detractores) / total) * 100
    if nps_actual >= 94: return "✅ Objetivo"
    x = (0.94 * total + detractores - promotores) / (1 - 0.94)
    return f"🚨 Faltan {math.ceil(x)}"

def get_bar_color(val):
    if val >= 94: return '#2E7D32'
    if val >= 90: return '#FBC02D'
    return '#D32F2F'

def crear_gauge_moderno(valor, titulo, objetivo=94.0):
    color_viva = get_bar_color(valor)
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        title = {'text': f"<b>{titulo}</b>", 'font': {'size': 12, 'color': '#555555'}},
        number = {'suffix': "%", 'font': {'size': 23, 'color': '#1E1E1E', 'family': 'Arial'}, 'valueformat': '.1f'},
        gauge = {
            'axis': {
                'range': [-100, 100], 
                'visible': True, 
                'showticklabels': False, 
                'tickvals': [-100, -50, 0, 50, 100],
                'tickwidth': 2,
                'tickcolor': '#555555',
                'ticklen': 5
            }, 
            'bar': {'color': color_viva, 'thickness': 0.25},
            'bgcolor': "#E6E9EC"
        }
    ))
    fig.update_layout(height=165, margin=dict(l=15, r=15, t=35, b=5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def crear_grafico_torta(df, columna_o_keyword, titulo):
    columna_real = None
    for col in df.columns:
        if columna_o_keyword.lower() in col.lower():
            columna_real = col
            break
            
    if not columna_real: 
        fig = go.Figure()
        fig.update_layout(title=titulo, annotations=[dict(text="Columna no encontrada", showarrow=False, font=dict(size=12))])
        return fig
    
    df_torta = df[[columna_real]].dropna().copy()
    df_torta[columna_real] = df_torta[columna_real].astype(str).str.strip().str.upper()
    
    if df_torta.empty:
        fig = go.Figure()
        fig.update_layout(title=titulo, annotations=[dict(text="Sin respuestas válidas", showarrow=False, font=dict(size=13))])
        return fig
        
    conteo = df_torta[columna_real].value_counts().reset_index()
    conteo.columns = ['Respuesta', 'Cantidad']
    
    conteo['Respuesta'] = conteo['Respuesta'].replace({'SÍ': 'SI', 'SÍ, SE OFRECIÓ': 'SI', 'CONTACTADO': 'SI'})
    conteo['Respuesta'] = conteo['Respuesta'].replace({'NO CONTACTADO': 'NO'})
    
    total_respuestas = conteo['Cantidad'].sum()
    
    if 'SI' in conteo['Respuesta'].values:
        cant_si = conteo[conteo['Respuesta'] == 'SI']['Cantidad'].sum()
        pct_si = (cant_si / total_respuestas) * 100 if total_respuestas > 0 else 0.0
        label_centro = "Sí"
    else:
        cant_si = conteo.iloc[0]['Cantidad']
        pct_si = (cant_si / total_respuestas) * 100 if total_respuestas > 0 else 0.0
        label_centro = str(conteo.iloc[0]['Respuesta']).title()
    
    colores_map = {'SI': '#2E7D32', 'NO': '#D32F2F'}
    
    fig = px.pie(
        conteo, 
        values='Cantidad', 
        names='Respuesta', 
        title=titulo, 
        hole=0.6,
        color='Respuesta',
        color_discrete_map=colores_map if 'SI' in conteo['Respuesta'].values else None,
        color_discrete_sequence=px.colors.qualitative.Pastel if 'SI' not in conteo['Respuesta'].values else None
    )
    fig.update_traces(textinfo='percent+label', textposition='outside', textfont=dict(size=9))
    
    fig.update_layout(
        height=165, 
        margin=dict(l=10, r=10, t=35, b=5), 
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(
            text=f"<b>{pct_si:.1f}%</b><br><span style='font-size:9px;color:#666;font-weight:normal;'>{label_centro}</span>", 
            showarrow=False, 
            font=dict(size=16, color='#2E7D32' if label_centro == "Sí" else '#007bff')
        )]
    )
    return fig

def crear_linea_reclamos_porcentaje(df, columnas_evaluar, titulo, meses_n, key_prefix):
    df_calc = df.copy()
    if df_calc.empty:
        fig = go.Figure()
        fig.update_layout(title=titulo, annotations=[dict(text="Sin Datos", showarrow=False)])
        return fig
        
    def check_is_reclamo(row):
        for col in columnas_evaluar:
            if col in df_calc.columns:
                val = pd.to_numeric(limpiar_comas_a_numerico(pd.Series(row[col])).iloc[0], errors='coerce')
                if not pd.isna(val) and val <= 8:
                    return 1
        return 0
        
    df_calc["Es_Reclamo"] = df_calc.apply(check_is_reclamo, axis=1)
    
    resumen_mes = []
    for m_num in sorted(df_calc["Mes_Num"].dropna().unique().astype(int)):
        df_mes = df_calc[df_calc["Mes_Num"] == m_num]
        total_encuestas = len(df_mes)
        if total_encuestas == 0: continue
        
        cant_reclamos = int(df_mes["Es_Reclamo"].sum())
        cant_conformes = total_encuestas - cant_reclamos
        pct_reclamos = (cant_reclamos / total_encuestas) * 100
        
        resumen_mes.append({
            "Mes_Num": m_num,
            "Mes_Nombre": meses_n[m_num],
            "Porcentaje Reclamos": round(pct_reclamos, 1),
            "Cantidad Reclamos": cant_reclamos,
            "Clientes Conformes": cant_conformes
        })
        
    if not resumen_mes:
        fig = go.Figure()
        fig.update_layout(title=titulo, annotations=[dict(text="Muestra insuficiente en los meses", showarrow=False)])
        return fig
        
    df_plot = pd.DataFrame(resumen_mes)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["Mes_Nombre"],
        y=df_plot["Porcentaje Reclamos"],
        mode='lines+markers+text',
        text=df_plot["Porcentaje Reclamos"].astype(str) + "%",
        textposition="top center",
        line=dict(color='#D32F2F', width=3),
        marker=dict(size=8, symbol='circle'),
        customdata=df_plot[["Cantidad Reclamos", "Clientes Conformes"]],
        hovertemplate="<b>📅 Mes: %{x}</b><br>" +
                      "📈 Porcentaje Reclamos: %{y:.1f}%<br>" +
                      "<span style='color:red;'>🚨 Cantidad Reclamos: %{customdata[0]}</span><br>" +
                      "<span style='color:green;'>✅ Clientes Conformes: %{customdata[1]}</span><br>" +
                      "<extra></extra>"
    ))
    
    fig.update_layout(
        title=titulo,
        xaxis_title="Meses",
        yaxis_title="% Reclamos (Notas <= 8)",
        yaxis=dict(range=[-5, 105]),
        height=280,
        margin=dict(l=30, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- LÓGICA PRINCIPAL ---
try:
    if 'filtro_val_m' not in st.session_state: st.session_state.filtro_val_m = "Todos"
    if 'filtro_col_m' not in st.session_state: st.session_state.filtro_col_m = "Cat_Filtro_Dinamica"
    if 'filtro_val_i' not in st.session_state: st.session_state.filtro_val_i = "Todos"
    if 'filtro_col_i' not in st.session_state: st.session_state.filtro_col_i = "Cat_Filtro_Dinamica"
    
    if 'filtro_cat_q' not in st.session_state: st.session_state.filtro_cat_q = "Todas"
    if 'filtro_sec_q' not in st.session_state: st.session_state.filtro_sec_q = "Todos"
    
    if 'feedback_cat_sel' not in st.session_state: st.session_state.feedback_cat_sel = "TODAS"

    # --- CARGA SIMULTÁNEA DE BASES ---
    df_m = load_data(URL_MARCA, "Encuestas de Marca")
    df_i = load_data(URL_INTERNA, "Encuestas Internas")
    df_q = load_data(URL_QUEJAS, "Gestión de Quejas")
    df_roar = load_data(URL_MARCA, "Prima de Calidad")
    df_base = load_data(URL_BASE, "Base de Correos")
    df_duv = load_data(URL_DUV, "Análisis DUV")
    
    if not df_m.empty and not df_i.empty:
        
        # MAPEO DE COLUMNAS
        MAPA_M = {
            'q1': 'Q1 - Satisfacción general', 'q2': 'Q2 - Recomendación - Concesionario', 'q3': 'Q3 - Verbalización',
            'q4': 'Q4 - Cortesía y amabilidad', 'q5': 'Q5 - Competencia Vendedor', 'q6': 'Q6 - Ofrecimiento Test Drive',
            'q8': 'Q8 - Satisfacción información entre compra y entrega', 'q11': 'Q11 - Satisfacción Momento de la entrega',
            'q13': 'Q13 - Satisfacción Entrega General',
            'q14': 'Q14 - Contactado', 'q15': 'Q15 - Satisfacción con el Contacto',
            'lbl_q1': 'Q1 - SATISFACCIÓN (NPS)', 'lbl_q2': 'Q2 - RECOMENDACIÓN (NPS)'
        }
        
        MAPA_I = {
            'q1': 'CSI', 'q2': '1. Basándose en su experiencia de compra, ¿Recomendaría el Concesionario a Familiares y amigos?',
            'q3': 'COMENTARIO DEL CLIENTE', 'q4': '2. ¿Cómo califica la cortesía y amabilidad del Vendedor / Asesor Comercial?',
            'q5': None, 'q6': '3. ¿Le han ofrecido una prueba de manejo?',
            'q8': '4. ¿Cómo califica la información facilitada entre la compra y la entrega de su vehículo nuevo? (Comunicación y explicación de tramites administrativos)',
            'q11': '5. ¿Cómo califica la presentación de su 0KM al momento de la entrega? (explicaciones de las características, la limpieza y la presentación con el vehículo, entre otros aspectos.)',
            'q14': 'contacto del concesionario posterior', 'q15': '7. ¿Cuán satisfecho se encuentra con el contacto posterior realizado por el concesionario?',
            'lbl_q1': 'CSI GENERAL (PROMEDIO %)', 'lbl_q2': '1. RECOMENDACIÓN (NPS)'
        }

        # Asegurar conversión explícita a Datetime e inyección de Año/Mes base
        df_m["Fecha de ultimo contacto"] = pd.to_datetime(df_m["Fecha de ultimo contacto"], errors='coerce')
        df_i["Fecha de ultimo contacto"] = pd.to_datetime(df_i["Fecha de ultimo contacto"], errors='coerce')
        
        df_m['Anio'] = df_m["Fecha de ultimo contacto"].dt.year
        df_m['Mes_Num'] = df_m["Fecha de ultimo contacto"].dt.month
        df_i['Anio'] = df_i["Fecha de ultimo contacto"].dt.year
        df_i['Mes_Num'] = df_i["Fecha de ultimo contacto"].dt.month

        # Categorizaciones estructurales para clics basadas en NPS
        def generar_categorias(val):
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return "Sin Datos"
            if v >= 9: return "Promotor"
            if v >= 7: return "Neutro"
            return "Detractor"

        df_m['Cat_Filtro_Dinamica'] = df_m[MAPA_M['q1']].apply(generar_categorias)
        df_m['Cat_Filtro_Q2'] = df_m[MAPA_M['q2']].apply(generar_categorias)
        
        df_i['Cat_Filtro_Dinamica'] = limpiar_comas_a_numerico(df_i[MAPA_I['q1']]).apply(generar_categorias)
        df_i['Cat_Filtro_Q2'] = limpiar_comas_a_numerico(df_i[MAPA_I['q2']]).apply(generar_categorias)

        st.title("📊 Indicadores y seguimiento de calidad de venta -Autociel")
        
        # --- AQUÍ DEFINIMOS LAS 5 PESTAÑAS (FUSIONANDO FEEDBACK Y QUEJAS) ---
        tab_global, tab_unificada, tab_individual, tab_feedback, tab_prima = st.tabs([
            "🏠 Monitor Global Comparativo", 
            "👥 Tabla Unificada de Asesores", 
            "👤 Ficha Individual por Asesor",
            "💬 Análisis de Voz y Quejas",
            "🏆 Prima de Calidad"
        ])

        # ==========================================================
        # TAB 1: MONITOR GLOBAL
        # ==========================================================
        with tab_global:
            with st.expander("⚙️ Filtros del Monitor Global", expanded=True):
                col_fg1, col_fg2, col_fg3 = st.columns(3)
                with col_fg1:
                    anios_comb_g = sorted(list(set(df_m['Anio'].dropna().unique().astype(int)) | set(df_i['Anio'].dropna().unique().astype(int))), reverse=True)
                    anio_sel = st.selectbox("Año:", options=anios_comb_g if anios_comb_g else [2026], key="g_anio")
                with col_fg2:
                    meses_n = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6: "Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
                    set_meses_g = set(df_m[df_m['Anio'] == anio_sel]['Mes_Num'].unique()) | set(df_i[df_i['Anio'] == anio_sel]['Mes_Num'].unique())
                    meses_disp_nums_g = sorted(list(set_meses_g))
                    meses_disp_nombres_g = [meses_n[m] for m in meses_disp_nums_g] if meses_disp_nums_g else ["Mayo"]
                    meses_sel_nombres = st.multiselect("Seleccione Mes(es):", options=meses_disp_nombres_g, default=meses_disp_nombres_g[-1:], key="g_meses")
                    meses_sel_nums = [k for k, v in meses_n.items() if v in meses_sel_nombres]
                with col_fg3:
                    marcas_disp_g = sorted(list(set(df_m["MARCA"].dropna().unique()) | set(df_i["MARCA"].dropna().unique())))
                    marcas = st.multiselect("MARCA:", options=marcas_disp_g, default=marcas_disp_g, key="g_marcas")

                canales_m_g = set(df_m[df_m["MARCA"].isin(marcas)]["Canal de Venta"].dropna().unique())
                canales_i_g = set(df_i[df_i["MARCA"].isin(marcas)]["Canal de Venta"].dropna().unique())
                canales_disp_g = sorted(list(canales_m_g | canales_i_g))
                canales = st.multiselect("Canal de Venta:", options=canales_disp_g, default=canales_disp_g, key="g_canales")

            df_m_time = df_m[(df_m["Anio"] == anio_sel) & (df_m["Mes_Num"].isin(meses_sel_nums))]
            df_i_time = df_i[(df_i["Anio"] == anio_sel) & (df_i["Mes_Num"].isin(meses_sel_nums))]

            df_m_base = df_m_time[(df_m_time["MARCA"].isin(marcas)) & (df_m_time["Canal de Venta"].isin(canales))]
            df_i_base = df_i_time[(df_i_time["MARCA"].isin(marcas)) & (df_i_time["Canal de Venta"].isin(canales))]
        # ==========================================================
        # DESPLEGABLE: COMPARACIÓN MENSUAL NPS INTERNO VS MARCA
        # ==========================================================
            with st.expander("📊 Ver anualmente el NPS (Evolución Mensual): Interno vs Marca", expanded=False):
                anios_comb_g_arr = sorted(list(set(df_m['Anio'].dropna().unique().astype(int)) | set(df_i['Anio'].dropna().unique().astype(int))), reverse=True)
                anio_actual_sel = anio_sel if 'anio_sel' in locals() else (anios_comb_g_arr[0] if anios_comb_g_arr else 2026)
                marcas_actuales_sel = marcas if 'marcas' in locals() else []

                df_m_anual_global = df_m[(df_m["Anio"] == anio_actual_sel) & (df_m["MARCA"].isin(marcas_actuales_sel))]
                df_i_anual_global = df_i[(df_i["Anio"] == anio_actual_sel) & (df_i["MARCA"].isin(marcas_actuales_sel))]
                
                resumen_comparativo = []
                meses_nombres_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
                
                meses_disponibles_calc = sorted(list(set(df_m_anual_global["Mes_Num"].dropna().unique()) | set(df_i_anual_global["Mes_Num"].dropna().unique())))
                
                for m_num in meses_disponibles_calc:
                    m_num_int = int(m_num)
                    nombre_mes = meses_nombres_dict.get(m_num_int, str(m_num_int))
                    
                    sub_m_mes = df_m_anual_global[df_m_anual_global["Mes_Num"] == m_num_int]
                    nps_m_val, _, _, _, _ = calcular_nps_detallado(sub_m_mes[MAPA_M['q2']]) if not sub_m_mes.empty else (0.0, 0, 0, 0, 0)
                    
                    sub_i_mes = df_i_anual_global[df_i_anual_global["Mes_Num"] == m_num_int]
                    nps_i_val, _, _, _, _ = calcular_nps_detallado(sub_i_mes[MAPA_I['q2']]) if not sub_i_mes.empty else (0.0, 0, 0, 0, 0)
                    
                    if not sub_m_mes.empty:
                        resumen_comparativo.append({"Mes": nombre_mes, "Mes_Num": m_num_int, "NPS": round(nps_m_val, 1), "Fuente": "NPS Oficial Marca"})
                    if not sub_i_mes.empty:
                        resumen_comparativo.append({"Mes": nombre_mes, "Mes_Num": m_num_int, "NPS": round(nps_i_val, 1), "Fuente": "NPS Encuesta Interna"})
                
                if resumen_comparativo:
                    df_comp_plot = pd.DataFrame(resumen_comparativo).sort_values("Mes_Num")
                    fig_comparativa = px.bar(
                        df_comp_plot, x="Mes", y="NPS", color="Fuente", barmode="group",
                        text=df_comp_plot["NPS"].astype(str) + "%",
                        color_discrete_map={"NPS Oficial Marca": "#1976D2", "NPS Encuesta Interna": "#2E7D32"}
                    )
                    fig_comparativa.add_hline(y=94.0, line_dash="dash", line_color="#D32F2F", annotation_text="Objetivo Calidad (94%)", annotation_position="top right")
                    fig_comparativa.update_traces(textposition='outside', textfont=dict(size=10))
                    fig_comparativa.update_layout(
                        height=350, margin=dict(l=20, r=20, t=30, b=20),
                        yaxis=dict(range=[-10, 110], title="NPS (%)"), xaxis=dict(title="Meses"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_comparativa, use_container_width=True, key="chart_comparativo_interno_marca_anual")
                else:
                    st.info("No hay suficientes datos registrados para generar la comparativa anual con el año y marcas seleccionadas.")

            st.header(f"Resultados en Paralelo: {', '.join(meses_sel_nombres)}")
            sc_marca, sc_interna = st.columns([1, 1])
            
            with sc_marca:
                st.markdown("### 🏢 Datos de Origen: Encuestas de Marca")
                val_m_q1, p_m_q1, n_m_q1, d_m_q1, t_m_q1 = calcular_nps_detallado(df_m_base[MAPA_M['q1']])
                nps_m_q2, p_m_q2, n_m_q2, d_m_q2, t_m_q2 = calcular_nps_detallado(df_m_base[MAPA_M['q2']])

                with st.container(border=True):
                    cm_q1, cm_q2, cm_tot = st.columns([2.2, 2.2, 0.8])
                    with cm_q1:
                        st.plotly_chart(crear_gauge_moderno(val_m_q1, MAPA_M['lbl_q1']), use_container_width=True, key="gauge_m_q1")
                        col_m1, col_m2, col_m3 = st.columns(3)
                        if col_m1.button(f"🟢 {p_m_q1} Prom", key="bm_q1_p"): st.session_state.filtro_col_m = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_m = "Promotor"; st.rerun()
                        if col_m2.button(f"🟡 {n_m_q1} Neu", key="bm_q1_n"): st.session_state.filtro_col_m = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_m = "Neutro"; st.rerun()
                        if col_m3.button(f"🔴 {d_m_q1} Det", key="bm_q1_d"): st.session_state.filtro_col_m = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_m = "Detractor"; st.rerun()
                    with cm_q2:
                        st.plotly_chart(crear_gauge_moderno(nps_m_q2, MAPA_M['lbl_q2']), use_container_width=True, key="gauge_m_q2")
                        col_m4, col_m5, col_m6 = st.columns(3)
                        if col_m4.button(f"🟢 {p_m_q2} Prom", key="bm_q2_p"): st.session_state.filtro_col_m = "Cat_Filtro_Q2"; st.session_state.filtro_val_m = "Promotor"; st.rerun()
                        if col_m5.button(f"🟡 {n_m_q2} Neu", key="bm_q2_n"): st.session_state.filtro_col_m = "Cat_Filtro_Q2"; st.session_state.filtro_val_m = "Neutro"; st.rerun()
                        if col_m6.button(f"🔴 {d_m_q2} Det", key="bm_q2_d"): st.session_state.filtro_col_m = "Cat_Filtro_Q2"; st.session_state.filtro_val_m = "Detractor"; st.rerun()
                    with cm_tot:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.metric("Muestra", t_m_q1)
                        if st.button("🔄 Todos", key="btn_clear_m"): st.session_state.filtro_val_m = "Todos"; st.rerun()

                df_m_sub = df_m_base.copy()
                if st.session_state.filtro_val_m != "Todos":
                    df_m_sub = df_m_sub[df_m_sub[st.session_state.filtro_col_m] == st.session_state.filtro_val_m]
                
                st.markdown(f"**Segmentación actual Marca:** `{st.session_state.filtro_val_m}`")
                stabs_m = st.tabs(["🤝 Gestión Comercial", "🚗 Test Drive", "💰 Finanzas", "📦 Procesos y Entrega", "📞 Contacto Posterior"])
                
                with stabs_m[0]:
                    v1, v2 = st.columns(2)
                    v1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub[MAPA_M['q4']])[0], "Q4 - Cortesía y Amabilidad (NPS)"), use_container_width=True, key="g_m_q4")
                    v2.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub[MAPA_M['q5']])[0], "Q5 - Competencia Vendedor (NPS)"), use_container_width=True, key="g_m_q5")
                with stabs_m[1]:
                    ct1, ct2 = st.columns(2)
                    ct1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub['Q7 - Satisfacción Test Drive'])[0], "Q7 - Sat. Test Drive (NPS)"), use_container_width=True, key="g_m_q7")
                    ct2.plotly_chart(crear_grafico_torta(df_m_sub, MAPA_M['q6'], 'Q6 - Ofrecimiento Test Drive'), use_container_width=True, key="p_m_q6")
                with stabs_m[2]:
                    cf1, cf2 = st.columns(2)
                    cf1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub['Q10 - Satisfacción Financiación utilizada'])[0], "Q10 - Sat. Financiación (NPS)"), use_container_width=True, key="g_m_q10")
                    cf2.plotly_chart(crear_grafico_torta(df_m_sub, 'Q9 - Financiación utilizada', 'Mix Ventas Financiadas'), use_container_width=True, key="p_m_q9")
                with stabs_m[3]:
                    _, col_macro, _ = st.columns([0.5, 3.0, 0.5])
                    with col_macro:
                        q13_val = calcular_nps_detallado(df_m_sub[MAPA_M['q13']])[0]
                        st.plotly_chart(crear_gauge_moderno(q13_val, "⭐ Q13 - Satisfacción Entrega General (NPS)"), use_container_width=True, key="g_m_q13")
                    st.markdown("<hr style='margin:5px 0px; border-color:#eee;'>", unsafe_allow_html=True)
                    ce1, ce2 = st.columns(2)
                    ce1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub[MAPA_M['q8']])[0], "Q8 - Info Pre-entrega (NPS)"), use_container_width=True, key="g_m_q8")
                    ce2.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub[MAPA_M['q11']])[0], "Q11 - Momento de la entrega (NPS)"), use_container_width=True, key="g_m_q11")
                with stabs_m[4]:
                    cp1, cp2 = st.columns(2)
                    cp1.plotly_chart(crear_grafico_torta(df_m_sub, MAPA_M['q14'], 'Q14 - Contactado Posterior'), use_container_width=True, key="p_m_q14")
                    cp2.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_m_sub[MAPA_M['q15']])[0], "Q15 - Sat. con el Contacto (NPS)"), use_container_width=True, key="g_m_q15")

                st.markdown("---")
                st.markdown("##### 💬 Verbalizaciones del Cliente (Marca)")
                df_m_v = df_m_sub[["Fecha de ultimo contacto", "Nombre de cliente", MAPA_M['q3'], "Vendedor"]].copy().sort_values("Fecha de ultimo contacto", ascending=False)
                df_m_v["Fecha de ultimo contacto"] = df_m_v["Fecha de ultimo contacto"].dt.strftime('%d/%m/%Y')
                df_m_v = df_m_v.rename(columns={MAPA_M['q3']: 'Comentario Textual'})
                
                busqueda_m = st.text_input("🔍 Buscar en comentarios de Marca:", "", key="search_m").strip()
                if busqueda_m:
                    df_m_v = df_m_v[df_m_v['Comentario Textual'].str.contains(busqueda_m, case=False, na=False)]
                st.dataframe(df_m_v, use_container_width=True, hide_index=True, height=180)

            with sc_interna:
                st.markdown("### 🎯 Datos de Origen: Encuestas Internas")
                val_i_q1, t_i_q1 = calcular_csi_directo_porcentaje(df_i_base[MAPA_I['q1']])
                serie_csi = limpiar_comas_a_numerico(df_i_base[MAPA_I['q1']]).dropna()
                p_i_q1 = (serie_csi >= 9.0).sum()
                n_i_q1 = ((serie_csi >= 7.0) & (serie_csi < 9.0)).sum()
                d_i_q1 = (serie_csi < 7.0).sum()
                nps_i_q2, p_i_q2, n_i_q2, d_i_q2, t_i_q2 = calcular_nps_detallado(df_i_base[MAPA_I['q2']])

                with st.container(border=True):
                    ci_q1, ci_q2, ci_tot = st.columns([2.2, 2.2, 0.8])
                    with ci_q1:
                        st.plotly_chart(crear_gauge_moderno(val_i_q1, MAPA_I['lbl_q1']), use_container_width=True, key="gauge_i_q1")
                        col_i1, col_i2, col_i3 = st.columns(3)
                        if col_i1.button(f"🟢 {p_i_q1} Prom", key="bi_q1_p"): st.session_state.filtro_col_i = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_i = "Promotor"; st.rerun()
                        if col_i2.button(f"🟡 {n_i_q1} Neu", key="bi_q1_n"): st.session_state.filtro_col_i = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_i = "Neutro"; st.rerun()
                        if col_i3.button(f"🔴 {d_i_q1} Det", key="bi_q1_d"): st.session_state.filtro_col_i = "Cat_Filtro_Dinamica"; st.session_state.filtro_val_i = "Detractor"; st.rerun()
                    with ci_q2:
                        st.plotly_chart(crear_gauge_moderno(nps_i_q2, MAPA_I['lbl_q2']), use_container_width=True, key="gauge_i_q2")
                        col_i4, col_i5, col_i6 = st.columns(3)
                        if col_i4.button(f"🟢 {p_i_q2} Prom", key="bi_q2_p"): st.session_state.filtro_col_i = "Cat_Filtro_Q2"; st.session_state.filtro_val_i = "Promotor"; st.rerun()
                        if col_i5.button(f"🟡 {n_i_q2} Neu", key="bi_q2_n"): st.session_state.filtro_col_i = "Cat_Filtro_Q2"; st.session_state.filtro_val_i = "Neutro"; st.rerun()
                        if col_i6.button(f"🔴 {d_i_q2} Det", key="bi_q2_d"): st.session_state.filtro_col_i = "Cat_Filtro_Q2"; st.session_state.filtro_val_i = "Detractor"; st.rerun()
                    with ci_tot:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.metric("Muestra", t_i_q1)
                        if st.button("🔄 Todos", key="btn_clear_i"): st.session_state.filtro_val_i = "Todos"; st.rerun()

                df_i_sub = df_i_base.copy()
                if st.session_state.filtro_val_i != "Todos":
                    df_i_sub = df_i_sub[df_i_sub[st.session_state.filtro_col_i] == st.session_state.filtro_val_i]
                
                st.markdown(f"**Segmentación actual Interna:** `{st.session_state.filtro_val_i}`")
                stabs_i = st.tabs(["🤝 Gestión Comercial", "🚗 Test Drive", "📦 Procesos y Entrega", "📞 Contacto posterior"])
                
                with stabs_i[0]:
                    vi1, _ = st.columns([2, 2])
                    vi1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_i_sub[MAPA_I['q4']])[0], "Preg. 2 - Cortesía y Amabilidad (NPS)"), use_container_width=True, key="g_i_p2")
                with stabs_i[1]:
                    v_test, _ = st.columns([2, 2])
                    v_test.plotly_chart(crear_grafico_torta(df_i_sub, MAPA_I['q6'], 'Preg. 3 - Ofrecimiento de Test Drive'), use_container_width=True, key="p_i_p3")
                with stabs_i[2]:
                    ei1, ei2 = st.columns(2)
                    ei1.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_i_sub[MAPA_I['q8']])[0], "Preg. 4 - Calidad de Info Pre-entrega (NPS)"), use_container_width=True, key="g_i_p4")
                    ei2.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_i_sub[MAPA_I['q11']])[0], "Preg. 5 - Presentación del 0KM (NPS)"), use_container_width=True, key="g_i_p5")
                with stabs_i[3]:
                    pi1, pi2 = st.columns(2)
                    pi1.plotly_chart(crear_grafico_torta(df_i_sub, MAPA_I['q14'], 'Preg. 6 - Recepción Contacto'), use_container_width=True, key="p_i_p6")
                    pi2.plotly_chart(crear_gauge_moderno(calcular_nps_detallado(df_i_sub[MAPA_I['q15']])[0], "Preg. 7 - Sat. Contacto Posterior (NPS)"), use_container_width=True, key="g_i_p7")

                st.markdown("---")
                st.markdown("##### 💬 Verbalizaciones del Cliente (Internas)")
                df_i_v = df_i_sub[["Fecha de ultimo contacto", "Nombre de cliente", MAPA_I['q3'], "Vendedor"]].copy().sort_values("Fecha de ultimo contacto", ascending=False)
                df_i_v["Fecha de ultimo contacto"] = df_i_v["Fecha de ultimo contacto"].dt.strftime('%d/%m/%Y')
                df_i_v = df_i_v.rename(columns={MAPA_I['q3']: 'Comentario Textual'})
                
                busqueda_i = st.text_input("🔍 Buscar en comentarios Internos:", "", key="search_i").strip()
                if busqueda_i:
                    df_i_v = df_i_v[df_i_v['Comentario Textual'].str.contains(busqueda_i, case=False, na=False)]
                st.dataframe(df_i_v, use_container_width=True, hide_index=True, height=180)

        # ==========================================================
        # TAB 2: TABLA UNIFICADA DE ASESORES
        # ==========================================================
        with tab_unificada:
            with st.expander("⚙️ Filtros de Asesores", expanded=True):
                col_fu1, col_fu2, col_fu3 = st.columns(3)
                with col_fu1:
                    anios_comb_u = sorted(list(set(df_m['Anio'].dropna().unique().astype(int)) | set(df_i['Anio'].dropna().unique().astype(int))), reverse=True)
                    anio_sel_u = st.selectbox("Año:", options=anios_comb_u if anios_comb_u else [2026], key="u_anio")
                with col_fu2:
                    set_meses_u = set(df_m[df_m['Anio'] == anio_sel_u]['Mes_Num'].unique()) | set(df_i[df_i['Anio'] == anio_sel_u]['Mes_Num'].unique())
                    meses_disp_nums_u = sorted(list(set_meses_u))
                    meses_disp_nombres_u = [meses_n[m] for m in meses_disp_nums_u] if meses_disp_nums_u else ["Mayo"]
                    meses_sel_nombres_u = st.multiselect("Seleccione Mes(es):", options=meses_disp_nombres_u, default=meses_disp_nombres_u[-1:], key="u_meses")
                    meses_sel_nums_u = [k for k, v in meses_n.items() if v in meses_sel_nombres_u]
                with col_fu3:
                    marcas_disp_u = sorted(list(set(df_m["MARCA"].dropna().unique()) | set(df_i["MARCA"].dropna().unique())))
                    marcas_u = st.multiselect("MARCA:", options=marcas_disp_u, default=marcas_disp_u, key="u_marcas")

                canales_m_u = set(df_m[df_m["MARCA"].isin(marcas_u)]["Canal de Venta"].dropna().unique())
                canales_i_u = set(df_i[df_i["MARCA"].isin(marcas_u)]["Canal de Venta"].dropna().unique())
                canales_disp_u = sorted(list(canales_m_u | canales_i_u))
                canales_u = st.multiselect("Canal de Venta:", options=canales_disp_u, default=canales_disp_u, key="u_canales")

            df_m_time_u = df_m[(df_m["Anio"] == anio_sel_u) & (df_m["Mes_Num"].isin(meses_sel_nums_u))]
            df_i_time_u = df_i[(df_i["Anio"] == anio_sel_u) & (df_i["Mes_Num"].isin(meses_sel_nums_u))]
            df_m_base_u = df_m_time_u[(df_m_time_u["MARCA"].isin(marcas_u)) & (df_m_time_u["Canal de Venta"].isin(canales_u))]
            df_i_base_u = df_i_time_u[(df_i_time_u["MARCA"].isin(marcas_u)) & (df_i_time_u["Canal de Venta"].isin(canales_u))]

            st.header("Ranking de Performance Comercial Integrado")
            st.markdown("Evaluación unificada bajo la metodología estricta de **NPS** para todos los indicadores operativos.")
            
            vendedores_unificados = sorted(list(set(df_m_base_u["Vendedor"].dropna().unique()) | set(df_i_base_u["Vendedor"].dropna().unique())))
            
            if vendedores_unificados:
                resumen_master = []
                for vend in vendedores_unificados:
                    data_m = df_m_base_u[df_m_base_u["Vendedor"] == vend]
                    data_i = df_i_base_u[df_i_base_u["Vendedor"] == vend]
                    
                    if not data_m.empty:
                        nm_q2, pm_q2, _, dm_q2, tm_q2 = calcular_nps_detallado(data_m[MAPA_M['q2']])
                        cortesia_m = calcular_nps_detallado(data_m[MAPA_M['q4']])[0]
                        competencia_m = calcular_nps_detallado(data_m[MAPA_M['q5']])[0]
                        target_m = calcular_faltante_94(pm_q2, dm_q2, tm_q2)
                    else:
                        nm_q2, cortesia_m, competencia_m, target_m, tm_q2 = 0.0, 0.0, 0.0, "Sin registros", 0
                        
                    if not data_i.empty:
                        ni_q2, pi_q2, _, di_q2, ti_q2 = calcular_nps_detallado(data_i[MAPA_I['q2']])
                        cortesia_i = calcular_nps_detallado(data_i[MAPA_I['q4']])[0]
                        target_i = calcular_faltante_94(pi_q2, di_q2, ti_q2)
                    else:
                        ni_q2, cortesia_i, target_i, ti_q2 = 0.0, 0.0, "Sin registros", 0
                    
                    resumen_master.append({
                        "Asesor Comercial": vend,
                        "Muestra M": tm_q2,
                        "NPS Rec. (MARCA)": nm_q2 if tm_q2 > 0 else None,
                        "Cortesía M (NPS)": cortesia_m if tm_q2 > 0 else None,
                        "Competencia M (NPS)": competencia_m if tm_q2 > 0 else None,
                        "Faltante Obj. M (94%)": target_m,
                        "Muestra I": ti_q2,
                        "NPS Rec. (INTERNA)": ni_q2 if ti_q2 > 0 else None,
                        "Cortesía I (NPS)": cortesia_i if ti_q2 > 0 else None,
                        "Faltante Obj. I (94%)": target_i
                    })
                
                df_master = pd.DataFrame(resumen_master).sort_values("Muestra M", ascending=False)
                
                def color_celda_nps_master(val):
                    try:
                        v = float(val)
                        if v >= 94: return 'background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: center;'
                        if v >= 90: return 'background-color: #FFF3CD; color: #856404; font-weight: bold; text-align: center;'
                        return 'background-color: #FFEBEE; color: #C62828; font-weight: bold; text-align: center;'
                    except:
                        return 'text-align: center; color: #999;'

                def estilar_celda_alerta(val):
                    val_str = str(val)
                    if "✅" in val_str:
                        return 'background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: center;'
                    elif "🚨" in val_str:
                        return 'color: #C62828; font-weight: bold; text-align: center;'
                    return 'text-align: center; color: #555;'

                df_styled = df_master.style.map(color_celda_nps_master, subset=["NPS Rec. (MARCA)", "Cortesía M (NPS)", "Competencia M (NPS)", "NPS Rec. (INTERNA)", "Cortesía I (NPS)"])\
                                           .map(estilar_celda_alerta, subset=['Faltante Obj. M (94%)', 'Faltante Obj. I (94%)'])\
                                           .format(precision=1, na_rep="Sin Datos")
                                           
                st.dataframe(df_styled, use_container_width=True, hide_index=True)

        # ==========================================================
        # 👤 TAB 3: FICHA INDIVIDUAL POR ASESOR (HISTÓRICA)
        # ==========================================================
        with tab_individual:
            st.header("📈 Evolución Histórica Completa por Asesor")
            st.markdown("Esta sección analiza la información **total acumulada** sin restricciones de filtros globales.")
            
            vendedores_disponibles = sorted(list(set(df_m["Vendedor"].dropna().unique()) | set(df_i["Vendedor"].dropna().unique())))
            
            if vendedores_disponibles:
                vendedor_sel = st.selectbox("Seleccione el Asesor a evaluar:", options=vendedores_disponibles, key="sb_vendedor_ficha_ind")
                st.markdown(f"## Desempeño Histórico de: **{vendedor_sel}**")
                
                df_vend_full_m = df_m[df_m["Vendedor"] == vendedor_sel].copy()
                if not df_vend_full_m.empty:
                    df_vend_full_m["Periodo"] = df_vend_full_m["Fecha de ultimo contacto"].dt.to_period("M")
                    resumen_mensual_m = []
                    for per, data_m in df_vend_full_m.groupby("Periodo"):
                        n_m, _, _, _, tm_p = calcular_nps_detallado(data_m[MAPA_M['q2']])
                        resumen_mensual_m.append({"Periodo_Str": str(per), "Periodo": per, "NPS": n_m, "Muestra": tm_p})
                    df_ev_m = pd.DataFrame(resumen_mensual_m).sort_values("Periodo")
                else:
                    df_ev_m = pd.DataFrame()

                df_vend_full_i = df_i[df_i["Vendedor"] == vendedor_sel].copy()
                if not df_vend_full_i.empty:
                    df_vend_full_i["Periodo"] = df_vend_full_i["Fecha de ultimo contacto"].dt.to_period("M")
                    resumen_mensual_i = []
                    for per, data_i in df_vend_full_i.groupby("Periodo"):
                        n_i, _, _, _, ti_p = calcular_nps_detallado(data_i[MAPA_I['q2']])
                        resumen_mensual_i.append({"Periodo_Str": str(per), "Periodo": per, "NPS": n_i, "Muestra": ti_p})
                    df_ev_i = pd.DataFrame(resumen_mensual_i).sort_values("Periodo")
                else:
                    df_ev_i = pd.DataFrame()

                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    with st.container(border=True):
                        if not df_vend_full_m.empty:
                            tot_nps_m, _, _, _, tot_muest_m = calcular_nps_detallado(df_vend_full_m[MAPA_M['q2']])
                            st.metric("NPS Recomendación Histórico Total (Marca)", f"{tot_nps_m:.1f}%", f"Muestra Total: {tot_muest_m} encuestas")
                        else:
                            tot_nps_m, tot_muest_m = 0.0, 0
                            st.info("Sin registros históricos en la base de Marca.")
                with col_m2:
                    with st.container(border=True):
                        if not df_vend_full_i.empty:
                            tot_nps_i, _, _, _, tot_muest_i = calcular_nps_detallado(df_vend_full_i[MAPA_I['q2']])
                            st.metric("NPS Recomendación Histórico Total (Interno)", f"{tot_nps_i:.1f}%", f"Muestra Total: {tot_muest_i} encuestas")
                        else:
                            tot_nps_i, tot_muest_i = 0.0, 0
                            st.info("Sin registros históricos en la base Interna.")

                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.markdown("#### 🏢 Línea del Tiempo: Encuestas de Marca")
                    if not df_ev_m.empty:
                        fig_m = px.line(df_ev_m, x="Periodo_Str", y="NPS", 
                                        text=df_ev_m["NPS"].round(1).astype(str) + "%", 
                                        labels={"Periodo_Str": "Mes / Periodo", "NPS": "NPS %"}, markers=True)
                        fig_m.add_hline(y=94, line_dash="dash", line_color="green", annotation_text="Objetivo (94%)")
                        fig_m.update_traces(textposition="top center", line=dict(color='#2E7D32', width=3))
                        fig_m.update_layout(yaxis=dict(range=[-100, 110]), height=260, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_m, use_container_width=True, key="canvas_ev_marca_ind")
                    else:
                        st.caption("No hay datos suficientes para graficar.")
                with col_g2:
                    st.markdown("#### 🎯 Línea del Tiempo: Encuestas Internas")
                    if not df_ev_i.empty:
                        fig_i = px.line(df_ev_i, x="Periodo_Str", y="NPS", 
                                        text=df_ev_i["NPS"].round(1).astype(str) + "%", 
                                        labels={"Periodo_Str": "Mes / Periodo", "NPS": "NPS %"}, markers=True)
                        fig_i.add_hline(y=94, line_dash="dash", line_color="green", annotation_text="Objetivo (94%)")
                        fig_i.update_traces(textposition="top center", line=dict(color='#007bff', width=3))
                        fig_i.update_layout(yaxis=dict(range=[-100, 110]), height=260, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_i, use_container_width=True, key="canvas_ev_interna_ind")
                    else:
                        st.caption("No hay datos suficientes para graficar.")

                st.markdown("---")
                st.markdown("### 📅 Análisis Detallado por Año Seleccionado")
                
                anios_vendedor = sorted(list(set(df_vend_full_m['Anio'].dropna().unique().astype(int)) | set(df_vend_full_i['Anio'].dropna().unique().astype(int))), reverse=True)
                
                if anios_vendedor:
                    anio_tabla = st.selectbox("Seleccione el año que desea desglosar:", options=anios_vendedor, key="sb_anio_tabla_individual")
                    df_tabla_m = df_vend_full_m[df_vend_full_m['Anio'] == anio_tabla]
                    df_tabla_i = df_vend_full_i[df_vend_full_i['Anio'] == anio_tabla]
                    
                    tabla_datos = []
                    for m_num in range(1, 13):
                        sub_m = df_tabla_m[df_tabla_m['Mes_Num'] == m_num]
                        sub_i = df_tabla_i[df_tabla_i['Mes_Num'] == m_num]
                        
                        if sub_m.empty and sub_i.empty:
                            continue
                            
                        nps_m, _, _, _, count_m = calcular_nps_detallado(sub_m[MAPA_M['q2']]) if not sub_m.empty else (None, 0, 0, 0, 0)
                        nps_i, _, _, _, count_i = calcular_nps_detallado(sub_i[MAPA_I['q2']]) if not sub_i.empty else (None, 0, 0, 0, 0)
                        
                        tabla_datos.append({
                            "Mes": meses_n[m_num],
                            "Muestra Marca": count_m,
                            "NPS Marca %": f"{nps_m:.1f}%" if count_m > 0 else "Sin Datos",
                            "Muestra Interna": count_i,
                            "NPS Interno %": f"{nps_i:.1f}%" if count_i > 0 else "Sin Datos"
                        })
                    
                    if tabla_datos:
                        df_resumen_anio = pd.DataFrame(tabla_datos)
                        st.markdown(f"**Desglose mensual de actividades durante el año {anio_tabla}:**")
                        st.dataframe(df_resumen_anio, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No se registran encuestas en ningún mes para el año {anio_tabla}.")
                else:
                    st.info("El asesor seleccionado no cuenta con registros fechados para estructurar el desglose anual.")

        # ==========================================================
        # 💬 TAB 4: ANÁLISIS DE VOZ DEL CLIENTE Y GESTIÓN DE QUEJAS
        # ==========================================================
        with tab_feedback:
            # Dividimos la pestaña entera en 2 columnas maestras (50% y 50%) con un espacio amplio en el medio
            col_izq_voz, col_der_quejas = st.columns([1, 1], gap="large")
            
            # ---------------------------------------------------------
            # LADO IZQUIERDO: VOZ DEL CLIENTE
            # ---------------------------------------------------------
            with col_izq_voz:
                st.header("💬 Voz del Cliente")
                st.markdown("Inteligencia de Texto basada en las encuestas.")
                
                with st.expander("⚙️ Filtros de Voz del Cliente", expanded=True):
                    col_ff1, col_ff2, col_ff3 = st.columns(3)
                    with col_ff1:
                        anios_comb_f = sorted(list(set(df_m['Anio'].dropna().unique().astype(int)) | set(df_i['Anio'].dropna().unique().astype(int))), reverse=True)
                        anio_sel_f = st.selectbox("Año:", options=anios_comb_f if anios_comb_f else [2026], key="f_anio")
                    with col_ff2:
                        set_meses_f = set(df_m[df_m['Anio'] == anio_sel_f]['Mes_Num'].unique()) | set(df_i[df_i['Anio'] == anio_sel_f]['Mes_Num'].unique())
                        meses_disp_nums_f = sorted(list(set_meses_f))
                        meses_disp_nombres_f = [meses_n[m] for m in meses_disp_nums_f] if meses_disp_nums_f else ["Mayo"]
                        meses_sel_nombres_f = st.multiselect("Mes(es):", options=meses_disp_nombres_f, default=meses_disp_nombres_f[-1:], key="f_meses")
                        meses_sel_nums_f = [k for k, v in meses_n.items() if v in meses_sel_nombres_f]
                    with col_ff3:
                        marcas_disp_f = sorted(list(set(df_m["MARCA"].dropna().unique()) | set(df_i["MARCA"].dropna().unique())))
                        marcas_f = st.multiselect("MARCA:", options=marcas_disp_f, default=marcas_disp_f, key="f_marcas")

                    canales_m_f = set(df_m[df_m["MARCA"].isin(marcas_f)]["Canal de Venta"].dropna().unique())
                    canales_i_f = set(df_i[df_i["MARCA"].isin(marcas_f)]["Canal de Venta"].dropna().unique())
                    canales_disp_f = sorted(list(canales_m_f | canales_i_f))
                    canales_f = st.multiselect("Canal de Venta:", options=canales_disp_f, default=canales_disp_f, key="f_canales")

                df_m_time_f = df_m[(df_m["Anio"] == anio_sel_f) & (df_m["Mes_Num"].isin(meses_sel_nums_f))]
                df_i_time_f = df_i[(df_i["Anio"] == anio_sel_f) & (df_i["Mes_Num"].isin(meses_sel_nums_f))]
                df_m_base = df_m_time_f[(df_m_time_f["MARCA"].isin(marcas_f)) & (df_m_time_f["Canal de Venta"].isin(canales_f))]
                df_i_base = df_i_time_f[(df_i_time_f["MARCA"].isin(marcas_f)) & (df_i_time_f["Canal de Venta"].isin(canales_f))]

                st.markdown("---")
                st.markdown("### 📈 Tendencia Mensual del % de Reclamos")
                col_linea_m, col_linea_i = st.columns(2)
                
                with col_linea_m:
                    columnas_marca_reclamo = [MAPA_M['q1'], MAPA_M['q2'], MAPA_M['q4'], MAPA_M['q5'], MAPA_M['q8'], MAPA_M['q11'], MAPA_M['q13'], MAPA_M['q15']]
                    fig_linea_m = crear_linea_reclamos_porcentaje(df_m_base, columnas_marca_reclamo, "🏢 Marca", meses_n, "marca")
                    st.plotly_chart(fig_linea_m, use_container_width=True)
                    
                with col_linea_i:
                    columnas_interna_reclamo = [MAPA_I['q1'], MAPA_I['q2'], MAPA_I['q4'], MAPA_I['q8'], MAPA_I['q11'], MAPA_I['q15']]
                    fig_linea_i = crear_linea_reclamos_porcentaje(df_i_base, columnas_interna_reclamo, "🎯 Internas", meses_n, "interna")
                    st.plotly_chart(fig_linea_i, use_container_width=True)
                    
                st.markdown("---")
                st.markdown("### 📊 Temas Operativos")
                col_bar_m, col_bar_i = st.columns(2)
                
                with col_bar_m:
                    st.markdown("##### Marca")
                    df_m_fback = df_m_base[df_m_base["Categoria_Comentario"] != "SIN COMENTARIO"].copy()
                    if not df_m_fback.empty:
                        conteo_com_m = df_m_fback["Categoria_Comentario"].value_counts().reset_index()
                        conteo_com_m.columns = ["Categoría", "Casos"]
                        fig_bar_m = px.bar(conteo_com_m, x="Casos", y="Categoría", orientation='h', color="Casos", color_continuous_scale="Reds")
                        fig_bar_m.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
                        st.plotly_chart(fig_bar_m, use_container_width=True)
                    else:
                        st.caption("No hay comentarios válidos.")
                        
                with col_bar_i:
                    st.markdown("##### Internos")
                    df_i_fback = df_i_base[df_i_base["Categoria_Comentario"] != "SIN COMENTARIO"].copy()
                    if not df_i_fback.empty:
                        conteo_com_i = df_i_fback["Categoria_Comentario"].value_counts().reset_index()
                        conteo_com_i.columns = ["Categoría", "Casos"]
                        fig_bar_i = px.bar(conteo_com_i, x="Casos", y="Categoría", orientation='h', color="Casos", color_continuous_scale="Blues")
                        fig_bar_i.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
                        st.plotly_chart(fig_bar_i, use_container_width=True)
                    else:
                        st.caption("No hay comentarios válidos.")
                        
                st.markdown("---")
                st.markdown("### 🔍 Perforación de Texto")
                categorias_fback_disp = ["TODAS", "ATENCIÓN Y ASESORAMIENTO", "PROCESO DE ENTREGA / TIEMPOS", "PRECIO Y FINANCIACIÓN", "ESTADO Y LIMPIEZA DEL VEHÍCULO", "GESTORÍA Y ADMINISTRACIÓN", "TEST DRIVE", "OTROS / GENERAL"]
                cat_fback_sel = st.selectbox("📌 Filtrar por Categoría:", options=categorias_fback_disp, index=0, key="sb_feedback_cat_drill")
                
                f_col_m, f_col_i = st.columns(2)
                with f_col_m:
                    st.markdown("##### Marca")
                    df_tabla_fback_m = df_m_base.copy()
                    if cat_fback_sel != "TODAS":
                        df_tabla_fback_m = df_tabla_fback_m[df_tabla_fback_m["Categoria_Comentario"] == cat_fback_sel]
                    df_tabla_fback_m_v = df_tabla_fback_m[["Fecha de ultimo contacto", "Nombre de cliente", MAPA_M['q3'], "Vendedor"]].copy()
                    if not df_tabla_fback_m_v.empty:
                        df_tabla_fback_m_v["Fecha de ultimo contacto"] = df_tabla_fback_m_v["Fecha de ultimo contacto"].dt.strftime('%d/%m/%Y')
                        df_tabla_fback_m_v = df_tabla_fback_m_v.rename(columns={MAPA_M['q3']: 'Comentario Textual'}).dropna(subset=['Comentario Textual'])
                    st.dataframe(df_tabla_fback_m_v, use_container_width=True, hide_index=True, height=200)
                    
                with f_col_i:
                    st.markdown("##### Internas")
                    df_tabla_fback_i = df_i_base.copy()
                    if cat_fback_sel != "TODAS":
                        df_tabla_fback_i = df_tabla_fback_i[df_tabla_fback_i["Categoria_Comentario"] == cat_fback_sel]
                    df_tabla_fback_i_v = df_tabla_fback_i[["Fecha de ultimo contacto", "Nombre de cliente", MAPA_I['q3'], "Vendedor"]].copy()
                    if not df_tabla_fback_i_v.empty:
                        df_tabla_fback_i_v["Fecha de ultimo contacto"] = df_tabla_fback_i_v["Fecha de ultimo contacto"].dt.strftime('%d/%m/%Y')
                        df_tabla_fback_i_v = df_tabla_fback_i_v.rename(columns={MAPA_I['q3']: 'Comentario Textual'}).dropna(subset=['Comentario Textual'])
                    st.dataframe(df_tabla_fback_i_v, use_container_width=True, hide_index=True, height=200)

            # ---------------------------------------------------------
            # LADO DERECHO: GESTIÓN DE QUEJAS
            # ---------------------------------------------------------
            # ---------------------------------------------------------
            # LADO DERECHO: GESTIÓN DE QUEJAS
            # ---------------------------------------------------------
            with col_der_quejas:
                st.header("⚠️ Auditoría de Quejas")
                st.markdown("Análisis de insatisfacción y reclamos.")
                
                if not df_q.empty:
                    with st.expander("🔄 Filtro de Quejas", expanded=True):
                        fc1, fc2, fc3 = st.columns(3)
                        with fc1:
                            if "Fecha_Filtro" in df_q.columns and not pd.api.types.is_datetime64_any_dtype(df_q["Fecha_Filtro"]):
                                df_q["Fecha_Filtro"] = pd.to_datetime(df_q["Fecha_Filtro"])
                            anos_disponibles = ["TODOS"] + sorted(list(df_q["Fecha_Filtro"].dt.year.dropna().unique()), reverse=True)
                            ano_filtrado = st.selectbox("📅 Año:", options=[str(a) for a in anos_disponibles], index=0, key="sb_ctrl_ano")
                            
                        with fc2:
                            meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6: "Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
                            df_temp_mes = df_q.copy()
                            if ano_filtrado != "TODOS":
                                df_temp_mes = df_temp_mes[df_temp_mes["Fecha_Filtro"].dt.year == int(ano_filtrado)]
                            meses_disp_nums = sorted(list(df_temp_mes["Mes_Num"].dropna().unique()))
                            
                            # --- CAMBIO AQUÍ: Lista de meses disponibles y Multiselect ---
                            meses_disponibles = [meses_dict[int(m)] for m in meses_disp_nums]
                            meses_filtrados = st.multiselect("🗓️ Mes(es):", options=meses_disponibles, default=meses_disponibles, key="sb_ctrl_mes_multi")
                            meses_sel_nums_q = [k for k, v in meses_dict.items() if v in meses_filtrados]
                            
                        with fc3:
                            df_temp_canal = df_temp_mes.copy()
                            if meses_sel_nums_q:
                                df_temp_canal = df_temp_canal[df_temp_canal["Mes_Num"].isin(meses_sel_nums_q)]
                            canales_disponibles = ["TODOS"] + sorted(list(df_temp_canal["canal de venta"].dropna().unique()))
                            canal_filtrado = st.selectbox("🔌 Canal:", options=canales_disponibles, index=0, key="sb_ctrl_canal")

                    # --- LÓGICA DE FILTRADO ACTUALIZADA ---
                    df_q_filtrado = df_q.copy()
                    if ano_filtrado != "TODOS":
                        df_q_filtrado = df_q_filtrado[df_q_filtrado["Fecha_Filtro"].dt.year == int(ano_filtrado)]
                    
                    # Filtramos por los múltiples meses seleccionados
                    if meses_sel_nums_q:
                        df_q_filtrado = df_q_filtrado[df_q_filtrado["Mes_Num"].isin(meses_sel_nums_q)]
                    elif not meses_filtrados: 
                        # Si el usuario borra todos los meses del selector, vaciamos la tabla temporalmente
                        df_q_filtrado = df_q_filtrado.iloc[0:0] 
                        
                    if canal_filtrado != "TODOS":
                        df_q_filtrado = df_q_filtrado[df_q_filtrado["canal de venta"] == canal_filtrado]
                    st.markdown("---")
                    tot_quejas = len(df_q_filtrado)
                    casos_resueltos = df_q_filtrado[df_q_filtrado["Reporte tratado por"].str.contains("CERR|SOLUC|FINALIZ|OK|OK TALLER", na=False, case=False)]
                    tot_resueltos = len(casos_resueltos)
                    tot_abiertos = tot_quejas - tot_resueltos
                    tasa_resolucion = (tot_resueltos / tot_quejas * 100) if tot_quejas > 0 else 0.0
                    
                    cq1, cq2, cq3 = st.columns(3)
                    with cq1: st.metric("Quejas", f"{tot_quejas} casos")
                    with cq2: st.metric("Pendientes", f"{tot_abiertos} activos")
                    with cq3: st.metric("Resolución", f"{tasa_resolucion:.1f}%")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    cg_col1, cg_col2 = st.columns(2)
                    
                    with cg_col1:
                        st.markdown("#### 📊 Embudo Reclamo")
                        df_funnel = df_q_filtrado["Categorizacion del Reclamo"].value_counts().reset_index()
                        df_funnel.columns = ["Categorizacion del Reclamo", "Casos"]
                        
                        if not df_funnel.empty:
                            fig_funnel = px.funnel(df_funnel.head(12), x="Casos", y="Categorizacion del Reclamo", color="Categorizacion del Reclamo", color_discrete_sequence=px.colors.sequential.Reds_r)
                            fig_funnel.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, clickmode='event+select')
                            
                            event_funnel = st.plotly_chart(fig_funnel, use_container_width=True, key="funnel_quejas_dinamico", on_select="rerun", selection_mode="points")
                            
                            if event_funnel and len(event_funnel.selection["points"]) > 0:
                                st.session_state.filtro_cat_q = event_funnel.selection["points"][0]["y"]
                            else:
                                st.session_state.filtro_cat_q = "Todas"
                                
                            st.caption(f"Categoría: `{st.session_state.filtro_cat_q}`")
                        else:
                            st.info("Sin registros.")
                            
                    with cg_col2:
                        st.markdown("#### 🏢 Sectores")
                        df_sectores = df_q_filtrado["Sector Afectado"].value_counts().reset_index()
                        df_sectores.columns = ["Sector Afectado", "Casos"]
                        
                        if not df_sectores.empty:
                            fig_sectores = px.bar(df_sectores.head(12), x="Sector Afectado", y="Casos", text="Casos", color="Casos", color_continuous_scale="Oranges")
                            fig_sectores.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, coloraxis_showscale=False, clickmode='event+select')
                            
                            event_sec = st.plotly_chart(fig_sectores, use_container_width=True, key="barras_sectores_dinamico", on_select="rerun", selection_mode="points")
                            
                            if event_sec and len(event_sec.selection["points"]) > 0:
                                st.session_state.filtro_sec_q = event_sec.selection["points"][0]["x"]
                            else:
                                st.session_state.filtro_sec_q = "Todos"
                                
                            st.caption(f"Sector: `{st.session_state.filtro_sec_q}`")
                        else:
                            st.info("Sin registros.")
                            
                    st.markdown("---")
                    st.markdown("### 🔍 Detalle de Quejas")
                    
                    df_visual_q = df_q_filtrado.copy()
                    if st.session_state.filtro_cat_q != "Todas":
                        df_visual_q = df_visual_q[df_visual_q["Categorizacion del Reclamo"] == st.session_state.filtro_cat_q]
                    if st.session_state.filtro_sec_q != "Todos":
                        df_visual_q = df_visual_q[df_visual_q["Sector Afectado"] == st.session_state.filtro_sec_q]
                    
                    if "comentario" not in df_visual_q.columns:
                        df_visual_q["comentario"] = "Sin comentarios cargados"

                    columnas_solicitadas = ["tipo de queja", "marca", "cliente", "vendedor", "canal de venta", "comentario"]
                    df_tabla_final = df_visual_q[columnas_solicitadas].rename(columns={
                        "tipo de queja": "Tipo", "marca": "Marca", "cliente": "Cliente", "vendedor": "Vendedor",
                        "canal de venta": "Canal", "comentario": "Comentario del Cliente"
                    })
                    
                    buscar_queja = st.text_input("🔍 Buscar palabra clave en quejas:", "", key="search_quejas_dinamico_input").strip()
                    if buscar_queja:
                        mascara = df_tabla_final.astype(str).apply(lambda x: x.str.contains(buscar_queja, case=False, na=False)).any(axis=1)
                        df_tabla_final = df_tabla_final[mascara]
                    
                    st.dataframe(df_tabla_final, use_container_width=True, hide_index=True, height=280)
                else:
                    st.info("No se encontraron registros de quejas.")

        # ==========================================================
        # 🏆 TAB 5: PRIMA DE CALIDAD (ENC ROAR)
        # ==========================================================
        with tab_prima:
            st.markdown("## 📊 Tablero de Auditoría y Liquidación: Prima de Calidad Venta")
            
            if not df_roar.empty:
                if "Anio" not in df_roar.columns or df_roar["Anio"].isna().all():
                    col_fech = next((c for c in df_roar.columns if 'fech' in str(c).lower() or 'mes' in str(c).lower()), df_roar.columns[0])
                    df_roar["Fecha de ultimo contacto"] = pd.to_datetime(df_roar[col_fech], dayfirst=True, errors='coerce')
                    df_roar["Anio"] = df_roar["Fecha de ultimo contacto"].dt.year
                
                with st.expander("⚙️ Filtros de Prima", expanded=True):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        anios_roar = sorted(list(df_roar["Anio"].dropna().unique()), reverse=True)
                        anios_roar_str = [str(int(a)) for a in anios_roar if pd.notna(a)]
                        anio_roar_sel = st.selectbox("Año:", options=anios_roar_str if anios_roar_str else ["2026"], key="sb_roar_anio_aislado")
                    
                    with col_f2:
                        marcas_roar = sorted(list(df_roar["Marca_Normalizada"].dropna().unique())) if "Marca_Normalizada" in df_roar.columns else ["PEUGEOT", "CITROEN"]
                        marcas_roar = [m for m in marcas_roar if m != "SIN MARCA"]
                        marca_roar_sel = st.multiselect("Marcas:", options=marcas_roar, default=marcas_roar, key="sb_roar_marca_aislada")
                
                st.markdown("---")
                
                # --- AYUDA RÁPIDA DE FÓRMULAS CON ICONO TOOLTIP NATIVO ---
                col_ayuda1, col_ayuda2, col_ayuda3, col_ayuda4 = st.columns(4)
                col_ayuda1.button("💰 Techo Máximo ⓘ", help="Fórmula: Suma(Precio Facturado de TODOS los autos patentados) × 0.40%", use_container_width=True)
                col_ayuda2.button("💵 Liquidación Aprobada ⓘ", help="Fórmula: Suma(Precio Facturado de autos con H.O. ≤ día 24) × SUMA DRIVERS", use_container_width=True)
                col_ayuda3.button("💸 Pérdida por H.O. ⓘ", help="Fórmula: Suma(Precio Facturado de autos tardíos/sin fecha) × SUMA DRIVERS", use_container_width=True)
                col_ayuda4.button("📉 Pérdida por Calidad ⓘ", help="Fórmula: [Techo Máximo] - [Liquidación Aprobada] - [Pérdida por H.O.]", use_container_width=True)
                
                meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                
                datos_umbrales = [
                    {"Mes": "🔑 UMBRALES (VENTAS)"},
                    {"Mes": "📞 Contacto Posterior 6MM (Meta ≥ 80%)"},
                    {"Mes": "🏢 NPS Mínimo Global (Meta ≥ 88.5%)"},
                    {"Mes": "✉️ Tasa de Mail Válido (Meta ≥ 80%)"},
                    {"Mes": "📊 Muestra Mínima (Meta ≥ 4 Peugeot / 3 Citroen)"},
                    {"Mes": "🎯 INCENTIVOS COMERCIALES"},
                    {"Mes": "🔹 Recomendación (Q2)"},
                    {"Mes": "🔹 Q8 Info Entre Compra y Entrega"},
                    {"Mes": "🔹 Q4 Cortesía y Amabilidad"},
                    {"Mes": "🔹 Q15 Satisfacción del Contacto"},
                    {"Mes": "💰 SUMA DRIVERS (Unitario)"},
                    {"Mes": "✅ Cant. Patentadas y Entregadas en Regla"},
                    {"Mes": "⚠️ Cant. Fuera de Plazo o Sin H.O."},
                    {"Mes": "💰 Techo Máximo Potencial (0.40%)"},
                    {"Mes": "💵 Liquidación Aprobada (Efectiva)"},
                    {"Mes": "💸 Pérdida por H.O. (Fuera de Plazo)"},
                    {"Mes": "📉 Pérdida por Calidad / NPS"}
                ]
                
                col_q14 = next((c for c in df_roar.columns if '14' in str(c) or 'contactad' in str(c).lower()), None)
                anio_num = int(anio_roar_sel) if anio_roar_sel else 2026
                
                meta_muestra = 0
                if marca_roar_sel:
                    marcas_upper = [m.upper() for m in marca_roar_sel]
                    if "PEUGEOT" in marcas_upper: meta_muestra += 4
                    if "CITROEN" in marcas_upper: meta_muestra += 3
                else:
                    meta_muestra = 7 
                
                def get_inc(nps_v, q_t):
                    if nps_v <= 90.49: return 0.0
                    if q_t == 'q2': return 0.20 if nps_v >= 96 else 0.13
                    if q_t == 'q8': return 0.14 if nps_v >= 96 else 0.08
                    if q_t in ['q4', 'q15']: return 0.03 if nps_v >= 96 else 0.02
                    return 0.0

                # DICCIONARIOS PARA ALMACENAR MONTOS CRUDOS MES A MES (Para Flujo de Caja y Gráfico)
                flujo_techo = {}
                flujo_cobrado = {}
                flujo_perdida = {}

                for i, mes_nombre in enumerate(meses_nombres):
                    mes_num = i + 1
                    for r in range(17): datos_umbrales[r][mes_nombre] = "-"
                    datos_umbrales[0][mes_nombre] = "" 
                    datos_umbrales[5][mes_nombre] = ""
                    
                    porcentaje_6mm = 0.0
                    nps_val = 0.0
                    tasa_mail = 0.0
                    cant_muestra = 0
                    
                    # 1. Contacto 6MM
                    fecha_inicio_6mm = pd.to_datetime(f"{anio_num}-{mes_num}-01") - pd.DateOffset(months=5)
                    fecha_fin_6mm = pd.to_datetime(f"{anio_num}-{mes_num}-01") + pd.offsets.MonthEnd(1)
                    if "Fecha de ultimo contacto" in df_roar.columns and col_q14:
                        mascara_tiempo = (df_roar["Fecha de ultimo contacto"] >= fecha_inicio_6mm) & (df_roar["Fecha de ultimo contacto"] <= fecha_fin_6mm)
                        df_bloque = df_roar[mascara_tiempo].copy()
                        if marca_roar_sel and "Marca_Normalizada" in df_bloque.columns:
                            df_bloque = df_bloque[df_bloque["Marca_Normalizada"].isin(marca_roar_sel)]
                        if not df_bloque.empty:
                            respuestas = df_bloque[col_q14].dropna().astype(str).str.strip().str.upper().str.replace('Í', 'I')
                            respuestas_validas = respuestas[respuestas.isin(["SI", "NO"])]
                            total_validas = len(respuestas_validas)
                            if total_validas > 0:
                                porcentaje_6mm = (len(respuestas_validas[respuestas_validas == "SI"]) / total_validas) * 100
                                datos_umbrales[1][mes_nombre] = f"{porcentaje_6mm:.1f}%"
                    
                    # 2. NPS Global
                    df_mes_nps = pd.DataFrame()
                    if not df_m.empty and MAPA_M['q2'] in df_m.columns:
                        mascara_mes = (df_m["Anio"] == anio_num) & (df_m["Mes_Num"] == mes_num)
                        df_mes_nps = df_m[mascara_mes].copy()
                        if marca_roar_sel and "MARCA" in df_mes_nps.columns:
                            df_mes_nps = df_mes_nps[df_mes_nps["MARCA"].astype(str).str.strip().str.upper().isin(marcas_upper)]
                        if not df_mes_nps.empty:
                            nps_val, _, _, _, tot_nps = calcular_nps_detallado(df_mes_nps[MAPA_M['q2']])
                            if tot_nps > 0: datos_umbrales[2][mes_nombre] = f"{nps_val:.1f}%"
                    
                    # 3. Mail Válido
                    col_estado = next((c for c in df_base.columns if 'estado de limpieza' in c.lower()), None)
                    col_rechazo = next((c for c in df_base.columns if 'razón de rechazo' in c.lower() or 'razon de rechazo' in c.lower()), None)
                    if not df_base.empty and col_estado:
                        mascara_mes_base = (df_base["Anio"] == anio_num) & (df_base["Mes_Num"] == mes_num)
                        df_mes_base = df_base[mascara_mes_base].copy()
                        if marca_roar_sel and "Marca_Normalizada" in df_mes_base.columns:
                            df_mes_base = df_mes_base[df_mes_base["Marca_Normalizada"].isin(marcas_upper)]
                        if not df_mes_base.empty:
                            estado_serie = df_mes_base[col_estado].astype(str).str.strip().str.upper().str.replace('Á', 'A')
                            cant_validos = (estado_serie == "VALIDO").sum()
                            razones_validas_penalizables = [
                                "NoContactProvided",
                                "No se proporciono ningun contacto valido",
                                "Correo electrónico/teléfono ausente;Correo electrónico/teléfono Inválido",
                                "Invalid Email",
                                "Mandatory field missing - email; invalid email"
                            ]
                            cant_rechazos = 0
                            if col_rechazo:
                                razon_serie = df_mes_base[col_rechazo].astype(str).str.strip()
                                mascara_rechazos = (estado_serie.str.contains("NO VALID", na=False)) & (razon_serie.isin(razones_validas_penalizables))
                                cant_rechazos = mascara_rechazos.sum()
                            total_divisor = cant_validos + cant_rechazos
                            if total_divisor > 0:
                                tasa_mail = (cant_validos / total_divisor) * 100
                                datos_umbrales[3][mes_nombre] = f"{tasa_mail:.1f}%"
                    
                    # 4. Muestra Mínima
                    if not df_m.empty:
                        mascara_mes_muestra = (df_m["Anio"] == anio_num) & (df_m["Mes_Num"] == mes_num)
                        df_mes_muestra = df_m[mascara_mes_muestra].copy()
                        if marca_roar_sel and "MARCA" in df_mes_muestra.columns:
                            df_mes_muestra = df_mes_muestra[df_mes_muestra["MARCA"].astype(str).str.strip().str.upper().isin(marcas_upper)]
                        cant_muestra = len(df_mes_muestra)
                        if cant_muestra > 0: datos_umbrales[4][mes_nombre] = str(cant_muestra)
                        
                    # 5. Cálculo Condicional de Drivers (Target de Bonus)
                    llaves_ok = (porcentaje_6mm >= 80.0) and (nps_val >= 88.5) and (tasa_mail >= 80.0) and (cant_muestra >= meta_muestra)
                    
                    nps_q2 = calcular_nps_detallado(df_mes_nps[MAPA_M['q2']])[0] if not df_mes_nps.empty else 0.0
                    nps_q8 = calcular_nps_detallado(df_mes_nps[MAPA_M['q8']])[0] if not df_mes_nps.empty else 0.0
                    nps_q4 = calcular_nps_detallado(df_mes_nps[MAPA_M['q4']])[0] if not df_mes_nps.empty else 0.0
                    nps_q15 = calcular_nps_detallado(df_mes_nps[MAPA_M['q15']])[0] if not df_mes_nps.empty else 0.0
                    
                    inc_q2 = get_inc(nps_q2, 'q2') if llaves_ok else 0.0
                    inc_q8 = get_inc(nps_q8, 'q8') if llaves_ok else 0.0
                    inc_q4 = get_inc(nps_q4, 'q4') if llaves_ok else 0.0
                    inc_q15 = get_inc(nps_q15, 'q15') if llaves_ok else 0.0
                    inc_tot = inc_q2 + inc_q8 + inc_q4 + inc_q15
                    
                    # 6. Cantidades y Cálculos Monetarios
                    cant_pat_entregados = 0
                    cant_vacios = 0
                    cant_fuera_tiempo = 0
                    
                    techo_maximo = 0.0
                    liq_aprobada = 0.0
                    liq_perdida_ho = 0.0
                    liq_perdida_nps = 0.0
                    
                    if not df_duv.empty and "Anio_Patentamiento" in df_duv.columns:
                        df_mes_duv = df_duv[(df_duv["Anio_Patentamiento"] == anio_num) & (df_duv["Mes_Patentamiento"] == mes_num)].copy()
                        
                        if marca_roar_sel and "Marca_Normalizada" in df_mes_duv.columns:
                            df_mes_duv = df_mes_duv[df_mes_duv["Marca_Normalizada"].isin(marcas_upper)]
                            
                        if not df_mes_duv.empty:
                            if mes_num == 12:
                                mes_sig = 1
                                anio_sig = anio_num + 1
                            else:
                                mes_sig = mes_num + 1
                                anio_sig = anio_num
                            
                            fecha_limite_ho = pd.to_datetime(f"{anio_sig}-{mes_sig:02d}-24 23:59:59")
                            
                            mascara_ok = (df_mes_duv["FECHA DE H.O."].notna()) & (df_mes_duv["FECHA DE H.O."] <= fecha_limite_ho)
                            cant_pat_entregados = int(mascara_ok.sum())
                            
                            cant_vacios = int(df_mes_duv["FECHA DE H.O."].isna().sum())
                            cant_fuera_tiempo = int((df_mes_duv["FECHA DE H.O."] > fecha_limite_ho).sum())
                            
                            if "Precio Facturado" in df_mes_duv.columns:
                                pozo_total_facturado = df_mes_duv["Precio Facturado"].sum()
                                suma_ok = df_mes_duv.loc[mascara_ok, "Precio Facturado"].sum()
                                suma_fuera = df_mes_duv.loc[~mascara_ok, "Precio Facturado"].sum()
                                
                                techo_maximo = pozo_total_facturado * 0.0040
                                liq_aprobada = suma_ok * (inc_tot / 100.0)
                                liq_perdida_ho = suma_fuera * (inc_tot / 100.0)
                                liq_perdida_nps = techo_maximo - liq_aprobada - liq_perdida_ho
                                if liq_perdida_nps < 0: liq_perdida_nps = 0.0
                    
                    # Guardamos los valores crudos para los KPIs y el Gráfico
                    flujo_techo[mes_nombre] = techo_maximo
                    flujo_cobrado[mes_nombre] = liq_aprobada
                    flujo_perdida[mes_nombre] = liq_perdida_ho + liq_perdida_nps

                    # Carga de Resultados a la tabla
                    datos_umbrales[6][mes_nombre] = f"{inc_q2:.2f}%"
                    datos_umbrales[7][mes_nombre] = f"{inc_q8:.2f}%"
                    datos_umbrales[8][mes_nombre] = f"{inc_q4:.2f}%"
                    datos_umbrales[9][mes_nombre] = f"{inc_q15:.2f}%"
                    datos_umbrales[10][mes_nombre] = f"{inc_tot:.2f}%"
                    
                    datos_umbrales[11][mes_nombre] = str(cant_pat_entregados)
                    
                    total_fuera = cant_vacios + cant_fuera_tiempo
                    if total_fuera > 0:
                        datos_umbrales[12][mes_nombre] = f"{total_fuera}  (❌ {cant_fuera_tiempo} tarde | 🔲 {cant_vacios} vacíos)"
                    else:
                        datos_umbrales[12][mes_nombre] = "0"
                        
                    def format_moneda(valor):
                        if valor <= 0: return "-"
                        return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        
                    datos_umbrales[13][mes_nombre] = format_moneda(techo_maximo)
                    datos_umbrales[14][mes_nombre] = format_moneda(liq_aprobada)
                    datos_umbrales[15][mes_nombre] = format_moneda(liq_perdida_ho)
                    datos_umbrales[16][mes_nombre] = format_moneda(liq_perdida_nps)
                
                df_umbrales = pd.DataFrame(datos_umbrales)

                # ==========================================================
                # MATRIZ DE LIQUIDACIÓN Y ESTILOS (1° LA TABLA)
                # ==========================================================
                def estilar_filas_prima(row):
                    estilos = []
                    es_cabecera = "🔑" in str(row["Mes"])
                    es_contacto = "Contacto Posterior" in str(row["Mes"])
                    es_nps = "NPS Mínimo Global" in str(row["Mes"])
                    es_mail = "Tasa de Mail Válido" in str(row["Mes"])
                    es_muestra = "Muestra Mínima" in str(row["Mes"])
                    es_incentivo_cabecera = "🎯" in str(row["Mes"])
                    es_driver = "🔹" in str(row["Mes"])
                    es_cant_pat = "✅" in str(row["Mes"])
                    es_fuera_plazo = "⚠️" in str(row["Mes"])
                    es_suma = "💰 SUMA" in str(row["Mes"])
                    es_techo = "💰 Techo" in str(row["Mes"])
                    es_liq_ok = "💵" in str(row["Mes"])
                    es_liq_ho = "💸" in str(row["Mes"])
                    es_liq_nps = "📉" in str(row["Mes"])
                    
                    for col in row.index:
                        if col == "Mes":
                            if es_cabecera or es_incentivo_cabecera:
                                estilos.append('background-color: #f0f2f6; font-weight: bold; color: #31333F; border-bottom: 2px solid #ddd; border-top: 1px solid #ddd;')
                            elif es_driver or es_cant_pat or es_fuera_plazo:
                                estilos.append('background-color: white; color: #444; text-align: left; padding-left: 15px; font-weight: 500;')
                            elif es_techo or es_liq_ok or es_liq_ho or es_liq_nps:
                                estilos.append('background-color: white; color: #333; text-align: left; padding-left: 15px; font-weight: bold;')
                            elif es_suma:
                                estilos.append('background-color: #E3F2FD; color: #1565C0; font-weight: bold; text-align: left;')
                            else:
                                estilos.append('background-color: white; color: #555; text-align: left; font-weight: 500;')
                        else:
                            val = row[col]
                            if es_cabecera or es_incentivo_cabecera:
                                estilos.append('background-color: #f0f2f6; border-bottom: 2px solid #ddd; border-top: 1px solid #ddd;')
                            elif val == "-":
                                estilos.append('background-color: #fdfdfd; color: #ccc; text-align: center;')
                            else:
                                if es_contacto or es_mail:
                                    try:
                                        if float(str(val).replace('%', '')) >= 80.0: estilos.append('background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: center;')
                                        else: estilos.append('background-color: #FFEBEE; color: #C62828; font-weight: bold; text-align: center;')
                                    except: estilos.append('text-align: center;')
                                elif es_nps:
                                    try:
                                        if float(str(val).replace('%', '')) >= 88.5: estilos.append('background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: center;')
                                        else: estilos.append('background-color: #FFEBEE; color: #C62828; font-weight: bold; text-align: center;')
                                    except: estilos.append('text-align: center;')
                                elif es_muestra:
                                    try:
                                        if int(val) >= meta_muestra: estilos.append('background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: center;')
                                        else: estilos.append('background-color: #FFEBEE; color: #C62828; font-weight: bold; text-align: center;')
                                    except: estilos.append('text-align: center;')
                                elif es_driver:
                                    if val == "0.00%": estilos.append('color: #999; text-align: center;')
                                    else: estilos.append('color: #2E7D32; font-weight: bold; text-align: center;')
                                elif es_cant_pat:
                                    estilos.append('color: #333; font-weight: bold; text-align: center;')
                                elif es_fuera_plazo:
                                    if str(val) == "0":
                                        estilos.append('color: #2E7D32; font-weight: bold; text-align: center;')
                                    else:
                                        estilos.append('color: #C62828; font-weight: bold; text-align: center; font-size: 13px;')
                                elif es_techo:
                                    estilos.append('background-color: #FFF8E1; color: #F57F17; font-weight: bold; text-align: right; padding-right: 15px;')
                                elif es_liq_ok:
                                    estilos.append('background-color: #E8F5E9; color: #2E7D32; font-weight: bold; text-align: right; padding-right: 15px;')
                                elif es_liq_ho or es_liq_nps:
                                    estilos.append('background-color: #FFEBEE; color: #C62828; font-weight: bold; text-align: right; padding-right: 15px;')
                                elif es_suma:
                                    estilos.append('background-color: #E3F2FD; color: #1565C0; font-weight: bold; text-align: center;')
                                else:
                                    estilos.append('text-align: center;')
                    return estilos

                df_estilizado = df_umbrales.style.apply(estilar_filas_prima, axis=1)
                
                st.dataframe(
                    df_estilizado, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "Mes": st.column_config.TextColumn(
                            "Concepto / Indicador", 
                            width="medium",
                            help="Techo Máximo (0.40%) | Liquidación Aprobada | Pérdida H.O. | Pérdida NPS"
                        )
                    }
                )

                # ==========================================================
                # 💵 CONTROL DE FLUJO DE CAJA (2° LAS TARJETAS Y EL GRÁFICO)
                # ==========================================================
                st.markdown("---")
                st.markdown("### 💵 Control de Flujo de Caja")
                
                # Selector de meses cobrados
                meses_cobrados_sel = st.multiselect(
                    "Meses cobrados:", 
                    options=meses_nombres, 
                    default=meses_nombres[:5], 
                    key="ms_meses_cobrados_flujo"
                )
                
                # Cálculos de acumulados según lo tildado en el selector
                tot_cobrado = sum(flujo_cobrado[m] for m in meses_cobrados_sel)
                tot_perdido = sum(flujo_perdida[m] for m in meses_cobrados_sel)
                tot_techo_cobrado = sum(flujo_techo[m] for m in meses_cobrados_sel)
                
                pct_alcanzado = (tot_cobrado / tot_techo_cobrado * 100) if tot_techo_cobrado > 0 else 0.0
                
                # PENDIENTE: Meses del año con patentamientos que NO están tildados como cobrados
                meses_pendientes = [m for m in meses_nombres if m not in meses_cobrados_sel]
                tot_pendiente = sum(flujo_cobrado[m] for m in meses_pendientes)
                
                def fmt_kpi(val):
                    return f"${val:,.0f}".replace(",", ".")

                # 4 Tarjetas visuales de KPI
                kc1, kc2, kc3, kc4 = st.columns(4)
                
                with kc1:
                    st.markdown(f"""
                    <div style="background-color: white; border-left: 5px solid #00C853; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
                        <span style="color: #666; font-size: 13px; font-weight: bold;">💰 COBRADO</span><br>
                        <span style="color: #00C853; font-size: 24px; font-weight: 800;">{fmt_kpi(tot_cobrado)}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with kc2:
                    st.markdown(f"""
                    <div style="background-color: white; border-left: 5px solid #D32F2F; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
                        <span style="color: #666; font-size: 13px; font-weight: bold;">💸 PERDIDO</span><br>
                        <span style="color: #D32F2F; font-size: 24px; font-weight: 800;">{fmt_kpi(tot_perdido)}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with kc3:
                    st.markdown(f"""
                    <div style="background-color: white; border-left: 5px solid #651FFF; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
                        <span style="color: #666; font-size: 13px; font-weight: bold;">📊 % ALCANZADO</span><br>
                        <span style="color: #651FFF; font-size: 24px; font-weight: 800;">{pct_alcanzado:.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with kc4:
                    st.markdown(f"""
                    <div style="background-color: white; border-left: 5px solid #2962FF; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
                        <span style="color: #666; font-size: 13px; font-weight: bold;">⏳ PENDIENTE</span><br>
                        <span style="color: #2962FF; font-size: 24px; font-weight: 800;">{fmt_kpi(tot_pendiente)}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Gráfico de Área Evolutiva (Verde alcanzado vs Techo vs Rojo perdida)
                df_grafico = pd.DataFrame({
                    "Mes": meses_nombres,
                    "Alcanzado": [flujo_cobrado[m] for m in meses_nombres],
                    "Máximo": [flujo_techo[m] for m in meses_nombres],
                    "Pérdida": [flujo_perdida[m] for m in meses_nombres]
                })
                
                fig_flujo = go.Figure()
                
                # Área Alcanzado (Verde)
                fig_flujo.add_trace(go.Scatter(
                    x=df_grafico["Mes"], y=df_grafico["Alcanzado"],
                    mode='lines+markers+text',
                    name='$ Alcanzado',
                    line=dict(color='#00C853', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(0, 200, 83, 0.15)',
                    text=[f"${v/1e6:.1f}M" if v > 0 else "" for v in df_grafico["Alcanzado"]],
                    textposition='top center'
                ))
                
                # Línea Máximo Potencial (Punteada Gris)
                fig_flujo.add_trace(go.Scatter(
                    x=df_grafico["Mes"], y=df_grafico["Máximo"],
                    mode='lines',
                    name='$ Máximo',
                    line=dict(color='#90A4AE', width=2, dash='dash')
                ))
                
                # Área Pérdida (Roja)
                fig_flujo.add_trace(go.Scatter(
                    x=df_grafico["Mes"], y=df_grafico["Pérdida"],
                    mode='lines+markers',
                    name='$ Pérdida',
                    line=dict(color='#E53935', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(229, 57, 53, 0.15)'
                ))
                
                fig_flujo.update_layout(
                    height=320,
                    margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    yaxis=dict(showgrid=True, gridcolor='#F5F5F5', tickprefix="$"),
                    xaxis=dict(showgrid=False),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_flujo, use_container_width=True, key="fig_flujo_caja_cierre")
                
            else:
                st.info("No se encontraron datos en la hoja de Prima de Calidad (Enc Roar) o hubo un error al cargar.")
                        
except Exception as e:
    st.error(f"Error en la ejecución del Tablero Integrado: {e}")
