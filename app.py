from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS  # Añade esta línea
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import os
from werkzeug.utils import secure_filename
import numpy as np
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app)  # Añade esta línea para habilitar CORS
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Función para categorizar productos
def categorize_products(productos):
    categorias = {
        "🍔 Burgers": [
            "BURGUER CORSO", "CAÑAHUA BURGER", "CHICKPEA BURGER", "LENTEJA BURGER",
            "MORENA BURGER", "QUINOA BURGER", "TAURUS BURGUER", "MINI BURGER"
        ],
        "🥗 Ensaladas & Bowls": [
            "BUDDHA BOWL", "BUDDHA BOWL PEQUEÑO", "BUFFET DE ENSALADAS",
            "FALAFEL BOWL", "FALAFEL BOWL PEQUEÑO", "JALISCO BOWL", 
            "JALISCO BOWL PEQUEÑO", "MEDITERRANEA BOWL", "MEDITERRANEA BOWL PEQUEÑO"
        ],
        "🍽️ Almuerzos Diarios": [
            "ALMUERZO COMPLETO", "ALMUERZO + BUFFET DE ENSALADAS", "SEGUNDO",
            "SEGUNDO + BUFFET DE ENSALADAS", "SOPA", "ENTRADA"
        ],
        "⭐ Especiales": [
            "SAB. ALMUERZO ESPECIAL COMPLETO", "SAB. ESPECIAL SOPA", 
            "SEGUNDO SABADO ESPECIAL", "SILPANCHO VEGGIE", "PIQUE MACHO",
            "FRICASE AÑO NUEVO", "PICANA NAVIDEÑA", "VEGANCUCHO"
        ],
        "🥤 Bebidas Frías": [
            "AGUA CON GAS", "AGUA CON LIMON", "AGUA SIN GAS", "CITRUS FRESA",
            "FULL CITRUS", "FULL GREEN 780", "JUGO DE TEMPORADA", "COCO", "SKINNY"
        ],
        "☕ Otras Bebidas": [
            "CERVEZA", "CERVEZA CORONA PERSONAL", "CERVEZA S/A PROST LATA",
            "CHUFLAY O MOJITO VASO", "INFUSION DE HIERBAS", "TE", "MENTA",
            "VINO BLANCO TERRUÑO BOTELLA"
        ],
        "🍨 Postres & Helados": [
            "BROWNIES", "HELADO ARTESANAL", "HELADO ARTESANAL CHOCOLATE",
            "PASTEL DE ZANAHORIA", "TIRAMISU", "POSTRE ESPECIAL"
        ],
        "🎯 Combos & Promociones": [
            "COMBO 2x1 TRANCAPECHO HORA VEGGIE FELIZ", "COMBO BURGER 2X1 (SIN PAPAS)",
            "COMBO HAMBURGUESA 3X2", "COMBO TRANCAPECHO", "PROMO 21 SEPTIEMBRE",
            "VEGGIE WING 2X30"
        ],
        "📋 Planes & Mensualidades": [
            "ALMUERZO MENSUAL", "ALMUERZO SEMANAL", "FIT MENSUAL", "SEGUNDO MENSUAL",
            "SEGUNDO SEMANAL", "PLAN MENSUAL 400", "PROMO ALMUERZO SEMANAL"
        ],
        "🔧 Otros": [
            "DESECHABLES 1bs", "DESECHABLES 3bs", "DESECHABLES 5bs", "CONSUMO CORTESIA",
            "PAPAS FRITAS", "PAPITAS C/SALSA BLANCA", "PORCION EXTRA-FALAFEL",
            "PORCION HUEVO", "PORCION CARNE HAMBURGUESA"
        ]
    }
    
    # Crear mapeo de producto a categoría
    producto_categoria = {}
    for categoria, productos_lista in categorias.items():
        for producto in productos_lista:
            producto_categoria[producto] = categoria
    
    # Categorizar productos
    categorias_resultado = []
    for producto in productos:
        categoria = producto_categoria.get(producto, "🔧 Otros")
        categorias_resultado.append(categoria)
    
    return categorias_resultado

# Variable global para almacenar los datos
data = None

