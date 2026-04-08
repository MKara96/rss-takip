from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime
import re
import urllib.parse

# Ay isimlerini sayıya çevirmek için sözlük
AYLAR = {"Ocak":"01","Şubat":"02","Mart":"03","Nisan":"04","Mayıs":"05","Haziran":"06",
         "Temmuz":"07","Ağustos":"08","Eylül":"09","Ekim":"10","Kasım":"11","Aralık":"12"}

URLS = {
    "mku_haberler": "https://mku.edu.tr/newslist",
    "mku_duyurular": "https://mku.edu.tr/announcements",
    "egitim_haberler": "https://mku.edu.tr/departments/8/newsList",
    "egitim_duyurular": "https://mku.edu.tr/departments/8/announcements",
    "sosyal_bilimler_haberler": "https://mku.edu.tr/departments/121/newsList",
    "sosyal_bilimler_duyurular": "https://mku.edu.tr/departments/121/announcements",
    "turkce_ogrt_haberler": "https://mku.edu.tr/departments/1488/newsList",
    "turkce_ogrt_duyurular": "https://mku.edu.tr/departments/1488/announcements"
}

# HER KATEGORİ İÇİN ÖZEL VARSAYILAN RESİMLER (Estetik Renk Kodlarıyla)
VARSAYILAN_RESIMLER = {
    "mku_haberler": "https://placehold.co/800x400/1E3A8A/FFFFFF/png?text=MKU+Haberler&font=Montserrat", # Koyu Mavi
    "mku_duyurular": "https://placehold.co/800x400/B91C1C/FFFFFF/png?text=MKU+Duyurular&font=Montserrat", # Koyu Kırmızı
    "egitim_haberler": "https://placehold.co/800x400/047857/FFFFFF/png?text=Egitim+Fakultesi\nHaberler&font=Montserrat", # Zümrüt Yeşili
    "egitim_duyurular": "https://placehold.co/800x400/047857/FFFFFF/png?text=Egitim+Fakultesi\nDuyurular&font=Montserrat",
    "sosyal_bilimler_haberler": "https://placehold.co/800x400/6D28D9/FFFFFF/png?text=Sosyal+Bilimler\nHaberler&font=Montserrat", # Mor
    "sosyal_bilimler_duyurular": "https://placehold.co/800x400/6D28D9/FFFFFF/png?text=Sosyal+Bilimler\nDuyurular&font=Montserrat",
    "turkce_ogrt_haberler": "https://placehold.co/800x400/0F766E/FFFFFF/png?text=Turkce+Ogretmenligi\nHaberler&font=Montserrat", # Turkuaz
    "turkce_ogrt_duyurular": "https://placehold.co/800x400/0F766E/FFFFFF/png?text=Turkce+Ogretmenligi\nDuyurular&font=Montserrat"
}

def tr_tarih_isle(tarih_str):
    try:
        for tr_ay, sayi_ay in AYLAR.items():
            if tr_ay in tarih_str:
                tarih_str = tarih_str.replace(tr_ay, sayi_ay)
        parcalar = re.findall(r'\d+', tarih_str)
        if len(parcalar) >= 3:
            gun, ay, yil = parcalar[0].zfill(2), parcalar[1].zfill(2), parcalar[2]
            return datetime.strptime(f"{yil}-{ay}-{gun}", "%Y-%m-%d").replace(tzinfo=pytz.timezone('Europe/Istanbul'))
    except: pass
    return datetime.now(pytz.timezone('Europe/Istanbul'))

def generate_rss(name, url, page):
    print(f"{name} taranıyor: {url}")
    try:
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        html_content = page.content()
    except Exception as e:
        print(f"Hata: {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup(["header", "footer", "nav", "aside", "script", "style"]): 
        element.decompose()
    
    fg = FeedGenerator()
    fg.id(url); fg.title(name.upper()); fg.link(href=url, rel='alternate'); fg.language('tr')
    fg.description(f'MKÜ {name} - Otomatik Besleme')

    added_links = set()
    count = 0
    
    for item in soup.find_all('a', href=True):
        link = item['href']
        parent = item.find_parent('div')
        if not parent: continue
        
        full_text = parent.get_text(separator=' ', strip=True)
        if len(full_text) < 30: continue
        
        full_link = "https://mku.edu.tr/" + link.lstrip('/') if not link.startswith('http') else link
        if "mku.edu.tr" not in full_link or full_link in added_links: continue

        # --- RESİM VE YEDEK RESİM KONTROLÜ ---
        img_tag = parent.find('img')
        img_url = ""
        
        # 1. Sitede resim var mı diye bak
        if img_tag and img_tag.get('src'):
            img_url = img_tag['src']
            if not img_url.startswith('http'): 
                img_url = "https://mku.edu.tr/" + img_url.lstrip('/')
                
        # 2. Eğer sitede resim yoksa, bizim tasarladığımız yedek resmi kullan
        if not img_url:
            img_url = VARSAYILAN_RESIMLER.get(name, "https://placehold.co/800x400/333333/FFFFFF/png?text=MKU+Duyuru")

        tarih_obj = tr_tarih_isle(full_text)
        added_links.add(full_link)
        
        fe = fg.add_entry()
        fe.id(full_link)
        fe.link(href=full_link)
        
        text_parts = [t.strip() for t in full_text.split('  ') if len(t.strip()) > 10]
        fe.title(max(text_parts, key=len) if text_parts else "Yeni Duyuru")
        
        # Açıklama içeriği
        desc = ""
        if img_url: desc += f'<img src="{img_url}" style="width:100%; border-radius:8px; margin-bottom:12px;"/><br/>'
        desc += f"<b>Detay:</b> {full_text[:300]}..."
        fe.description(desc)
        
        fe.published(tarih_obj)
        
        count += 1
        if count >= 15: break

    if not os.path.exists('rss_files'): os.makedirs('rss_files')
    fg.rss_file(f"rss_files/{name}.xml")
    print(f"{name} tamamlandı. ({count} içerik)")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        for name, url in URLS.items():
            generate_rss(name, url, page)
        browser.close()

if __name__ == "__main__": main()
