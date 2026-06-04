from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse
import re
import concurrent.futures

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. 47 PROVIDERS DATABASE
# ==========================================
PROVIDERS = {
    "Moviesmod": {"name": "Moviesmod", "url": "https://moviesmod.farm", "type": "wp_json"},
    "Vega": {"name": "vegamovies", "url": "https://vegamovies.mq", "type": "wp_json"},
    "UhdMovies": {"name": "UhdMovies", "url": "https://uhdmovies.rodeo", "type": "wp_json"},
    "lux": {"name": "luxmovies", "url": "https://rogmovies.club", "type": "wp_json"},
    "drive": {"name": "moviesDrive", "url": "https://new3.moviesdrives.my/", "type": "wp_json"},
    "extra": {"name": "extraMovies", "url": "https://extramovies.ist", "type": "wp_json"},
    "4khdhub": {"name": "4khdhub", "url": "https://4khdhub.link", "type": "wp_json"},
    "filmyfly": {"name": "flimyfly", "url": "https://new2.filmyfiy.org", "type": "wp_json"},
    "cinevood": {"name": "Cinevood", "url": "https://kmmovies.space", "type": "wp_json"},
    "kmmovies": {"name": "kmmovies", "url": "https://kmmovies.space", "type": "wp_json"},
    "zeefliz": {"name": "zeefliz", "url": "https://zeefliz.beer", "type": "wp_json"},
    "movies4u": {"name": "movies4u", "url": "https://movies4u.ee", "type": "wp_json"},
    "1cinevood": {"name": "cinewood", "url": "https://1cinevood.in", "type": "wp_json"},
    "moviezwap": {"name": "moviezwap", "url": "https://www.moviezwap.onl/", "type": "wp_json"},
    "hdhub": {"name": "hdhub4u", "url": "https://new2.hdhub4u.limo", "type": "pingora_api"},
    "autoEmbed": {"name": "autoEmbed", "url": "https://autoembed.cc", "type": "auto_embed"},
    "aed": {"name": "autoEmbedDrama", "url": "https://watch-drama.autoembed.cc", "type": "auto_embed"},
    "aea": {"name": "autoEmbedAnime", "url": "https://watch-anime.autoembed.cc", "type": "auto_embed"},
    "Topmovies": {"name": "Topmovies", "url": "https://moviesleech.rodeo", "type": "html_scrape"},
    "filepress": {"name": "filepress", "url": "https://new14.filepress.store", "type": "html_scrape"},
    "multi": {"name": "multimovies", "url": "https://multimovies.fyi", "type": "html_scrape"},
    "w4u": {"name": "world4ufree", "url": "https://world4ufree.tw", "type": "html_scrape"},
    "kat": {"name": "katmovieshd", "url": "https://new1.katmoviehd.cymru", "type": "html_scrape"},
    "dc": {"name": "dramacool", "url": "https://dramacool.org.ro", "type": "html_scrape"},
    "dooflix": {"name": "dooflix", "url": "https://dooflixpanel.com", "type": "html_scrape"},
    "tokyoinsider": {"name": "tokyoinsider", "url": "https://www.tokyoinsider.com", "type": "html_scrape"},
    "consumet": {"name": "consumet", "url": "https://consumet.zendax.tech", "type": "html_scrape"},
    "nfMirror": {"name": "nfMirror", "url": "https://net22.cc", "type": "html_scrape"},
    "primewire": {"name": "primewire", "url": "https://primewire.si", "type": "html_scrape"},
    "rive": {"name": "rive", "url": "https://www.rivestream.app", "type": "html_scrape"},
    "kissKh": {"name": "kissKh", "url": "https://kisskh.do", "type": "html_scrape"},
    "vadapav": {"name": "vadapav", "url": "https://vadapav.mov", "type": "html_scrape"},
    "cinemaLuxe": {"name": "cinemaLuxe", "url": "https://cinemalux.cyou", "type": "html_scrape"},
    "showbox": {"name": "showbox", "url": "https://www.showbox.media", "type": "html_scrape"},
    "animerulz": {"name": "animerulz", "url": "https://animerulz.co", "type": "html_scrape"},
    "moviesapi": {"name": "moviesapi", "url": "https://moviesapi.to", "type": "html_scrape"},
    "ridomovies": {"name": "ridomovies", "url": "https://ridomovies.tv", "type": "html_scrape"},
    "protonMovies": {"name": "protonMovies", "url": "https://m.protonmovies.space", "type": "html_scrape"},
    "dramafull": {"name": "dramafull", "url": "https://dramafull.cc", "type": "html_scrape"},
    "nfCookie": {"name": "nf cookie verify", "url": "https://userverify.netmirror.app", "type": "html_scrape"},
    "embedsu": {"name": "embedsu", "url": "https://moviemaze.cc", "type": "html_scrape"},
    "9xflix": {"name": "9xflix", "url": "https://soft-water-2a42.flixoflixx.workers.dev", "type": "html_scrape"},
    "movieBox": {"name": "MovieBox", "url": "https://api6.aoneroom.com", "type": "html_scrape"},
    "katmoviefix": {"name": "katmoviefix", "url": "https://katmoviefix.rest", "type": "html_scrape"},
    "joya9tv": {"name": "joya9tv1", "url": "https://joya9tv1.com", "type": "html_scrape"},
    "skymovieshd": {"name": "skyMovesHd", "url": "https://skymovieshd.free", "type": "html_scrape"},
    "Animeflix": {"name": "Animeflix", "url": "https://ww3.animeflix.ltd", "type": "html_scrape"}
}

