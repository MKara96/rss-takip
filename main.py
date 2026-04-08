import os
import re
import pytz
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# --- 1. GERÇEK AKADEMİK KAPAK ÇİZİM MOTORU (Yüzde Yüz Çalışır) ---
def generate_academic_cover(category_key, title_text, bg_color_hex):
    if not os.path.exists('rss_files'):
        os.makedirs('rss_files')
        
    img_path = f"rss_files/{category_key}.png"
    width, height = 800, 400
    
    # Renk kodunu dönüştür
    bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Akademik bir font indiriyoruz (Merriweather Bold)
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Bold.ttf"
        font_bytes = requests.get(font_url).content
        font_main = ImageFont.truetype(BytesIO(font_bytes), 42)
        font_sub = ImageFont.truetype(BytesIO(font_bytes), 18)
    except:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Estetik Çerçeve
    draw.rectangle([20, 20, width-20, height-20], outline="#ffffff", width=2)
    draw.rectangle([30, 30, width-30, height-30], outline="rgba(255,255,255,0.4)", width=1)
    
    # Üst Kurum Yazısı
    top_text = "T.C. HATAY MUSTAFA KEMAL ÜNİVERSİTESİ"
    bbox = draw.textbbox((0, 0), top_text, font=font_sub)
    draw.text(((width - (bbox[2]-bbox[0])) / 2, 70), top_text, fill="#e2e8f0", font=font_sub)
    
    # Ayırıcı Çizgi
    draw.line([(width/2 - 60, 110), (width/2 + 60, 110)], fill="#ffffff", width=2)
    
    # Ana Başlık (Fakülte/Duyuru İsmi)
    lines = title_text.split('\n')
    y_text = 160
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        draw.text(((width - (bbox[2]-bbox[0])) / 2, y_text), line, fill="#ffffff", font=font_main)
        y_text += (bbox[3]-bbox[1]) + 15
        
    # Alt Etiket
    footer_text = "RESMİ BİLGİLENDİRME SİSTEMİ"
    bbox = draw.textbbox((0, 0), footer_text, font=font_sub)
    draw.text(((width - (bbox[2]-bbox[0])) / 2, height - 80), footer_text, fill="#94a3b8", font=font_sub)
    
    img.save(img_path)
    
    # Çizdiğimiz bu resmi RSS okuyucuya doğrudan GitHub linkiyle servis ediyoruz!
    repo = os.environ.get('GITHUB_REPOSITORY', 'mku/rss')
    return f"https://raw.githubusercontent.com/{repo}/main/{img_path}"

# KATEGORİ TEMALARI (Kurumsal Renkler)
THEMES = {
    "mku_haberler": {"title": "MKÜ HABER BÜLTENİ", "color": "#0f172a"}, # Koyu Lacivert
    "mku_duyurular": {"title": "MKÜ RESMİ DUYURULARI", "color": "#7f1d1d"}, # Koyu Bordo
    "egitim_haberler": {"title": "EĞİTİM FAKÜLTESİ\nHABERLERİ", "color": "#14532d"}, # Orman Yeşili
    "egitim_duyurular": {"title": "EĞİTİM FAKÜLTESİ\nDUYURULARI", "color": "#14532d"},
    "sosyal_bilimler_haberler": {"title": "SOSYAL BİLİMLER\nHABERLERİ", "color": "#4c1d95"}, # Koyu Mor
    "sosyal_bilimler_duyurular": {"title": "SOSYAL BİLİMLER\nDUYURULARI", "color": "#4c1d95"},
    "turkce_ogrt_haberler": {"title": "TÜRKÇE ÖĞRETMENLİĞİ\nHABERLERİ", "color": "#134e4a"}, # Derin Turkuaz
    "turkce_ogrt_duyurular": {"title": "TÜRKÇE ÖĞRETMENLİĞİ\nDUYURULARI", "color": "#134e4a"}
}

# --- 2. TARİH İŞLEME ---
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

