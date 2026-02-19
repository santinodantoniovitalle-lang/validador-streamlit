import streamlit as st
import pandas as pd
import re
import unicodedata
from urllib.parse import unquote
import io

st.set_page_config(page_title="Validador de Base", layout="wide")

# =====================================================
# CONFIGURACIÓN
# =====================================================

PREFIJOS = {
    "MX": "52",
    "CL": "56", 
    "PE": "51",
    "PA": "507"
}

PAISES_VALIDOS = list(PREFIJOS.keys())

MAPEO_PAISES = {
    "mexico": "MX", "méxico": "MX", "mx": "MX",
    "chile": "CL", "cl": "CL",
    "peru": "PE", "perú": "PE", "pe": "PE",
    "panama": "PA", "panamá": "PA", "pa": "PA"
}

PALABRAS_INVALIDAS = [
    "test", "prueba", "xxx", "null", "none", "n/a", "asdf", "xxxx", "123"
]

# =====================================================
# FUNCIONES ORIGINALES
# =====================================================

def buscar_columna(df, aliases):
    """Busca columna por nombres alternativos"""
    for col in df.columns:
        if col.lower().strip() in aliases:
            return col
    return None

def limpiar_texto(txt):
    """Limpieza completa de texto (versión original)"""
    if pd.isna(txt):
        return txt
    txt = unquote(str(txt))
    txt = unicodedata.normalize("NFC", txt)
    txt = re.sub(r"[^a-zA-ZÀ-ÿ\s@._-]", "", txt)
    return txt.strip()

def normalizar_nombre(txt):
    """Normaliza nombres a título (versión original)"""
    if pd.isna(txt):
        return txt
    return limpiar_texto(txt).title()

def email_valido(email):
    """Validación estricta de email"""
    if pd.isna(email):
        return False
    patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(patron, str(email)) is not None

def nombre_valido(nombre):
    """Validación estricta de nombre"""
    if pd.isna(nombre):
        return False
    nombre = str(nombre)
    if len(nombre) < 2:
        return False
    if re.search(r"\d", nombre):
        return False
    return not any(b in nombre.lower() for b in PALABRAS_INVALIDAS)

def telefono_falso(num):
    """Detecta teléfonos falsos (repetitivos)"""
    if pd.isna(num):
        return True
    num = str(num)
    return len(set(num)) == 1 or num in ["123456789", "987654321"]

def normalizar_pais(p):
    """Normaliza nombres de países"""
    if pd.isna(p):
        return None
    p = limpiar_texto(str(p)).lower()
    return MAPEO_PAISES.get(p, None)

# =====================================================
# INTERFAZ
# =====================================================

st.title("Validador de Base de Datos")

archivo = st.file_uploader("Sube archivo Excel o CSV")

