#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para actualizar la plantilla eventos.html con filtros"""

# Leer el archivo eventos.html
with open('templates/eventos.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Insertar filtros despues del encabezado
filtros_html = '''        <!-- Seccion de Filtros -->
        <div style="background: #f8f9fa; padding: 20px; margin-bottom: 20px; border-radius: 8px;">
            <h4 style="margin-bottom: 15px; color: #333;">Buscar Eventos</h4>
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
                    <a href="{{ url_for('ver_eventos') }}" style="background: #6c757d; color: white; padding: 8px 12px; text-align: center; text-decoration: none; border-radius: 4px; flex: 1; cursor: pointer;">Limpiar</a>
                </div>
            </form>
        </div>
'''

# Encontrar donde insertar los filtros (despues del encabezado)
marker = '</div>\n\n        <div class="grid-eventos">'
if marker in content:
    content = content.replace(
        '</div>\n\n        <div class="grid-eventos">',
        '</div>\n\n' + filtros_html + '\n        <div class="grid-eventos">'
    )
    print("Filtros agregados a eventos.html")
else:
    print("No se encontro marcador para insertar filtros")

# Agregar categoria a las tarjetas de eventos
old_evento_card = '''                <p><strong>Cupo:</strong> {{ evento.capacidad_maxima }}</p>
                {% if evento.finalizado %}'''

new_evento_card = '''                <p><strong>Cupo:</strong> {{ evento.capacidad_maxima }}</p>
                {% if evento.categoria %}
                <span style="display: inline-block; background: #e3f2fd; color: #04047f; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-top: 8px;">{{ evento.categoria }}</span>
                {% endif %}
                {% if evento.finalizado %}'''

if old_evento_card in content:
    content = content.replace(old_evento_card, new_evento_card)
    print("Categoria agregada a tarjetas de eventos")
else:
    print("No se encontro marcador para agregar categoria")

# Actualizar h2 titulo
content = content.replace('<h2>Eventos</h2>', '<h2>Proximos Eventos</h2>')

# Escribir el archivo modificado
with open('templates/eventos.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("eventos.html actualizado correctamente!")
