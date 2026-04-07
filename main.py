from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime

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

def generate_rss(name, url, page):
    print(f"{name} için veriler çekiliyor: {url}")
    
    try:
        page.goto(url, timeout=40000, wait_until="networkidle")
        page.wait_for_timeout(3000)
        html_content = page.content()
    except Exception as e:
        print(f"Bağlantı hatası ({url}): {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Sayfanın üst (header), alt (footer) ve yan menülerini (nav, aside) tamamen sil!
    # Bu sayede bot sadece orta kısımdaki asıl haber kartlarına odaklanır.
    for element in soup(["header", "footer", "nav", "aside"]):
        element.decompose()
    
    fg = FeedGenerator()
    fg.id(url)
    fg.title(name.replace('_', ' ').upper())
    fg.author({'name': 'MKU RSS Bot'})
    fg.link(href=url, rel='alternate')
    fg.description(f'{name} için detaylı RSS beslemesi')
    fg.language('tr')

    added_links = set()
    count = 0
    
    for item in soup.find_all('a', href=True):
        link = item['href']
        if link.startswith(('#', 'javascript', 'mailto', 'tel')) or len(link) < 3:
            continue
            
        # Metni parçalara ayır
        raw_text = item.get_text(separator=' | ', strip=True)
        chunks = [c.strip() for c in raw_text.split(' | ') if len(c.strip()) > 2]
        
        # Eğer link sadece kısacık bir başlıksa, onu saran kartı (div) bulup içindeki tarihi/bölümü al
        if len(chunks) <= 1 or (len(chunks) > 0 and len(chunks[0]) < 50):
            parent_div = item.find_parent('div')
            if parent_div:
                parent_text = parent_div.get_text(separator=' | ', strip=True)
                parent_chunks = [c.strip() for c in parent_text.split(' | ') if len(c.strip()) > 2]
                
                # Kart yapısına uygunsa (2 ile 8 parça arası detay içeriyorsa) bunu baz al
                if 1 < len(parent_chunks) <= 8:
                    chunks = parent_chunks

        if not chunks: continue
        if len(chunks) > 8: continue # Çok büyük sayfa iskeletlerini (yanlış algılamaları) atla
            
        # Kartın içindeki en uzun metin her zaman haberin asıl başlığıdır
        title = max(chunks, key=len)
        
        # Başlık çok kısaysa menü linkidir, atla
        if len(title) < 25: continue
            
        # Gözden kaçan istenmeyen idari menü kelimelerini filtrele
        ignore_words = ["rektör", "sekreterlik", "danışmanları", "kalem müdürlüğü", "tanıtım filmi", "faaliyetler"]
        if any(w in title.lower() for w in ignore_words) and len(title) < 60:
            continue

        full_link = "https://mku.edu.tr/" + link.lstrip('/') if not link.startswith('http') else link

        if "mku.edu.tr" in full_link and full_link not in added_links:
            added_links.add(full_link)
            
            fe = fg.add_entry()
            fe.id(full_link)
            fe.title(title)
            
            # Karttaki DİĞER bilgileri (Tarih, Bölüm adı) alt alta çok şık bir açıklama olarak ekle
            details = [c for c in chunks if c != title]
            if details:
                desc_html = "<br/>".join([f"• {c}" for c in details])
            else:
                desc_html = "Detaylar için haber linkine tıklayın."
                
            fe.description(desc_html)
            fe.link(href=full_link)
            
            tz = pytz.timezone('Europe/Istanbul')
            fe.published(datetime.now(tz)) 
            
            count += 1
            if count >= 15:
                break

    if not os.path.exists('rss_files'):
        os.makedirs('rss_files')
        
    fg.rss_file(f"rss_files/{name}.xml")
    print(f"{name}.xml oluşturuldu. Bulunan içerik: {count}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        for name, url in URLS.items():
            generate_rss(name, url, page)
        browser.close()

if __name__ == "__main__":
    main()
