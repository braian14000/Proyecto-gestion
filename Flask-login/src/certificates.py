from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime


def generar_certificado(nombre, apellido, dni, evento):
    """Genera un certificado en PNG desde cero con diseño más completo."""
    base_dir = os.path.dirname(__file__)
    salida_dir = os.path.join(base_dir, 'static', 'certificados')
    logo_path = os.path.join(base_dir, 'static', 'img', 'LogoUTN_Gestion_De_Eventos.png')

    if not os.path.exists(salida_dir):
        os.makedirs(salida_dir, exist_ok=True)

    ancho = 1000
    alto = 700
    imagen = Image.new('RGB', (ancho, alto), color='#F8FAFB')
    draw = ImageDraw.Draw(imagen)

    def cargar_fuente(tamano, bold=False):
        fuentes = [
            os.path.join(base_dir, 'static', 'fuentes', 'arialbd.ttf'),
            os.path.join(base_dir, 'static', 'fuentes', 'arial.ttf'),
            '/Windows/Fonts/arialbd.ttf' if bold else '/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        ]
        for fuente in fuentes:
            try:
                return ImageFont.truetype(fuente, tamano)
            except Exception:
                continue
        return ImageFont.load_default()

    fuente_titulo = cargar_fuente(52, bold=True)
    fuente_subtitulo = cargar_fuente(26)
    fuente_nombre = cargar_fuente(52, bold=True)
    fuente_texto = cargar_fuente(28)
    fuente_pie = cargar_fuente(22)

    accent_dark = (9, 94, 128)
    accent_light = (38, 168, 182)
    accent_soft = (223, 241, 247)

    # Fondo superior con detalles y panel de logo
    draw.rectangle([0, 0, ancho, 175], fill=accent_light)
    draw.rectangle([0, 170, ancho, 185], fill=accent_soft)

    # Logo arriba al centro si existe
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert('RGBA')
            logo_w = 180
            logo_h = int(logo.height * (logo_w / logo.width))
            if logo_h > 110:
                logo_h = 110
            logo = logo.resize((logo_w, logo_h), Image.ANTIALIAS)
            logo_x = (ancho - logo_w) // 2
            logo_y = 20
            imagen.paste(logo, (logo_x, logo_y), logo)
        except Exception:
            pass

    # Etiqueta superior debajo del logo
    label = "CERTIFICADO DE ASISTENCIA"
    bbox_label = draw.textbbox((0, 0), label, font=fuente_titulo)
    x_label = (ancho - (bbox_label[2] - bbox_label[0])) // 2
    y_label = 190
    draw.text((x_label, y_label), label, fill=accent_dark, font=fuente_titulo)

    # Texto de apoyo
    subtitulo = "CONCEDIDO CON ORGULLO A"
    bbox_sub = draw.textbbox((0, 0), subtitulo, font=fuente_subtitulo)
    x_sub = (ancho - (bbox_sub[2] - bbox_sub[0])) // 2
    y_sub = y_label + 70
    draw.text((x_sub, y_sub), subtitulo, fill=accent_dark, font=fuente_subtitulo)

    # Nombre del asistente
    nombre_completo = f"{nombre} {apellido}".strip()
    bbox_nombre = draw.textbbox((0, 0), nombre_completo, font=fuente_nombre)
    x_nombre = (ancho - (bbox_nombre[2] - bbox_nombre[0])) // 2
    y_nombre = y_sub + 60
    draw.text((x_nombre, y_nombre), nombre_completo, fill=accent_dark, font=fuente_nombre)

    # Línea de separación
    y_sep = y_nombre + 70
    draw.line([(150, y_sep), (ancho - 150, y_sep)], fill=accent_light, width=4)

    # Descripción del evento
    texto_ayuda = "Por haber asistido al evento"
    bbox_ayuda = draw.textbbox((0, 0), texto_ayuda, font=fuente_texto)
    x_ayuda = (ancho - (bbox_ayuda[2] - bbox_ayuda[0])) // 2
    y_ayuda = y_sep + 30
    draw.text((x_ayuda, y_ayuda), texto_ayuda, fill=accent_dark, font=fuente_texto)

    # Nombre del evento en un recuadro blanco
    evento_str = str(evento)
    caja_x0 = 140
    caja_x1 = ancho - 140
    caja_y0 = y_ayuda + 50
    caja_y1 = caja_y0 + 120
    draw.rectangle([caja_x0, caja_y0, caja_x1, caja_y1], fill='white', outline=accent_light, width=2)

    # Texto del evento con wrapping
    max_width = caja_x1 - caja_x0 - 40
    palabras = evento_str.split(' ')
    line = ''
    y_text = caja_y0 + 20
    for palabra in palabras:
        prueba = f"{line} {palabra}".strip()
        bbox_prueba = draw.textbbox((0, 0), prueba, font=fuente_texto)
        if bbox_prueba[2] - bbox_prueba[0] <= max_width:
            line = prueba
        else:
            x_line = caja_x0 + (max_width - (draw.textbbox((0, 0), line, font=fuente_texto)[2] - draw.textbbox((0, 0), line, font=fuente_texto)[0])) // 2 + 20
            draw.text((x_line, y_text), line, fill=accent_dark, font=fuente_texto)
            y_text += 36
            line = palabra
    if line:
        x_line = caja_x0 + (max_width - (draw.textbbox((0, 0), line, font=fuente_texto)[2] - draw.textbbox((0, 0), line, font=fuente_texto)[0])) // 2 + 20
        draw.text((x_line, y_text), line, fill=accent_dark, font=fuente_texto)

    # DNI y fecha
    fecha_text = datetime.now().strftime('%d/%m/%Y')
    texto_dni = f"DNI: {dni}"
    texto_fecha = f"Fecha de emisión: {fecha_text}"
    bbox_dni = draw.textbbox((0, 0), texto_dni, font=fuente_pie)
    bbox_fecha = draw.textbbox((0, 0), texto_fecha, font=fuente_pie)
    x_dni = 120
    x_fecha = ancho - 120 - (bbox_fecha[2] - bbox_fecha[0])
    y_pie_text = alto - 90
    draw.text((x_dni, y_pie_text), texto_dni, fill=accent_dark, font=fuente_pie)
    draw.text((x_fecha, y_pie_text), texto_fecha, fill=accent_dark, font=fuente_pie)

    # Pie final
    pie_text = "Gestión de Eventos - UTN Facultad Regional San Francisco"
    bbox_pie = draw.textbbox((0, 0), pie_text, font=fuente_pie)
    x_pie = (ancho - (bbox_pie[2] - bbox_pie[0])) // 2
    draw.text((x_pie, alto - 50), pie_text, fill=accent_dark, font=fuente_pie)

    salida_path = os.path.join(salida_dir, f"certificado_{dni}.png")
    imagen.save(salida_path, format='PNG')
    print(f"[INFO] Certificado generado: {salida_path}")
    return salida_path
