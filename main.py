import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import os
import pytz
from datetime import datetime
import urllib3

# SSL sertifika hatalarını görmezden gelmek için
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    
    # Üniversite sitelerini kandırmak için daha gerçekçi bir tarayıcı kimliği
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
    except Exception as e:
        print(f"Bağlantı hatası ({url}): {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    fg = FeedGenerator()
    fg.id(url)
    fg.title(name.replace('_', ' ').upper())
    fg.author({'name': 'MKU RSS Bot'})
    fg.link(href=url, rel='alternate')
    fg.description(f'{name} için otomatik RSS beslemesi')
    fg.language('tr')

    added_links = set()
    count = 0
    
    # Sayfadaki tüm linkleri bul
    for item in soup.find_all('a', href=True):
        link = item['href']
        
        # Gereksiz sistem linklerini (javascript, tel, mailto vb.) atla
        if link.startswith(('#', 'javascript', 'mailto', 'tel')) or len(link) < 3:
            continue
            
        # Linkin metnini al
        title = item.text.strip()
        
        # Eğer link boşsa veya sadece "Tıklayın" yazıyorsa, bir üst kutudaki asıl metni çek
        if len(title) < 15:
            if item.parent:
                title = item.parent.text.strip()
                
        # Metindeki fazla boşlukları temizle
        title = " ".join(title.split())
        
        # Metin yeterince uzunsa (gerçek bir haber başlığıysa) işleme al
        if len(title) > 15 and len(title) < 300: 
            
            # Ana sayfa, iletişim gibi menü butonlarını filtrele
            lower_title = title.lower()
            ignore_words = ["ana sayfa", "hakkımızda", "iletişim", "misyon", "vizyon", "akademik", "öğrenci"]
            if any(word in lower_title for word in ignore_words) and len(title) < 30:
                continue

            # Yarım linkleri tam üniversite linkine çevir
            if not link.startswith('http'):
                full_link = "https://mku.edu.tr/" + link.lstrip('/')
            else:
                full_link = link

            if "mku.edu.tr" in full_link and full_link not in added_links:
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