# ==========================================
# 2. HELPER TOOLS
# ==========================================
def get_scraper():
    return cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).replace('&#8211;', '-').replace('&#8217;', "'").replace('&#8230;', '...')

# ==========================================
# 3. CORE SCRAPING STRATEGIES (No Garbage Logic)
# ==========================================
def strategy_wp_json(query, base_url):
    scraper = get_scraper()
    api_url = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts?search={urllib.parse.quote_plus(query)}&_embed"
    results = []
    try:
        res = scraper.get(api_url, timeout=10)
        if res.status_code == 200:
            for item in res.json():
                title = clean_html(item.get('title', {}).get('rendered', 'Unknown'))
                link = item.get('link', '')
                img = ""
                try: img = item['_embedded']['wp:featuredmedia'][0]['source_url']
                except: pass
                if link and len(title) > 2: results.append({"title": title, "link": link, "image": img})
    except Exception:
        # Error log ko chota kar diya gaya hai
        print(f"[-] Skipped {base_url} (Site Down/Blocked)")
    return results

def strategy_pingora(query, base_url):
    api_url = "https://search.pingora.fyi/collections/post/documents/search"
    params = {'q': query, 'query_by': 'post_title', 'limit': '15', 'page': '1'}
    headers = {"User-Agent": "Mozilla/5.0", "Origin": base_url, "Referer": base_url + "/"}
    results = []
    try:
        res = requests.get(api_url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            for hit in res.json().get('hits', []):
                doc = hit.get('document', {})
                title = doc.get('post_title', 'Unknown')
                link = doc.get('permalink', '')
                if link and len(title) > 2:
                    results.append({"title": title, "link": link, "image": doc.get('post_thumbnail', '')})
    except Exception:
        print(f"[-] Skipped {base_url} (Site Down/Blocked)")
    return results

def strategy_html(query, base_url):
    scraper = get_scraper()
    search_url = f"{base_url.rstrip('/')}/?s={urllib.parse.quote_plus(query)}"
    results = []
    try:
        res = scraper.get(search_url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        cards = soup.find_all(['article', 'div', 'li'], class_=['item', 'post-item', 'result-item', 'movie-card', 'post'])
        
        if not cards:
            # Agar proper cards nahi mile, toh sirf wahi links uthayenge jo images rakhte hain
            # aur sath me proper filtering apply karenge
            cards = [a for a in soup.find_all('a') if a.find('img')]
            
        unique_links = set()
        
        # In words ko contain karne wale links kachra (garbage) hote hain
        bad_keywords = ['/category/', '/genre/', '/tag/', '/author/', '/page/', 'login', 'register', 'contact']
        
        for card in cards:
            a_tag = card if card.name == 'a' else card.find('a')
            if not a_tag: continue
            
            link = a_tag.get('href', '')
            if not link or '#' in link or not link.startswith('http'): continue
            
            # Agar link me garbage keyword hai, toh yahi block kar do
            if any(bad in link.lower() for bad in bad_keywords): 
                continue
            
            title_tag = card.find(['h2', 'h3', 'div'], class_=['title', 'entry-title'])
            title = title_tag.text.strip() if title_tag else (a_tag.get('title') or a_tag.text.strip())
            
            img_tag = card.find('img') if card.name != 'a' else card.find('img')
            img = img_tag.get('src') or img_tag.get('data-src') if img_tag else ""
            
            # Title kam se kam 4 character ka hona chahiye (taaki icon wagaira block ho jaye)
            if title and len(title) > 3 and link not in unique_links:
                unique_links.add(link)
                results.append({"title": title, "link": link, "image": img})
    except Exception:
        print(f"[-] Skipped {base_url} (Site Down/Blocked)")
    return results

def strategy_autoembed(query):
    return [{"title": f"AutoEmbed requires TMDB ID. Search '{query}' on TMDB first.", "link": "", "image": ""}]

# ==========================================
# 4. MAIN API ROUTES
# ==========================================
@app.route("/")
def home():
    return jsonify({"message": "Master API is Running!", "total_providers": len(PROVIDERS), "providers_list": list(PROVIDERS.keys())})

@app.route("/search")
def search_movie():
    query = request.args.get('q', '')
    provider_keys_param = request.args.get('provider', 'hdhub')
    
    if not query: return jsonify({"error": "Provide a query."})
    
    provider_keys = []
    if provider_keys_param.lower() == 'all':
        provider_keys = list(PROVIDERS.keys())
    else:
        provider_keys = [k.strip() for k in provider_keys_param.split(',')]
        
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_provider = {}
        for key in provider_keys:
            if key not in PROVIDERS:
                continue
            prov = PROVIDERS[key]
            
            if prov['type'] == 'wp_json':
                future = executor.submit(strategy_wp_json, query, prov['url'])
            elif prov['type'] == 'pingora_api':
                future = executor.submit(strategy_pingora, query, prov['url'])
            elif prov['type'] == 'auto_embed':
                future = executor.submit(strategy_autoembed, query)
            else:
                future = executor.submit(strategy_html, query, prov['url'])
            future_to_provider[future] = prov['name']
            
        for future in concurrent.futures.as_completed(future_to_provider):
            prov_name = future_to_provider[future]
            try:
                res = future.result()
                for r in res:
                    r['provider'] = prov_name
                all_results.extend(res)
            except Exception:
                pass # Agar Threading me error aye to chup chap aage badh jao

    return jsonify({
        "status": "success", 
        "providers_searched": len(provider_keys), 
        "results_found": len(all_results), 
        "data": all_results
    })

# --- SUPER FILTERED LINK EXTRACTOR ---
@app.route("/get-links")
def get_links():
    movie_path = request.args.get('url', '')
    if not movie_path: return jsonify({"error": "Provide movie URL"})

    scraper = get_scraper()
    print(f"\n[+] Extracting Data from: {movie_path}")
    
    base_domain = urllib.parse.urlparse(movie_path).netloc
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = scraper.get(movie_path, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        content_area = soup.find('div', class_=['entry-content', 'post-content', 'thecontent', 'content-area', 'post-single-content'])
        search_area = content_area if content_area else soup
        
        streaming_links = []
        unique_urls = set()
        
        # 1. IFRAME EXTRACTOR
        for iframe in search_area.find_all('iframe'):
            src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
            if not src: continue
            if src.startswith('//'): src = 'https:' + src
            if 'youtube.com' in src or 'youtu.be' in src or 'facebook.com' in src: continue
                
            if src not in unique_urls and src.startswith('http'):
                unique_urls.add(src)
                streaming_links.append({"quality": "Direct Player", "link": src, "type": "player"})

        # 2. SERVER LINK EXTRACTOR
        player_buttons = search_area.find_all(['li', 'div', 'button', 'a'], class_=re.compile(r'dooplay|player|server|source|btn|button', re.IGNORECASE))
        for btn in player_buttons:
            url = btn.get('data-url') or btn.get('data-embed') or btn.get('data-src')
            if url and url.startswith('http') and url not in unique_urls:
                unique_urls.add(url)
                name = btn.text.strip() or "Server Link"
                streaming_links.append({"quality": f"Watch on {name}", "link": url, "type": "server_link"})

        # 3. STRICT DOWNLOAD LINKS EXTRACTOR
        valid_resolutions = ['480p', '720p', '1080p', '2160p', '4k', 'mb', 'gb']
        valid_hosts = ['drive.google', 'hubcloud', 'filepress', 'mega.nz', 'gadgetsweb', 'linkstaker']
        
        for a_tag in search_area.find_all('a'):
            href = a_tag.get('href', '')
            text = a_tag.text.strip().lower()
            
            if not href or href == '#' or 'category/' in href or 'genre/' in href:
                continue
                
            if base_domain in href and not any(res in text for res in valid_resolutions):
                continue
            
            has_resolution = any(res in text for res in valid_resolutions)
            has_valid_host = any(host in href for host in valid_hosts)
            
            if (has_resolution or has_valid_host) and "how to download" not in text:
                if href.startswith('http') and href not in unique_urls:
                    unique_urls.add(href)
                    
                    quality_text = a_tag.text.strip()
                    if not quality_text: quality_text = "Download Link"
                    if len(quality_text) > 30: quality_text = quality_text[:30] + "..."
                    
                    streaming_links.append({"quality": quality_text, "link": href, "type": "download"})

        # 4. EPISODE EXTRACTOR
        episodes = []
        ep_lists = search_area.find_all(['ul', 'div'], class_=re.compile(r'episodio|episode|ep-list|seasons', re.IGNORECASE))
        for el in ep_lists:
            for a_tag in el.find_all('a'):
                href = a_tag.get('href', '')
                text = a_tag.text.strip()
                if href.startswith('http') and len(text) > 0 and href not in [e['link'] for e in episodes]:
                    episodes.append({"episode": text, "link": href})

        return jsonify({
            "status": "success", 
            "movie_url": movie_path, 
            "links_found": len(streaming_links), 
            "links": streaming_links,
            "is_series": len(episodes) > 0,
            "episodes": episodes
        })
    except Exception as e:
        print(f"[-] Error extracting links: {e}")
        return jsonify({"error": "Failed to fetch links.", "details": str(e)})

if __name__ == "__main__":
    print("🚀 API starting on http://localhost:8000")
    app.run(host="0.0.0.0", port=8000)
