from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

# Crea un PDF di test che simula un volantino
filename = 'test_volantino.pdf'
c = canvas.Canvas(filename, pagesize=A4)
width, height = A4

# Sfondo
c.setFillColor(colors.lightblue)
c.rect(0, 0, width, height, fill=1)

# Header
c.setFillColor(colors.darkblue)
c.rect(0, height-80, width, 80, fill=1)
c.setFillColor(colors.white)
c.setFont('Helvetica-Bold', 24)
c.drawString(50, height-50, 'SUPERMERCATO TEST - OFFERTE SPECIALI')

# Prodotti
products = [
    {'nome': 'Pasta Barilla 500g', 'prezzo': '1.99', 'originale': '2.49'},
    {'nome': 'Latte Fresco 1L', 'prezzo': '1.29', 'originale': '1.49'},
    {'nome': 'Pane Integrale', 'prezzo': '2.50', 'originale': '2.99'},
    {'nome': 'Olio Extravergine 1L', 'prezzo': '4.99', 'originale': '5.99'}
]

y_start = height - 150
for i, product in enumerate(products):
    y_pos = y_start - (i * 100)
    
    # Box prodotto
    c.setFillColor(colors.white)
    c.rect(50, y_pos-60, width-100, 80, fill=1, stroke=1)
    
    # Nome prodotto
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(70, y_pos-20, product['nome'])
    
    # Prezzo scontato
    c.setFillColor(colors.red)
    c.setFont('Helvetica-Bold', 20)
    c.drawString(70, y_pos-45, f'€ {product["prezzo"]}')
    
    # Prezzo originale
    c.setFillColor(colors.gray)
    c.setFont('Helvetica', 12)
    c.drawString(200, y_pos-45, f'Prima: € {product["originale"]}')
    
    # Calcola sconto
    sconto = round((1 - float(product['prezzo']) / float(product['originale'])) * 100)
    
    # Etichetta sconto
    c.setFillColor(colors.red)
    c.rect(width-150, y_pos-50, 80, 30, fill=1)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(width-140, y_pos-40, f'-{sconto}%')

# Footer
c.setFillColor(colors.darkgray)
c.rect(0, 0, width, 60, fill=1)
c.setFillColor(colors.white)
c.setFont('Helvetica', 12)
c.drawString(50, 30, 'Offerte valide fino al 31/12/2024 - Supermercato Test')
c.drawString(50, 15, 'Via Test 123, Città Test - Tel: 123-456-7890')

c.save()
print(f'✅ PDF test creato: {filename}')
print(f'📦 Prodotti simulati: {len(products)}')
print(f'📄 Formato: PDF (A4)')