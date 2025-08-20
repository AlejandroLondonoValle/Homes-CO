import requests
import pyfiglet
import json
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

# Inicializar colorama
init(autoreset=True)

# Headers globales para evitar bloqueos
headers = {"User-Agent": "Mozilla/5.0"}

def check_site(session, nombre, datos, usuario):
    """Verifica si un usuario existe en un sitio"""
    link = datos["url"].format(usuario)
    try:
        resp = session.get(link, headers=headers, timeout=5)

        # Caso 1: Verificación por código de estado
        if datos["errorType"] == "status_code":
            return (nombre, link, resp.status_code == 200)

        # Caso 2: Verificación por mensajes de error en el HTML
        elif datos["errorType"] == "message":
            error_msgs = datos["errorMsg"] if isinstance(datos["errorMsg"], list) else [datos["errorMsg"]]
            if any(msg in resp.text for msg in error_msgs):
                return (nombre, link, False)
            return (nombre, link, True)

        return (nombre, link, False)

    except Exception:
        return (nombre, link, False)

def buscar_usuario(usuario, sitios):
    """Lanza búsquedas en paralelo con requests.Session"""
    resultados = []
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(check_site, session, nombre, datos, usuario)
                for nombre, datos in sitios.items() if nombre != "$schema"
            ]
            for future in futures:
                resultados.append(future.result())
    return resultados

def encabezado_y_marca(canvas, doc, usuario, fecha):
    """Dibuja el encabezado y marca de agua en cada página"""
    width, height = letter

    # Insertar logo
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQz3XWYKu_vwhT-kwB_3GYLfw7OHWwzMO2VPw&s"
    logo_path = "/tmp/logo.png"
    with open(logo_path, "wb") as f:
        f.write(requests.get(logo_url).content)
    canvas.drawImage(logo_path, 50, height - 80, width=50, height=50, mask='auto')

    # Texto empresa
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(120, height - 50, "BruteKaliSecurity")

    canvas.setFont("Helvetica", 10)
    canvas.setFillGray(0.3)
    canvas.drawString(120, height - 65, "Informe de Seguridad - Reporte de Búsqueda")

    # Fecha y usuario
    canvas.setFont("Helvetica", 10)
    canvas.setFillGray(0.2)
    canvas.drawRightString(width - 50, height - 50, f"Fecha: {fecha}")
    canvas.drawRightString(width - 50, height - 65, f"Usuario: {usuario}")

    # Marca de agua
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 40)
    canvas.setFillGray(0.85, 0.5)
    canvas.rotate(45)
    canvas.drawCentredString(width / 2, height / 2, "BruteKaliSecurity")
    canvas.restoreState()

def exportar_pdf(usuario, resultados):
    """Genera un PDF con los resultados positivos en tabla"""
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"resultados_{usuario}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]

    story = []
    story.append(Spacer(1, 100))  # espacio debajo del encabezado

    # Tabla de resultados
    data = [["#", "✓", "Nombre de Sitio", "Enlace"]]
    i = 1
    for nombre, link, encontrado in sorted(resultados):
        if encontrado:
            check = "✓"
            enlace = Paragraph(f'<a href="{link}" color="blue">{link}</a>', styleN)
        else:
            check = "✗"
            enlace = "No encontrado"
        data.append([i, check, nombre, enlace])
        i += 1

    table = Table(data, colWidths=[30, 30, 150, 250])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 11),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("GRID", (0,0), (-1,-1), 0.25, colors.gray),
    ]))

    story.append(table)
    doc.build(story, onFirstPage=lambda c, d: encabezado_y_marca(c, d, usuario, fecha),
                      onLaterPages=lambda c, d: encabezado_y_marca(c, d, usuario, fecha))

    print(Fore.CYAN + f"\n📄 PDF generado: {filename}")

def main():
    # Banner
    banner = pyfiglet.figlet_format("Sherlock Colombia")
    print(Fore.CYAN + banner)

    # Cargar el JSON
    with open("data.json", "r", encoding="utf-8") as f:
        sitios = json.load(f)

    # Pedir usuario
    usuario = input(Fore.YELLOW + "Ingresa el usuario que deseas buscar: ")

    # Buscar en todos los sitios
    resultados = buscar_usuario(usuario, sitios)

    # Mostrar resultados en consola
    print(Fore.MAGENTA + "\nResultados:")
    for nombre, link, encontrado in sorted(resultados):
        if encontrado:
            print(Fore.GREEN + f"[✓] {nombre} → {link}")
        else:
            print(Fore.RED + f"[✗] {nombre} (no encontrado)")

    # Exportar a PDF
    exportar_pdf(usuario, resultados)

if __name__ == "__main__":
    main()
