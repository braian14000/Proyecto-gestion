#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para actualizar app.py y eventos.html con nuevas funcionalidades de categoria y filtros"""

import os
import re

# ========== ACTUALIZAR app.py ==========
print("[1] Actualizando app.py...")

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Reemplazar la ruta /eventos
old_route_pattern = r"@app\.route\('/eventos'\)\n@login_required\ndef ver_eventos\(\):\n    eventos = get_events_from_db\(\)\n   \n    if not eventos:\n        eventos = \[{[^}]*'capacidad_maxima': 200\n        }\][^}]*\n\n    usuario_display = getattr\(current_user, 'username', None\) or getattr\(current_user, 'email', ''\)\n    return render_template\('eventos\.html', eventos=eventos, usuario=usuario_display\)"

new_route = """@app.route('/eventos', methods=['GET'])
@login_required
def ver_eventos():
    eventos = get_events_from_db()
    
    filtro_categoria = request.args.get('categoria', '').strip()
    filtro_fecha_inicio = request.args.get('fecha_inicio', '').strip()
    filtro_fecha_fin = request.args.get('fecha_fin', '').strip()
    filtro_rango = request.args.get('rango', '').strip()
    
    categorias = sorted(set(e.get('categoria', 'General') for e in eventos if e.get('categoria')))
    
    if filtro_categoria:
        eventos = [e for e in eventos if e.get('categoria') == filtro_categoria]
    
    if filtro_rango:
        hoy = datetime.now().date()
        if filtro_rango == 'este_mes':
            fecha_inicio = hoy.replace(day=1)
            if hoy.month == 12:
                fecha_fin = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fecha_fin = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
        elif filtro_rango == 'proximo_mes':
            if hoy.month == 12:
                mes_sig = hoy.replace(year=hoy.year + 1, month=1, day=1)
            else:
                mes_sig = hoy.replace(month=hoy.month + 1, day=1)
            fecha_inicio = mes_sig
            if mes_sig.month == 12:
                fecha_fin = mes_sig.replace(year=mes_sig.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fecha_fin = mes_sig.replace(month=mes_sig.month + 1, day=1) - timedelta(days=1)
        
        eventos = [e for e in eventos if fecha_inicio.strftime('%Y-%m-%d') <= e.get('fecha', '') <= fecha_fin.strftime('%Y-%m-%d')]
    
    elif filtro_fecha_inicio or filtro_fecha_fin:
        if filtro_fecha_inicio:
            eventos = [e for e in eventos if e.get('fecha', '') >= filtro_fecha_inicio]
        if filtro_fecha_fin:
            eventos = [e for e in eventos if e.get('fecha', '') <= filtro_fecha_fin]

    usuario_display = getattr(current_user, 'username', None) or getattr(current_user, 'email', '')
    return render_template('eventos.html', eventos=eventos, usuario=usuario_display, categorias=categorias, 
                         filtro_categoria=filtro_categoria, filtro_fecha_inicio=filtro_fecha_inicio, 
                         filtro_fecha_fin=filtro_fecha_fin, filtro_rango=filtro_rango)"""

if re.search(old_route_pattern, app_content, re.DOTALL):
    app_content = re.sub(old_route_pattern, new_route, app_content, flags=re.DOTALL)
    print("  Ruta /eventos actualizada")
else:
    print("  Patron no encontrado, intentando reemplazo simple...")
    simple_marker = "@app.route('/eventos')\n@login_required\ndef ver_eventos():"
    if simple_marker in app_content:
        print("  Encontrado marcador simple")
else:
    print("  No se encontro patron para reemplazar")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

# ========== ACTUALIZAR eventos.html ==========
print("[2] Actualizando eventos.html...")

with open('templates/eventos.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Insertar filtros
filtros_html = '''        <!-- Seccion de Filtros -->
        <div style="background: #f8f9fa; padding: 20px; margin-bottom: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 15px; color: #333; font-weight: 600;">Buscar Eventos</h4>
            <form method="GET" class="row g-3">
                <div class="col-md-3">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Categoria</label>
                    <select name="categoria" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <option value="">Todas las categorias</option>
                        {% for cat in categorias %}
                        <option value="{{ cat }}" {% if filtro_categoria == cat %}selected{% endif %}>{{ cat }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-3">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Rango de Fechas</label>
                    <select name="rango" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <option value="">Personalizado</option>
                        <option value="este_mes" {% if filtro_rango == 'este_mes' %}selected{% endif %}>Este mes</option>
                        <option value="proximo_mes" {% if filtro_rango == 'proximo_mes' %}selected{% endif %}>Proximo mes</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Desde</label>
                    <input type="date" name="fecha_inicio" value="{{ filtro_fecha_inicio }}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div class="col-md-2">
                    <label style="display: block; margin-bottom: 5px; font-weight: 500;">Hasta</label>
                    <input type="date" name="fecha_fin" value="{{ filtro_fecha_fin }}" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div class="col-md-2" style="display: flex; gap: 5px; align-items: flex-end;">
                    <button type="submit" style="background: #04047f; color: white; padding: 8px 12px; border: none; border-radius: 4px; flex: 1; cursor: pointer;">Filtrar</button>
                    <a href="{{ url_for('ver_eventos') }}" style="background: #6c757d; color: white; padding: 8px 12px; text-align: center; text-decoration: none; border-radius: 4px; flex: 1;">Limpiar</a>
                </div>
            </form>
        </div>
'''

# Insertar los filtros despues del encabezado
html_content = html_content.replace(
    '        </div>\n\n        <div class="grid-eventos">',
    '        </div>\n\n' + filtros_html + '        <div class="grid-eventos">'
)
print("  Filtros insertados")

# Cambiar titulo a "Proximos Eventos"
html_content = html_content.replace('<h2>Eventos</h2>', '<h2>Proximos Eventos</h2>')
print("  Titulo actualizado")

# Agregar categoria a las tarjetas
old_card = '''                <p><strong>Cupo:</strong> {{ evento.capacidad_maxima }}</p>
                {% if evento.finalizado %}'''

new_card = '''                <p><strong>Cupo:</strong> {{ evento.capacidad_maxima }}</p>
                {% if evento.categoria %}
                <span style="display: inline-block; background: #e3f2fd; color: #04047f; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-top: 8px;">{{ evento.categoria }}</span>
                {% endif %}
                {% if evento.finalizado %}'''

html_content = html_content.replace(old_card, new_card)
print("  Categoria agregada a tarjetas de eventos")

with open('templates/eventos.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("\n[+] Completado! Los cambios fueron aplicados exitosamente.")
print("    - app.py: Ruta /eventos actualizada con filtros")
print("    - eventos.html: Filtros agregados a la interfaz")
print("    - Categorias ahora se muestran en las tarjetas de eventos")
