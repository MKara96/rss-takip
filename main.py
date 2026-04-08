from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime, timedelta
import re

# --- AKADEMİK VE EDİTORYAL GÖRSEL ÜRETİCİ (GERÇEK PNG LİNKLERİ) ---
def generate_editorial_image(category_key):
    # Akademik Renkler: Lacivert, Bordo, Koyu Orman Yeşili, Koyu Mor, Derin Turkuaz
    themes = {
        "mku_haberler": {"bg": "0f172a", "title": "MKU+HABERLERI"},
        "mku_duyurular": {"bg": "7f1d1d", "title": "MKU+DUYURULARI"},
        "egitim_haberler": {"bg": "14532d", "title": "EGITIM+FAKULTESI%0AHABERLERI"},
        "egitim_duyurular": {"bg": "14532d", "title": "EGITIM+FAKULTESI%0ADUYURULARI"},
        "sosyal_bilimler_haberler": {"bg": "4c1d95", "title": "SOSYAL+BILIMLER%0AHABERLERI"},
        "sosyal_bilimler_duyurular": {"bg": "4c1d95", "title": "SOSYAL+BILIMLER%0ADUYURULARI"},
        "turkce_ogrt_haberler": {"bg": "134e4a", "title": "TURKCE+OGRETMENLIGI%0AHABERLERI"},
        "turkce_ogrt_duyurular": {"bg": "134e4a", "title": "TURKCE+OGRETMENLIGI%0ADUYURULARI"}
    }
    t = themes.get(category_key, {"bg": "1e293b", "title": "AKADEMIK+DUYURU"})
    
    # URL formatında boşluklar ve satır atlamalar (%0A)
    text = f"T.C.+HATAY+MUSTAFA+KEMAL+UNIVERSITESI%0A%0A---%0A%0A{t['title']}%0A%0A---%0A%0AResmi+Akademik+Bulten"
    
    # Gerçek PNG resmi üreten ve RSS okuyucuların kapağa sorunsuz alacağı link (Playfair Display akademik fontu ile)
    return f"https://placehold.co/800x400/{t['bg']}/f8fafc/png?text={text}&font=Playfair+Display"

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
        
        # BİLGİ OKUMA SORUNU ÇÖZÜMÜ: Sadece linki değil, kapsayıcı kutuyu genişletiyoruz
        parent = item.find_parent('div')
        if not parent: continue
        
        # Eğer kutu çok küçükse (sadece başlık varsa), bir üst kutuya çıkıp tüm metni al
        if len(parent.get_text(strip=True)) < 40 and parent.parent and parent.parent.name == 'div':
            parent = parent.parent
            
        raw_text = parent.get_text(separator=' | ', strip=True)
        chunks = [c.strip() for c in raw_text.split(' | ') if len(c.strip()) > 3]
        if not chunks: continue
        
        # En mantıklı başlığı bul
        link_text = item.get_text(strip=True)
        title = link_text if len(link_text) > 15 else max(chunks, key=len)
        if len(title) < 20: continue

        full_link = "https://mku.edu.tr/" + link.lstrip('/') if not link.startswith('http') else link
        if "mku.edu.tr" not in full_link or full_link in added_links: continue

        # --- RESİM SEÇİMİ ---
        img_tag = parent.find('img')
        img_url = ""
        is_real_image = False
        
        if img_tag and img_tag.get('src'):
            img_url = img_tag['src']
            if not img_url.startswith('http'): 
                img_url = "https://mku.edu.tr/" + img_url.lstrip('/')
            is_real_image = True
        
        if not is_real_image:
            img_url = generate_editorial_image(name)

        tarih_obj = tr_tarih_isle(raw_text)
        added_links.add(full_link)
        
        fe = fg.add_entry()
        
        # CACHE HİLESİ: RSS Okuyucunun tasarımları hemen çekmesi için linke #v2 ekledik
        fe.id(full_link + "#v2")
        fe.link(href=full_link)
        fe.title(title)
        
        # KAPAK FOTOĞRAFI (Artık %100 her okuyucuda kapağa düşecek)
        fe.enclosure(img_url, 0, 'image/png')
        
        # DETAYLI AÇIKLAMA: Bilgilerin madde madde okunduğu yer
        desc_html = f'<img src="{img_url}" style="width:100%; border-radius:4px; margin-bottom:15px;"/><br/>'
        desc_html += "<b>Duyuru Detayları:</b><br/>"
        
        # Başlık haricindeki tüm detayları (Tarih, Bölüm) alt alta yazdırıyoruz
        detaylar = [c for c in chunks if c != title]
        if detaylar:
            desc_html += "<br/>".join([f"• {c}" for c in detaylar])
        else:
            desc_html += "• " + raw_text[:200] + "..."
            
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
