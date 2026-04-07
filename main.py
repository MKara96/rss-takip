import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime

# Takip etmek istediğin tüm MKÜ linkleri
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

def generate_rss(name, url):
    print(f"{name} için veriler çekiliyor...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Bağlantı hatası ({url}): {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # RSS Beslemesi Ayarları
    fg = FeedGenerator()
    fg.id(url)
    fg.title(name.replace('_', ' ').upper())
    fg.author({'name': 'MKU RSS Bot'})
    fg.link(href=url, rel='alternate')
    fg.description(f'{name} için otomatik RSS beslemesi')
    fg.language('tr')

    # Sayfadaki linkleri bulma
    items = soup.find_all('a', href=True)
    added_links = set()
    count = 0
    
    for item in items:
        link = item['href']
        title = item.text.strip()
        
        if title and len(title) > 10: 
            if not link.startswith('http'):
                full_link = "https://mku.edu.tr" + link if link.startswith('/') else "https://mku.edu.tr/" + link
            else:
                full_link = link

            if full_link not in added_links:
                added_links.add(full_link)
                
                fe = fg.add_entry()
                fe.id(full_link)
                fe.title(title)
                fe.link(href=full_link)
                
                tz = pytz.timezone('Europe/Istanbul')
                fe.published(datetime.now(tz)) 
                
                count += 1
                if count >= 15: # En yeni 15 içeriği alır
                    break

    if not os.path.exists('rss_files'):
        os.makedirs('rss_files')
        
    fg.rss_file(f"rss_files/{name}.xml")
    print(f"{name}.xml oluşturuldu. Bulunan içerik: {count}")

for name, url in URLS.items():
    generate_rss(name, url)
