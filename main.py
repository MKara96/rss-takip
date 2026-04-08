from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime, timedelta
import re

# --- GERÇEK EDİTORYAL FOTOĞRAFLAR (Yüksek Çözünürlüklü Akademik Görseller) ---
# Tasarım hissini bilgisayar çizimlerinden çıkarıp, gerçek "Haber Sitesi" standardına taşıyoruz.
EDITORIAL_IMAGES = {
    "mku_haberler": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=800&q=80", # Kampüs / Üniversite Binası
    "mku_duyurular": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=800&q=80", # Akademik Mezuniyet / Duyuru
    "egitim_haberler": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=800&q=80", # Kitaplar ve Çalışma Masası
    "egitim_duyurular": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=800&q=80", # Kütüphane İçi
    "sosyal_bilimler_haberler": "https://images.unsplash.com/photo-1455390582262-044cdead2708?auto=format&fit=crop&w=800&q=80", # Kalem, Kağıt, Sosyal Bilimler
    "sosyal_bilimler_duyurular": "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=800&q=80", # Kitap Sayfaları
    "turkce_ogrt_haberler": "https://images.unsplash.com/photo-1474932430478-367d16b99031?auto=format&fit=crop&w=800&q=80", # Daktilo ve Edebiyat
    "turkce_ogrt_duyurular": "https://images.unsplash.com/photo-1455849318743-b2233052fcff?auto=format&fit=crop&w=800&q=80"  # Defter, Öğretmenlik
}

def get_fallback_image(category_key):
    return EDITORIAL_IMAGES.get(category_key, "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=800&q=80")

# --- TARİH İŞLEME ---
AYLAR = {"Ocak":"01","Şubat":"02","Mart":"03","Nisan":"04","Mayıs":"05","Haziran":"06",
         "Temmuz":"07","Ağustos":"08","Eylül":"09","Ekim":"10","Kasım":"11","Aralık":"12"}

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
    print(f"{name} taranıyor...")
    try:
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(4000)
        html_content = page.content()
    except Exception as e: return

    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup(["header", "footer", "nav", "aside", "script", "style"]): 
        element.decompose()
    
    fg = FeedGenerator()
    fg.id(url); fg.title(name.upper().replace('_', ' ')); fg.link(href=url, rel='alternate'); fg.language('tr')
    fg.description(f'MKÜ {name.replace("_", " ").title()} Akademik Yayını')

    added_links = set()
    count = 0
    tz = pytz.timezone('Europe/Istanbul')
    base_time = datetime.now(tz)
    
    for item in soup.find_all('a', href=True):
        link = item['href']
        if len(link) < 3 or link.startswith(('#', 'javascript', 'mailto', 'tel')): continue
        
        # --- İÇERİK METNİ (BODY) BULMA SORUNU ÇÖZÜLDÜ ---
        # Bot artık sadece linke değil, haberi kapsayan tüm geniş kutuya bakıyor.
        card = item.find_parent('div')
        if not card: continue
        
        # Kutu çok dar ise (içinde sadece başlık varsa), tüm metni almak için bir üst kutuya çık.
        if len(card.get_text(strip=True)) < 50 and card.parent and card.parent.name == 'div':
            card = card.parent
        if len(card.get_text(strip=True)) < 50 and card.parent and card.parent.name == 'div':
            card = card.parent
            
        raw_text = card.get_text(separator=' | ', strip=True)
        chunks = [c.strip() for c in raw_text.split(' | ') if len(c.strip()) > 3]
        if not chunks: continue
        
        # En uzun metin her zaman haberin asıl başlığı/özetidir
        link_text = item.get_text(strip=True)
        title = link_text if len(link_text) > 20 else max(chunks, key=len)
        if len(title) < 20: continue

        full_link = "https://mku.edu.tr/" + link.lstrip('/') if not link.startswith('http') else link
        if "mku.edu.tr" not in full_link or full_link in added_links: continue

        # --- RESİM SEÇİMİ ---
        img_tag = card.find('img')
        img_url = ""
        is_real_image = False
        
        if img_tag and img_tag.get('src'):
            img_url = img_tag['src']
            if not img_url.startswith('http'): 
                img_url = "https://mku.edu.tr/" + img_url.lstrip('/')
            is_real_image = True
        
        if not is_real_image:
            img_url = get_fallback_image(name)

        tarih_obj = tr_tarih_isle(raw_text)
        added_links.add(full_link)
        
        fe = fg.add_entry()
        
        # RESET KODU: RSS Okuyucunun hatalı görünümleri unutup yeni görselleri çekmesi için zorunlu ID değişimi
        fe.id(full_link + "#editoryal-v1")
        fe.link(href=full_link)
        fe.title(title)
        
        # KAPAK FOTOĞRAFI (RSS Bloğunda kesin görünecek kod)
        fe.enclosure(img_url, 0, 'image/jpeg')
        
        # --- ZENGİN EDİTORYAL İÇERİK METNİ ---
        detaylar = [c for c in chunks if c != title and c != link_text and len(c) < 100]
        
        desc_html = f'<img src="{img_url}" style="width:100%; max-width:800px; border-radius:8px; margin-bottom:15px;"/><br/>'
        desc_html += f'<div style="font-family: sans-serif; color: #334155; font-size: 15px; line-height: 1.6;">'
        desc_html += f'<p><b>Haber Özeti:</b><br/>{title}</p>'
        
        if detaylar:
            desc_html += '<hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 15px 0;"/>'
            desc_html += '<p><b>Birim & Tarih Bilgileri:</b><br/>'
            desc_html += "<br/>".join([f"• {c}" for c in detaylar])
            desc_html += '</p>'
            
        desc_html += f'<br/><a href="{full_link}" style="color: #2563eb; text-decoration: none; font-weight: 600;">Haberi Sitede Görüntüle ➔</a>'
        desc_html += '</div>'
        
        fe.description(desc_html)
        fe.published(base_time - timedelta(minutes=count)) 
        
        count += 1
        if count >= 15: break

    if not os.path.exists('rss_files'): os.makedirs('rss_files')
    fg.rss_file(f"rss_files/{name}.xml")
    print(f"Bitti: {name}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 Chrome/120.0 Safari/537.36")
        page = context.new_page()
        
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
        
        for name, url in URLS.items():
            generate_rss(name, url, page)
            
        browser.close()

if __name__ == "__main__": main()