if archivo:
    # Cargar archivo
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo, dtype=str)
    else:
        df = pd.read_excel(archivo, dtype=str)
    
    st.success(f"Registros cargados: {len(df)}")
    
    # Detección automática de columnas
    columnas = df.columns.tolist()
    
    # Buscar columnas por nombres alternativos
    phone_options = ["phone", "telefono", "celular", "movil", "mobile"]
    country_options = ["country", "pais"]
    name_options = ["customerfirstname", "firstname", "nombre", "name"]
    last_options = ["customerlastname", "lastname", "apellido"]
    email_options = ["email", "correo", "mail"]
    
    phone_col = buscar_columna(df, phone_options)
    country_col = buscar_columna(df, country_options)
    name_col = buscar_columna(df, name_options)
    last_col = buscar_columna(df, last_options)
    email_col = buscar_columna(df, email_options)
    
    # Mostrar columnas detectadas
    st.info("Columnas detectadas automáticamente (puedes cambiarlas abajo)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name_col = st.selectbox("Columna Nombre", columnas, 
                               index=columnas.index(name_col) if name_col and name_col in columnas else 0)
        last_col = st.selectbox("Columna Apellido", columnas,
                               index=columnas.index(last_col) if last_col and last_col in columnas else 0)
        email_col = st.selectbox("Columna Email", columnas,
                                index=columnas.index(email_col) if email_col and email_col in columnas else 0)
    
    with col2:
        phone_col = st.selectbox("Columna Teléfono", columnas,
                                index=columnas.index(phone_col) if phone_col and phone_col in columnas else 0)
        country_col = st.selectbox("Columna País", columnas,
                                  index=columnas.index(country_col) if country_col and country_col in columnas else 0)
    
    if st.button("VALIDAR BASE"):
        df_original = df.copy()
        df_procesado = df.copy()
        resultados = []
        descartados = []
        
        # DataFrame para guardar registros descartados con su razón
        df_descartados = pd.DataFrame()
        
        # 1. Limpieza de texto
        for col in [name_col, last_col, email_col, country_col]:
            if col and col in df_procesado.columns:
                df_procesado[col] = df_procesado[col].apply(limpiar_texto)
        
        if name_col and name_col in df_procesado.columns:
            df_procesado[name_col] = df_procesado[name_col].apply(normalizar_nombre)
        if last_col and last_col in df_procesado.columns:
            df_procesado[last_col] = df_procesado[last_col].apply(normalizar_nombre)
        
        # 2. Validación de nombres
        if name_col and name_col in df_procesado.columns:
            antes = len(df_procesado)
            mask_validos = df_procesado[name_col].apply(nombre_valido)
            mask_descartados = ~mask_validos
            
            # Guardar descartados
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Nombre inválido"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_validos]
            resultados.append(f"Nombres válidos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 3. Validación de apellidos
        if last_col and last_col in df_procesado.columns:
            antes = len(df_procesado)
            mask_validos = df_procesado[last_col].apply(nombre_valido)
            mask_descartados = ~mask_validos
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Apellido inválido"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_validos]
            resultados.append(f"Apellidos válidos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 4. Validación de emails
        if email_col and email_col in df_procesado.columns:
            antes = len(df_procesado)
            mask_validos = df_procesado[email_col].apply(email_valido)
            mask_descartados = ~mask_validos
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Email inválido"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_validos]
            resultados.append(f"Emails válidos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 5. Procesamiento de teléfonos
        if phone_col and phone_col in df_procesado.columns:
            # Eliminar nulos
            antes = len(df_procesado)
            mask_no_nulos = df_procesado[phone_col].notna()
            mask_nulos = ~mask_no_nulos
            
            if mask_nulos.any():
                temp_desc = df_procesado[mask_nulos].copy()
                temp_desc["razon_descarte"] = "Teléfono nulo"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_no_nulos]
            resultados.append(f"Teléfonos no nulos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
            
            # Limpiar dígitos
            df_procesado[phone_col] = df_procesado[phone_col].astype(str).str.replace(r"\D", "", regex=True)
            
            # Validar longitud básica (SIN prefijo)
            antes = len(df_procesado)
            mask_longitud = (df_procesado[phone_col].str.len() >= 8) & (df_procesado[phone_col].str.len() <= 12)
            mask_descartados = ~mask_longitud
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Teléfono longitud incorrecta (debe ser 8-12 dígitos)"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_longitud]
            resultados.append(f"Teléfonos longitud básica: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
            
            # Eliminar terminados en 00000
            antes = len(df_procesado)
            mask_no_00000 = ~df_procesado[phone_col].str.endswith("00000", na=False)
            mask_descartados = ~mask_no_00000
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Teléfono termina en 00000"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_no_00000]
            resultados.append(f"Sin terminación 00000: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
            
            # Eliminar falsos
            antes = len(df_procesado)
            mask_no_falsos = ~df_procesado[phone_col].apply(telefono_falso)
            mask_descartados = ~mask_no_falsos
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "Teléfono falso (repetitivo)"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_no_falsos]
            resultados.append(f"Sin teléfonos falsos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 6. Normalizar países
        if country_col and country_col in df_procesado.columns:
            df_procesado["pais_norm"] = df_procesado[country_col].apply(normalizar_pais)
            
            antes = len(df_procesado)
            mask_pais_valido = df_procesado["pais_norm"].isin(PAISES_VALIDOS)
            mask_descartados = ~mask_pais_valido
            
            if mask_descartados.any():
                temp_desc = df_procesado[mask_descartados].copy()
                temp_desc["razon_descarte"] = "País no válido (solo MX, CL, PE, PA)"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado[mask_pais_valido]
            resultados.append(f"Países válidos: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
            
            # Agregar prefijos y validar longitud final
            if phone_col and phone_col in df_procesado.columns:
                def procesar_telefono(row):
                    phone = row[phone_col]
                    country = row["pais_norm"]
                    pref = PREFIJOS.get(country, "")
                    
                    # Agregar prefijo si no lo tiene
                    if pref and not phone.startswith(pref):
                        phone_con_prefijo = pref + phone
                    else:
                        phone_con_prefijo = phone
                    
                    # Validar longitud según país
                    if country == "PA":  # Panamá usa prefijo 507 (3 dígitos)
                        if 11 <= len(phone_con_prefijo) <= 15:
                            return phone_con_prefijo
                    else:  # MX, CL, PE (prefijo 2 dígitos)
                        if 10 <= len(phone_con_prefijo) <= 14:
                            return phone_con_prefijo
                    
                    return None  # No pasa validación
                
                antes = len(df_procesado)
                df_procesado["telefono_temp"] = df_procesado.apply(procesar_telefono, axis=1)
                mask_telefono_valido = df_procesado["telefono_temp"].notna()
                mask_descartados = ~mask_telefono_valido
                
                if mask_descartados.any():
                    temp_desc = df_procesado[mask_descartados].copy()
                    temp_desc["razon_descarte"] = "Teléfono con prefijo - longitud final incorrecta"
                    df_descartados = pd.concat([df_descartados, temp_desc])
                
                df_procesado = df_procesado[mask_telefono_valido]
                df_procesado["telefono_final"] = df_procesado["telefono_temp"]
                df_procesado = df_procesado.drop("telefono_temp", axis=1)
                resultados.append(f"Teléfonos con prefijo válido: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 7. Eliminar duplicados
        if phone_col and phone_col in df_procesado.columns:
            antes = len(df_procesado)
            # Identificar duplicados antes de eliminarlos
            duplicados_telefono = df_procesado[df_procesado.duplicated(subset=[phone_col], keep=False)]
            if not duplicados_telefono.empty:
                temp_desc = duplicados_telefono.copy()
                temp_desc["razon_descarte"] = "Teléfono duplicado"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado.drop_duplicates(subset=[phone_col])
            resultados.append(f"Sin duplicados por teléfono: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        if email_col and email_col in df_procesado.columns:
            antes = len(df_procesado)
            # Identificar duplicados antes de eliminarlos
            duplicados_email = df_procesado[df_procesado.duplicated(subset=[email_col], keep=False)]
            if not duplicados_email.empty:
                temp_desc = duplicados_email.copy()
                temp_desc["razon_descarte"] = "Email duplicado"
                df_descartados = pd.concat([df_descartados, temp_desc])
            
            df_procesado = df_procesado.drop_duplicates(subset=[email_col])
            resultados.append(f"Sin duplicados por email: {len(df_procesado)} (eliminados: {antes-len(df_procesado)})")
        
        # 8. Crear nombre completo
        if name_col and last_col and name_col in df_procesado.columns and last_col in df_procesado.columns:
            df_procesado["Nombre Completo"] = (
                df_procesado[name_col].astype(str).str.strip() + 
                " " + 
                df_procesado[last_col].astype(str).str.strip()
            )
        
        # Eliminar duplicados en descartados (por si un registro fue descartado por múltiples razones)
        if not df_descartados.empty:
            df_descartados = df_descartados.drop_duplicates(subset=df_original.columns.tolist())
        
        # Mostrar resultados
        st.success(f"✅ BASE FINAL: {len(df_procesado)} registros")
        st.warning(f"⚠️ Registros descartados: {len(df_descartados)}")
        
        # Pestañas para mostrar válidos y descartados
        tab1, tab2 = st.tabs(["✅ Registros Válidos", "❌ Registros Descartados"])
        
        with tab1:
            st.dataframe(df_procesado.head(100))
            st.caption(f"Mostrando 100 de {len(df_procesado)} registros válidos")
        
        with tab2:
            if not df_descartados.empty:
                st.dataframe(df_descartados.head(100))
                st.caption(f"Mostrando 100 de {len(df_descartados)} registros descartados")
                
                # Mostrar resumen de razones de descarte
                st.subheader("📊 Resumen de descartes por razón")
                razones = df_descartados["razon_descarte"].value_counts().reset_index()
                razones.columns = ["Razón de descarte", "Cantidad"]
                st.dataframe(razones)
            else:
                st.info("No hay registros descartados")
        
        with st.expander("Ver detalles del proceso"):
            for resultado in resultados:
                st.write(resultado)
        
        # Botones de descarga
        col1, col2 = st.columns(2)
        
        with col1:
            # Descargar válidos en Excel
            output_validos = io.BytesIO()
            with pd.ExcelWriter(output_validos, engine='openpyxl') as writer:
                df_procesado.to_excel(writer, index=False, sheet_name='Base Limpia')
            output_validos.seek(0)
            
            st.download_button(
                "📥 Descargar registros VÁLIDOS (Excel)",
                output_validos,
                "base_valida.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Descargar descartados en Excel
            if not df_descartados.empty:
                output_descartados = io.BytesIO()
                with pd.ExcelWriter(output_descartados, engine='openpyxl') as writer:
                    df_descartados.to_excel(writer, index=False, sheet_name='Descartados')
                output_descartados.seek(0)
                
                st.download_button(
                    "📥 Descargar registros DESCARTADOS (Excel)",
                    output_descartados,
                    "base_descartados.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        st.balloons()
