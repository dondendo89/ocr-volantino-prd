#!/usr/bin/env python3
"""
Generatore di Card Prodotto
Crea immagini strutturate e professionali per i prodotti estratti
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class ProductCardGenerator:
    def __init__(self):
        """Inizializza il generatore di card prodotto"""
        self.card_width = 400
        self.card_height = 300
        self.margin = 15
        self.header_height = 40
        
        # Colori del tema
        self.colors = {
            'background': (255, 255, 255),  # Bianco
            'header': (231, 76, 60),        # Rosso
            'product_bg': (52, 152, 219),   # Blu
            'brand_bg': (243, 156, 18),     # Arancione
            'price_bg': (231, 76, 60),      # Rosso
            'offer_bg': (241, 196, 15),     # Giallo
            'text_dark': (44, 62, 80),      # Grigio scuro
            'text_light': (127, 140, 141),  # Grigio chiaro
            'border': (221, 221, 221)       # Grigio bordo
        }
        
        # Carica font (usa font di sistema se disponibili)
        self.fonts = self._load_fonts()
    
    def _load_fonts(self):
        """Carica i font disponibili nel sistema"""
        fonts = {}
        font_paths = [
            '/System/Library/Fonts/Arial.ttf',  # macOS
            '/System/Library/Fonts/Helvetica.ttc',  # macOS
            'C:/Windows/Fonts/arial.ttf',  # Windows
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        ]
        
        # Trova il primo font disponibile
        default_font_path = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                default_font_path = font_path
                break
        
        try:
            if default_font_path:
                fonts['title'] = ImageFont.truetype(default_font_path, 20)
                fonts['brand'] = ImageFont.truetype(default_font_path, 14)
                fonts['price'] = ImageFont.truetype(default_font_path, 24)
                fonts['info'] = ImageFont.truetype(default_font_path, 14)
                fonts['small'] = ImageFont.truetype(default_font_path, 10)
                fonts['header'] = ImageFont.truetype(default_font_path, 18)
            else:
                # Fallback ai font di default
                fonts['title'] = ImageFont.load_default()
                fonts['brand'] = ImageFont.load_default()
                fonts['price'] = ImageFont.load_default()
                fonts['info'] = ImageFont.load_default()
                fonts['small'] = ImageFont.load_default()
                fonts['header'] = ImageFont.load_default()
                logger.warning("⚠️ Usando font di default - qualità ridotta")
        except Exception as e:
            logger.warning(f"⚠️ Errore caricamento font: {e}")
            # Usa font di default per tutto
            default_font = ImageFont.load_default()
            fonts = {
                'title': default_font,
                'brand': default_font,
                'price': default_font,
                'info': default_font,
                'small': default_font,
                'header': default_font
            }
        
        return fonts
    
    def _clean_text(self, text, max_length=None):
        """Pulisce e tronca il testo se necessario"""
        if not text:
            return "N/A"
        
        # Rimuovi caratteri speciali problematici
        text = re.sub(r'[^\w\s.,€$-]', '', str(text))
        text = text.strip()
        
        if max_length and len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        return text or "N/A"
    
    def _draw_rounded_rectangle(self, draw, coords, radius, fill, outline=None):
        """Disegna un rettangolo con angoli arrotondati"""
        x1, y1, x2, y2 = coords
        
        # Disegna il rettangolo principale
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline)
        
        # Disegna gli angoli arrotondati
        draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill, outline=outline)
        draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill, outline=outline)
        draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill, outline=outline)
        draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill, outline=outline)
    
    def _extract_product_region(self, original_image_path, product_info):
        """Estrae la regione del prodotto dall'immagine originale"""
        try:
            with Image.open(original_image_path) as img:
                # Per ora usa l'intera immagine ridimensionata
                # In futuro si potrebbe implementare il riconoscimento delle regioni
                img_resized = img.copy()
                img_resized.thumbnail((100, 100), Image.Resampling.LANCZOS)
                return img_resized
        except Exception as e:
            logger.warning(f"⚠️ Errore estrazione regione: {e}")
            # Crea un'immagine placeholder
            placeholder = Image.new('RGB', (100, 100), self.colors['product_bg'])
            return placeholder
    
    def generate_product_card(self, product_info, original_image_path=None, supermercato_nome="SUPERMERCATO"):
        """Genera una card prodotto professionale"""
        try:
            # Crea l'immagine base
            img = Image.new('RGB', (self.card_width, self.card_height), self.colors['background'])
            draw = ImageDraw.Draw(img)
            
            # Disegna il bordo
            draw.rectangle([0, 0, self.card_width-1, self.card_height-1], 
                         outline=self.colors['border'], width=2)
            
            # Header con nome supermercato
            self._draw_rounded_rectangle(draw, 
                                       [self.margin, self.margin, 
                                        self.card_width - self.margin, 
                                        self.margin + self.header_height], 
                                       5, self.colors['header'])
            
            supermercato_text = self._clean_text(supermercato_nome, 25).upper()
            draw.text((self.card_width // 2, self.margin + self.header_height // 2), 
                     supermercato_text, 
                     font=self.fonts['header'], 
                     fill='white', 
                     anchor='mm')
            
            # Estrai e posiziona l'immagine del prodotto
            product_img = None
            if original_image_path and os.path.exists(original_image_path):
                product_img = self._extract_product_region(original_image_path, product_info)
            
            # Area immagine prodotto
            img_x = self.margin + 10
            img_y = self.margin + self.header_height + 15
            img_w, img_h = 100, 100
            
            if product_img:
                # Ridimensiona mantenendo proporzioni
                product_img.thumbnail((img_w, img_h), Image.Resampling.LANCZOS)
                # Centra l'immagine
                paste_x = img_x + (img_w - product_img.width) // 2
                paste_y = img_y + (img_h - product_img.height) // 2
                img.paste(product_img, (paste_x, paste_y))
            else:
                # Placeholder per l'immagine
                self._draw_rounded_rectangle(draw, 
                                           [img_x, img_y, img_x + img_w, img_y + img_h], 
                                           10, self.colors['product_bg'])
                draw.text((img_x + img_w//2, img_y + img_h//2), 
                         "PRODOTTO", 
                         font=self.fonts['brand'], 
                         fill='white', 
                         anchor='mm')
            
            # Informazioni prodotto
            info_x = img_x + img_w + 20
            info_y = img_y
            
            # Nome prodotto
            nome = self._clean_text(product_info.get('nome', 'Prodotto'), 20)
            draw.text((info_x, info_y), nome, 
                     font=self.fonts['title'], 
                     fill=self.colors['text_dark'])
            
            # Marca evidenziata
            marca = self._clean_text(product_info.get('marca', 'N/A'), 12)
            if marca != 'N/A':
                marca_y = info_y + 25
                marca_w = len(marca) * 8 + 20
                self._draw_rounded_rectangle(draw, 
                                           [info_x, marca_y, info_x + marca_w, marca_y + 20], 
                                           3, self.colors['brand_bg'])
                draw.text((info_x + marca_w//2, marca_y + 10), 
                         marca.upper(), 
                         font=self.fonts['brand'], 
                         fill='white', 
                         anchor='mm')
                info_y = marca_y + 30
            else:
                info_y += 30
            
            # Quantità/Peso
            quantita = self._clean_text(product_info.get('quantita', ''), 15)
            if quantita:
                draw.text((info_x, info_y), f"Peso: {quantita}", 
                         font=self.fonts['info'], 
                         fill=self.colors['text_light'])
                info_y += 20
            
            # Prezzo grande e visibile
            prezzo = product_info.get('prezzo')
            prezzo_str = product_info.get('prezzo_originale', 'N/A')
            
            if prezzo or prezzo_str != 'N/A':
                price_y = info_y + 10
                price_w = 120
                price_h = 40
                
                self._draw_rounded_rectangle(draw, 
                                           [info_x, price_y, info_x + price_w, price_y + price_h], 
                                           5, self.colors['price_bg'])
                
                if prezzo:
                    price_text = f"€ {prezzo:.2f}"
                else:
                    price_text = str(prezzo_str)
                
                draw.text((info_x + price_w//2, price_y + 20), 
                         price_text, 
                         font=self.fonts['price'], 
                         fill='white', 
                         anchor='mm')
                
                draw.text((info_x + price_w//2, price_y + 35), 
                         "al pezzo", 
                         font=self.fonts['small'], 
                         fill='white', 
                         anchor='mm')
                
                info_y = price_y + price_h + 10
            
            # Categoria
            categoria = self._clean_text(product_info.get('categoria', ''), 20)
            if categoria:
                draw.text((info_x, info_y), f"Categoria: {categoria}", 
                         font=self.fonts['info'], 
                         fill=self.colors['text_light'])
            
            # Offerta speciale (se presente sconto)
            sconto = product_info.get('sconto_percentuale')
            if sconto and sconto > 0:
                offer_x = self.card_width - 80
                offer_y = img_y + 20
                
                draw.ellipse([offer_x - 40, offer_y - 20, offer_x + 40, offer_y + 20], 
                           fill=self.colors['offer_bg'])
                
                draw.text((offer_x, offer_y - 8), "OFFERTA", 
                         font=self.fonts['small'], 
                         fill=self.colors['text_dark'], 
                         anchor='mm')
                draw.text((offer_x, offer_y + 8), f"-{sconto:.0f}%", 
                         font=self.fonts['small'], 
                         fill=self.colors['text_dark'], 
                         anchor='mm')
            
            # Footer con timestamp
            footer_y = self.card_height - 25
            timestamp = datetime.now().strftime("%d/%m/%Y")
            draw.text((self.margin, footer_y), f"Generato il {timestamp}", 
                     font=self.fonts['small'], 
                     fill=self.colors['text_light'])
            
            return img
            
        except Exception as e:
            logger.error(f"❌ Errore generazione card: {e}")
            # Ritorna un'immagine di errore
            error_img = Image.new('RGB', (self.card_width, self.card_height), (255, 200, 200))
            error_draw = ImageDraw.Draw(error_img)
            error_draw.text((self.card_width//2, self.card_height//2), 
                          "Errore generazione card", 
                          font=self.fonts['info'], 
                          fill='red', 
                          anchor='mm')
            return error_img
    
    def save_product_card(self, product_info, original_image_path, output_dir, 
                         image_name, region_id, supermercato_nome="SUPERMERCATO"):
        """Genera e salva una card prodotto"""
        try:
            # Genera la card
            card_img = self.generate_product_card(product_info, original_image_path, supermercato_nome)
            
            # Crea nome file pulito
            product_name = self._clean_text(product_info.get('nome', 'prodotto'), 30)
            product_name = re.sub(r'[^\w\s-]', '', product_name).strip()
            product_name = re.sub(r'[-\s]+', '_', product_name)
            
            filename = f"{image_name}_{product_name}_card_{region_id}.jpg"
            filepath = Path(output_dir) / filename
            
            # Salva con qualità alta
            card_img.save(filepath, 'JPEG', quality=95, optimize=True)
            
            logger.info(f"💾 Card salvata: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Errore salvataggio card: {e}")
            return None

# Alias per compatibilità
GeminiOnlyExtractor = ProductCardGenerator