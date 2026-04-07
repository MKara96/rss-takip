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
        # Gerçek bir tarayıcı gibi siteye girer ve sitenin tam yüklenmesini bekler
        page.goto(url, timeout=40000, wait_until="networkidle")
        page.wait_for_timeout(3000) # İçeriklerin ekrana düşmesi için ekstra 3 saniye bekleme
        html_content = page.content()
    except Exception as e:
        print(f"Bağlantı hatası ({url}): {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    fg = FeedGenerator()
    fg.id(url)
    fg.title(name.replace('_', ' ').upper())
    fg.author({'name': 'MKU RSS Bot'})
    fg.link(href=url, rel='alternate')
    fg.description(f'{name} için otomatik RSS beslemesi')
    fg.language('tr')

    added_links = set()
    count = 0
    
    for item in soup.find_all('a', href=True):
        link = item['href']
        title = item.text.strip()
        
        # Linkin kendi metni yoksa dışındaki kutucuğun metnini al
        if len(title) < 15 and item.parent:
            title = item.parent.text.strip()
                
        title = " ".join(title.split()) # Fazla boşlukları temizle
        
        if 15 < len(title) < 300 and not link.startswith(('#', 'javascript', 'mailto')):
            
            # Sayfadaki gereksiz menü butonlarını ele
            ignore_words = ["ana sayfa", "iletişim", "misyon", "hakkımızda", "yönetim", "telefon"]
            if any(w in title.lower() for w in ignore_words) and len(title) < 30:
                continue

            if not link.startswith('http'):
                full_link = "https://mku.edu.tr/" + link.lstrip('/')
            else:
                full_link = full_link = link

            if "mku.edu.tr" in full_link and full_link not in added_links:
                added_links.add(full_link)
                
                fe = fg.add_entry()
                fe.id(full_link)
                fe.title(title)
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
    # Gerçek bir Chrome tarayıcı motoru başlatıyoruz
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
