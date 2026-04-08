from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime
import re
import base64

# --- 8 KATEGORİ İÇİN RESMİ 'GÜNCELLEME/BİLDİRİ' TASARIMLARI ---
THEMES = {
    "mku_haberler": {"top": "MKÜ", "bottom": "HABERLERİ", "color": "#0ea5e9", "badge": "📰 HABER BÜLTENİ"},
    "mku_duyurular": {"top": "MKÜ", "bottom": "DUYURULARI", "color": "#ef4444", "badge": "📌 RESMİ DUYURU"},
    "egitim_haberler": {"top": "EĞİTİM FAKÜLTESİ", "bottom": "HABERLERİ", "color": "#10b981", "badge": "📰 HABER BÜLTENİ"},
    "egitim_duyurular": {"top": "EĞİTİM FAKÜLTESİ", "bottom": "DUYURULARI", "color": "#10b981", "badge": "🔔 BİLGİLENDİRME"},
    "sosyal_bilimler_haberler": {"top": "SOSYAL BİLİMLER", "bottom": "HABERLERİ", "color": "#8b5cf6", "badge": "📰 HABER BÜLTENİ"},
    "sosyal_bilimler_duyurular": {"top": "SOSYAL BİLİMLER", "bottom": "DUYURULARI", "color": "#8b5cf6", "badge": "⚡ GÜNCELLEME"},
    "turkce_ogrt_haberler": {"top": "TÜRKÇE ÖĞRETMENLİĞİ", "bottom": "HABERLERİ", "color": "#14b8a6", "badge": "📰 HABER BÜLTENİ"},
    "turkce_ogrt_duyurular": {"top": "TÜRKÇE ÖĞRETMENLİĞİ", "bottom": "DUYURULARI", "color": "#14b8a6", "badge": "📢 ÖNEMLİ DUYURU"}
}

def generate_update_svg(category_key):
    """Modern, resmi bir sistem bildirisi kapağı üretir."""
    t = THEMES.get(category_key, {"top": "SİSTEM", "bottom": "BİLDİRİSİ", "color": "#64748b", "badge": "⚡ BİLGİLENDİRME"})
    
    # Modern, koyu tema bildiri kartı tasarımı
    svg = f"""
    <svg width="800" height="400" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0f172a" />
                <stop offset="100%" stop-color="#1e293b" />
            </linearGradient>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#334155" stroke-width="0.5"/>
            </pattern>
        </defs>
        <rect width="800" height="400" fill="url(#bg)"/>
        <rect width="800" height="400" fill="url(#grid)"/>
        
        <rect width="12" height="400" fill="{t['color']}"/>
        
        <text x="60" y="80" font-family="system-ui, -apple-system, sans-serif" font-size="14" fill="#94a3b8" letter-spacing="4">T.C. HATAY MUSTAFA KEMAL ÜNİVERSİTESİ</text>
        
        <rect x="60" y="120" width="220" height="36" rx="6" fill="{t['color']}" fill-opacity="0.15" stroke="{t['color']}" stroke-width="1"/>
        <text x="170" y="144" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="bold" fill="{t['color']}" text-anchor="middle" letter-spacing="1">{t['badge']}</text>
        
        <text x="60" y="230" font-family="system-ui, -apple-system, sans-serif" font-size="38" font-weight="800" fill="#f8fafc" letter-spacing="1">{t['top']}</text>
        <text x="60" y="280" font-family="system-ui, -apple-system, sans-serif" font-size="34" font-weight="300" fill="#cbd5e1" letter-spacing="2">{t['bottom']}</text>
        
        <line x1="60" y1="330" x2="740" y2="330" stroke="#334155" stroke-width="1"/>
        <text x="60" y="365" font-family="monospace" font-size="12" fill="#475569">SYS.UPDATE // OTO-GÜNCELLEME SİSTEMİ</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{encoded}"

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
    except Exception as e:
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    for element in soup(["header", "footer", "nav", "aside", "script", "style"]): 
        element.decompose()
    
    fg = FeedGenerator()
    fg.id(url); fg.title(name.upper().replace('_', ' ')); fg.link(href=url, rel='alternate'); fg.language('tr')
    fg.description(f'MKÜ {name.replace("_", " ").title()} Resmi Bildiri Akışı')

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

        # --- RESİM SEÇİMİ ---
        img_tag = parent.find('img')
        img_url = ""
        is_real_image = False
        
        if img_tag and img_tag.get('src'):
            img_url = img_tag['src']
            if not img_url.startswith('http'): 
                img_url = "https://mku.edu.tr/" + img_url.lstrip('/')
            is_real_image = True
        
        # Gerçek resim yoksa sistem bildirisi üret!
        if not is_real_image:
            img_url = generate_update_svg(name)

        tarih_obj = tr_tarih_isle(full_text)
        added_links.add(full_link)
        
        fe = fg.add_entry()
        fe.id(full_link)
        fe.link(href=full_link)
        
        # --- KAPAK FOTOĞRAFI KODU (ENCLOSURE) ---
        # Siteden çekilen gerçek resimse RSS Thumbnail standartlarına ekliyoruz.
        if is_real_image:
            fe.enclosure(img_url, 0, 'image/jpeg')
        
        text_parts = [t.strip() for t in full_text.split('  ') if len(t.strip()) > 10]
        fe.title(max(text_parts, key=len) if text_parts else "Yeni Duyuru")
        
        # Açıklama (Her ihtimale karşı resmi metnin en üstüne de koyuyoruz)
        desc = f'<img src="{img_url}" style="width:100%; max-width: 800px; border-radius:8px; border: 1px solid #e2e8f0; margin-bottom:15px;"/><br/>'
        desc += f"<div style='font-family: sans-serif; color: #334155;'>"
        desc += f"<b style='color:#0f172a;'>Kategori:</b> {name.replace('_', ' ').upper()}<br/><br/>"
        desc += f"<b style='color:#0f172a;'>Özet Metin:</b><br/> {full_text[:350]}..."
        desc += "</div>"
        fe.description(desc)
        
        fe.published(tarih_obj)
        
        count += 1
        if count >= 15: break

    if not os.path.exists('rss_files'): os.makedirs('rss_files')
    fg.rss_file(f"rss_files/{name}.xml")

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