# --- 3. METİN OKUMA VE RSS OLUŞTURMA ---
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
    fg.id(url); fg.title(THEMES[name]["title"].replace('\n', ' ')); fg.link(href=url, rel='alternate'); fg.language('tr')
    fg.description(f'{THEMES[name]["title"].replace(chr(10), " ")} Akademik Akışı')

    # Resmi bir kez çiz ve URL'sini al
    kapak_resmi_url = generate_academic_cover(name, THEMES[name]["title"], THEMES[name]["color"])

    added_links = set()
    count = 0
    tz = pytz.timezone('Europe/Istanbul')
    base_time = datetime.now(tz)
    
    for item in soup.find_all('a', href=True):
        link = item['href']
        if len(link) < 3 or link.startswith(('#', 'javascript', 'mailto', 'tel')): continue
        
        full_link = "https://mku.edu.tr/" + link.lstrip('/') if not link.startswith('http') else link
        if "mku.edu.tr" not in full_link or full_link in added_links: continue

        # İÇERİK OKUMA SORUNU ÇÖZÜLDÜ: Linkin etrafındaki tüm kartı buluyoruz
        parent = item
        for _ in range(4): # Kutuyu kapsayana kadar 4 seviye yukarı çık
            if parent.parent and parent.parent.name not in ['body', 'html', 'main']:
                if len(parent.parent.get_text(strip=True)) < 800: # Tüm sayfayı almamak için sınır
                    parent = parent.parent
                else: break

        raw_text = parent.get_text(separator=' | ', strip=True)
        raw_text = re.sub(r'(\|\s*)+', '| ', raw_text) # Fazla ayırıcıları temizle
        chunks = [c.strip() for c in raw_text.split('|') if len(c.strip()) > 3]
        if not chunks: continue
        
        # Gerçek başlığı bul
        link_text = item.get_text(strip=True)
        title = link_text if len(link_text) > 15 else max(chunks, key=len)
        if len(title) < 15: continue
        if any(w in title.lower() for w in ['ana sayfa', 'iletişim', 'hakkımızda']): continue

        # Sitedeki gerçek resmi bul, yoksa çizdiğimiz PNG'yi kullan
        img_tag = parent.find('img')
        img_url = kapak_resmi_url
        if img_tag and img_tag.get('src'):
            real_img = img_tag['src']
            img_url = "https://mku.edu.tr/" + real_img.lstrip('/') if not real_img.startswith('http') else real_img

        tarih_obj = tr_tarih_isle(raw_text)
        added_links.add(full_link)
        
        fe = fg.add_entry()
        
        # CACHE TEMİZLEME: RSS okuyucunun eski hatalı önbelleği silmesi için ID'yi zorla değiştirdik
        fe.id(full_link + "#final-v2")
        fe.link(href=full_link)
        fe.title(title)
        
        # KAPAK (THUMBNAIL) RESMİ - %100 Garantili
        fe.enclosure(img_url, 0, 'image/png')
        
        # EKSİKSİZ AÇIKLAMA METNİ
        detaylar = [c for c in chunks if c != title and c != link_text and len(c) < 150]
        
        desc_html = f'<img src="{img_url}" style="width:100%; border-radius:6px; margin-bottom:15px;"/><br/>'
        desc_html += '<div style="font-family: sans-serif; color: #1e293b;">'
        desc_html += f'<p><b>Habere Ait Özet ve Detaylar:</b></p>'
        
        for detay in detaylar:
            desc_html += f'• {detay}<br/>'
            
        desc_html += '</div>'
        fe.description(desc_html)
        
        # Habere doğru sırayı ver
        fe.published(base_time - timedelta(minutes=count)) 
        
        count += 1
        if count >= 15: break

    if not os.path.exists('rss_files'): os.makedirs('rss_files')
    fg.rss_file(f"rss_files/{name}.xml")
    print(f"Başarıyla tamamlandı: {name}")

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
