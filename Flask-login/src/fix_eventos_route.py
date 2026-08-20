#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para agregar filtros a la ruta de eventos"""

import re

# Leer el archivo app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar y reemplazar la ruta de /eventos
old_route = """@app.route('/eventos')
@login_required
def ver_eventos():
    eventos = get_events_from_db()
   
    if not eventos:
        eventos = [{
            'id': 1,
            'titulo': 'Concierto de Rock',
            'fecha': '2026-07-15',
            'hora': '20:00',
            'descripcion': 'Una noche increíble con las mejores bandas locales.',
            'lugar': 'Estadio Principal',
            'capacidad_maxima': 200
        }]

    usuario_display = getattr(current_user, 'username', None) or getattr(current_user, 'email', '')
    return render_template('eventos.html', eventos=eventos, usuario=usuario_display)"""

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

if old_route in content:
    content = content.replace(old_route, new_route)
    print("✓ Ruta /eventos actualizada correctamente")
else:
    print("✗ No se encontró la ruta /eventos para reemplazar")
    exit(1)

# Escribir el archivo modificado
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Archivo app.py actualizado")