def process_data(df):
    """Procesar los datos para análisis"""
    global data
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.upper()
    
    # Renombrar columnas si es necesario
    column_mapping = {
        'L A D': 'DIA_SEMANA',
        'L_A_D': 'DIA_SEMANA'
    }
    df = df.rename(columns=column_mapping)
    
    # Agregar categorías
    df['CATEGORIA'] = categorize_products(df['PRODUCTO'].tolist())
    
    # Convertir tipos de datos
    df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
    df['CANTIDAD'] = pd.to_numeric(df['CANTIDAD'], errors='coerce')
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')
    df['YEAR'] = pd.to_numeric(df['YEAR'], errors='coerce')
    df['MONTH'] = pd.to_numeric(df['MONTH'], errors='coerce')
    df['DIA_SEMANA'] = pd.to_numeric(df['DIA_SEMANA'], errors='coerce')
    
    # Mapear días de la semana
    dias_semana = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 
                   5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
    df['DIA_NOMBRE'] = df['DIA_SEMANA'].map(dias_semana)
    
    # Mapear meses
    meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
             7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    df['MES_NOMBRE'] = df['MONTH'].map(meses)
    
    # Eliminar filas con valores nulos críticos
    df = df.dropna(subset=['CANTIDAD', 'VALOR'])
    
    data = df
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.lower().endswith(('.xlsx', '.xls')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Leer archivo Excel
            df = pd.read_excel(filepath)
            
            # Procesar datos
            df = process_data(df)
            
            return jsonify({
                'success': True,
                'message': f'Archivo procesado exitosamente. {len(df)} registros cargados.',
                'redirect': url_for('dashboard')
            })
            
        except Exception as e:
            return jsonify({'error': f'Error procesando archivo: {str(e)}'}), 500
    
    return jsonify({'error': 'Por favor sube un archivo Excel (.xlsx o .xls)'}), 400

@app.route('/dashboard')
def dashboard():
    global data
    if data is None:
        return redirect(url_for('index'))
    
    # Obtener valores únicos para los filtros
    categorias = sorted(data['CATEGORIA'].unique().tolist())
    productos_por_categoria = {}
    for categoria in categorias:
        productos_por_categoria[categoria] = sorted(data[data['CATEGORIA'] == categoria]['PRODUCTO'].unique().tolist())
    
    years = sorted(data['YEAR'].unique().tolist())
    months = list(range(1, 13))
    dias = list(range(1, 8))
    
    return render_template('dashboard.html', 
                         categorias=categorias,
                         productos_por_categoria=productos_por_categoria,
                         years=years,
                         months=months,
                         dias=dias)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/data')
def get_data():
    global data
    try:
        app.logger.info("Accediendo a /api/data")
        
        if data is None or data.empty:
            app.logger.error("No hay datos cargados o DataFrame está vacío")
            return jsonify({'error': 'No hay datos cargados. Por favor sube un archivo primero.'}), 400
        
        app.logger.info(f"Filtros recibidos: {request.args}")
        
        # Obtener filtros
        categorias_filter = request.args.getlist('categorias[]')
        productos_filter = request.args.getlist('productos[]')
        years_filter = request.args.getlist('years[]')
        months_filter = request.args.getlist('months[]')
        dias_filter = request.args.getlist('dias[]')
        
        app.logger.info(f"Filtros aplicados - Categorías: {categorias_filter}, Productos: {productos_filter}")
        
        # Filtrar datos
        df_filtered = data.copy()
        
        if categorias_filter:
            df_filtered = df_filtered[df_filtered['CATEGORIA'].isin(categorias_filter)]
        if productos_filter:
            df_filtered = df_filtered[df_filtered['PRODUCTO'].isin(productos_filter)]
        if years_filter:
            df_filtered = df_filtered[df_filtered['YEAR'].astype(str).isin(years_filter)]
        if months_filter:
            df_filtered = df_filtered[df_filtered['MONTH'].astype(str).isin(months_filter)]
        if dias_filter:
            df_filtered = df_filtered[df_filtered['DIA_SEMANA'].astype(str).isin(dias_filter)]
        
        app.logger.info(f"Datos después de filtrar: {len(df_filtered)} registros")
        
        # Generar gráficos
        graphs = generate_graphs(df_filtered)
        
        app.logger.info("Gráficos generados exitosamente")
        return jsonify(graphs)
        
    except Exception as e:
        app.logger.error(f"Error en /api/data: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

def generate_graphs(df):
    """Generar todos los gráficos con los datos filtrados"""
    graphs = {}
    
    # KPIs principales
    total_ventas = df['VALOR'].sum()
    total_cantidad = df['CANTIDAD'].sum()
    promedio_ticket = total_ventas / len(df) if len(df) > 0 else 0
    productos_unicos = df['PRODUCTO'].nunique()
    
    graphs['kpis'] = {
        'total_ventas': f"Bs. {total_ventas:,.2f}",
        'total_cantidad': f"{total_cantidad:,.0f}",
        'promedio_ticket': f"Bs. {promedio_ticket:.2f}",
        'productos_unicos': f"{productos_unicos}"
    }

    try:
        # 1. Ventas por categoría
        ventas_categoria = df.groupby('CATEGORIA').agg({'VALOR': 'sum'}).reset_index()
        fig1 = px.pie(ventas_categoria, values='VALOR', names='CATEGORIA',
                     title='Distribución de Ventas por Categoría')
        fig1.update_traces(textposition='inside', textinfo='percent+label')
        graphs['ventas_categoria'] = json.dumps(fig1, cls=PlotlyJSONEncoder)

        # 2. Top 10 productos más vendidos
        top_productos = df.groupby('PRODUCTO')['VALOR'].sum().nlargest(10).reset_index()
        fig2 = px.bar(top_productos, x='VALOR', y='PRODUCTO', orientation='h',
                     title='Top 10 Productos por Ventas',
                     labels={'VALOR': 'Ventas (Bs.)', 'PRODUCTO': 'Producto'})
        fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
        graphs['top_productos'] = json.dumps(fig2, cls=PlotlyJSONEncoder)

        # 3. Evolución de ventas mensuales
        ventas_mes = df.groupby(['YEAR', 'MONTH', 'MES_NOMBRE'])['VALOR'].sum().reset_index()
        ventas_mes['PERIODO'] = ventas_mes['MES_NOMBRE'] + ' ' + ventas_mes['YEAR'].astype(str)
        fig3 = px.line(ventas_mes, x='PERIODO', y='VALOR',
                      title='Evolución de Ventas Mensuales',
                      labels={'VALOR': 'Ventas (Bs.)', 'PERIODO': 'Período'})
        fig3.update_layout(xaxis={'tickangle': 45})  # Cambiado de update_xaxis a update_layout
        graphs['ventas_mensuales'] = json.dumps(fig3, cls=PlotlyJSONEncoder)
    
        # 4. Ventas por día de la semana
        ventas_dia = df.groupby(['DIA_SEMANA', 'DIA_NOMBRE']).agg({
            'VALOR': 'sum',
            'CANTIDAD': 'sum'
        }).reset_index().sort_values('DIA_SEMANA')
        
        fig4 = px.bar(ventas_dia, x='DIA_NOMBRE', y='VALOR',
                    title='Ventas por Día de la Semana',
                    labels={'VALOR': 'Ventas (Bs.)', 'DIA_NOMBRE': 'Día'})
        graphs['ventas_dia_semana'] = json.dumps(fig4, cls=PlotlyJSONEncoder)
        
        # 5. Heatmap de ventas por mes y día
        if len(df) > 0:
            heatmap_data = df.groupby(['MONTH', 'DIA_SEMANA'])['VALOR'].sum().reset_index()
            heatmap_pivot = heatmap_data.pivot(index='MONTH', columns='DIA_SEMANA', values='VALOR').fillna(0)
            
            # Renombrar índices y columnas
            meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
            dias = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 7: 'Dom'}
            
            heatmap_pivot.index = [meses.get(i, str(i)) for i in heatmap_pivot.index]
            heatmap_pivot.columns = [dias.get(i, str(i)) for i in heatmap_pivot.columns]
            
            fig5 = px.imshow(heatmap_pivot, 
                            title='Heatmap: Ventas por Mes y Día de la Semana',
                            labels=dict(x="Día de la Semana", y="Mes", color="Ventas (Bs.)"),
                            aspect="auto")
            graphs['heatmap_ventas'] = json.dumps(fig5, cls=PlotlyJSONEncoder)
        
        # 6. Comparación cantidad vs valor por categoría
        categoria_stats = df.groupby('CATEGORIA').agg({
            'VALOR': 'sum',
            'CANTIDAD': 'sum'
        }).reset_index()
        
        fig6 = px.scatter(categoria_stats, x='CANTIDAD', y='VALOR', 
                        size='VALOR', color='CATEGORIA',
                        title='Relación Cantidad vs Valor por Categoría',
                        labels={'CANTIDAD': 'Cantidad Total', 'VALOR': 'Valor Total (Bs.)'})
        graphs['cantidad_vs_valor'] = json.dumps(fig6, cls=PlotlyJSONEncoder)
    
    except Exception as e:
        app.logger.error(f"Error generando gráficos: {str(e)}")
        graphs['error'] = f"Error generando gráficos: {str(e)}"
    
    return graphs

if __name__ == '__main__':
    app.run(debug=True)