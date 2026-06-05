from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse
import re
import base64
import concurrent.futures

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. PROVIDER DATABASE
# ==========================================
PROVIDERS = {
    "hdhub": {"name": "hdhub4u", "url": "https://new2.hdhub4u.limo", "type": "pingora_api"}
}

def get_scraper():
    return cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def is_match(query, title):
    q_words = re.sub(r'[^a-zA-Z0-9\s]', ' ', query.lower()).split()
    t_words = re.sub(r'[^a-zA-Z0-9\s]', ' ', title.lower())
    return all(word in t_words for word in q_words)

# ==========================================
# 2. THE BYPASS ENGINE (EXTRACTORS)
# ==========================================
def extract_hubcloud_ultimate(url, scraper):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        res1 = scraper.get(url, headers=headers, timeout=10)
        soup1 = BeautifulSoup(res1.text, 'html.parser')
        token_link = None
        for a in soup1.find_all('a', href=True):
            if 'token=' in a['href'] or 'gamerxyt' in a['href'] or 'dl.php' in a['href']:
                token_link = a['href']
                break
        if not token_link: return url

        res2 = scraper.get(token_link, headers={"Referer": url, **headers}, timeout=10)
        soup2 = BeautifulSoup(res2.text, 'html.parser')
        pixel_link = None
        for a in soup2.find_all('a', href=True):
            if 'pixel.hubcloud' in a['href'] or re.search(r'\d+\.\d+\.\d+\.\d+', a['href']) or a['href'].endswith(('.mkv', '.mp4')):
                pixel_link = a['href']
                break
        
        if not pixel_link:
            meta = soup2.find('meta', attrs={'http-equiv': 'refresh'})
            if meta and 'url=' in meta.get('content', '').lower():
                pixel_link = meta.get('content').split('url=')[-1].strip()
        if not pixel_link: return url

        res3 = scraper.get(pixel_link, stream=True, timeout=(5, 10))
        raw_url = res3.url
        res3.close() # Free connection immediately
        
        if 'link=' in raw_url:
            raw_url = raw_url.split('link=')[-1]
            raw_url = urllib.parse.unquote(raw_url)
            
        return raw_url
    except Exception:
        return url

def extract_hubdrive(url, scraper):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = scraper.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        hubcloud_url = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.lower()
            if 'hubcloud' in href or 'hubcloud' in text:
                hubcloud_url = href
                break
                
        if hubcloud_url:
            return extract_hubcloud_ultimate(hubcloud_url, scraper)
        return url
    except Exception:
        return url

def extract_hubcdn(url, scraper):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        # FIX: allow_redirects=False stops cloudscraper from hanging on the timer JS
        res1 = scraper.get(url, headers=headers, timeout=10, allow_redirects=False)
        redirect_url = None
        
        # Search for the hidden token
        match = re.search(r'var\s+reurl\s*=\s*["\'](https?://[^"\']+)["\']', res1.text)
        if match:
            redirect_url = match.group(1)
        else:
            urls = re.findall(r'(https?://[^\s"\']+)', res1.text)
            for u in urls:
                if 'inventoryidea' in u or 'homelander' in u or '?r=' in u:
                    redirect_url = u
                    break

        if not redirect_url or '?r=' not in redirect_url:
            return url
            
        b64_token = redirect_url.split('?r=')[-1].split('&')[0]
        b64_token += "=" * ((4 - len(b64_token) % 4) % 4)
        decoded_url = base64.b64decode(b64_token).decode('utf-8')
        
        final_target = decoded_url
        if 'link=' in decoded_url:
            final_target = urllib.parse.unquote(decoded_url.split('link=')[-1])
            
        if 'obsession' in final_target or 'hubcloud' in final_target:
            return extract_hubcloud_ultimate(final_target, scraper)
            
        return final_target
    except Exception as e:
        return url

def decode_hblinks(url, scraper):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = scraper.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        extracted = []
        unique = set()
        
        content = soup.find('div', class_=['entry-content', 'post-content', 'thecontent'])
        search_area = content if content else soup
        current_domain = urllib.parse.urlparse(url).netloc
        
        for a in search_area.find_all('a', href=True):
            href = a['href']
            text = a.text.strip()
            if not href.startswith('http') or current_domain in href: continue
                
            if href not in unique:
                unique.add(href)
                server_name = text if len(text) > 2 else urllib.parse.urlparse(href).netloc
                extracted.append({"quality": server_name, "original_link": href, "type": "server_link"})
        return extracted
    except:
        return []

# ==========================================
# 3. CORE SCRAPING STRATEGY (SEARCH)
# ==========================================
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
                title = doc.get('post_title', '')
                link = doc.get('permalink', '')
                if link and len(title) > 2 and is_match(query, title):
                    if link.startswith('/'): link = base_url.rstrip('/') + link
                    results.append({"title": title, "link": link, "image": doc.get('post_thumbnail', '')})
    except:
        pass
    return results

# ==========================================
# 4. MAIN API ROUTES
# ==========================================
@app.route("/")
def home():
    return jsonify({"message": "Vega App Custom Provider API is Running!", "status": "Active"})

@app.route("/search")
def search_movie():
    query = request.args.get('q', '')
    if not query: return jsonify({"error": "Provide a search query."})
    
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(strategy_pingora, query, p['url']): p['name'] for p in PROVIDERS.values()}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            for r in res: r['provider'] = futures[future]
            all_results.extend(res)
    return jsonify({"status": "success", "results_found": len(all_results), "data": all_results})

@app.route("/get-links")
def get_links():
    target_url = request.args.get('url', '')
    if not target_url: return jsonify({"error": "Provide URL parameter."})

    scraper = get_scraper()

    if 'hblinks' in target_url.lower():
        print(f"\n[🚀] Starting Hub Page Decode: {target_url}")
        server_links = decode_hblinks(target_url, scraper)
        print(f"[✅] Found {len(server_links)} servers on page. Starting bypass engine...")
        
        final_data = []
        
        # ZOMBIE KILLER FIX: Removed "with" block to prevent background thread lock
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        future_map = {}
        
        for item in server_links:
            link_url = item['original_link'].lower()
            print(f"[⏳] Queuing Bypass for: {item['quality']} -> {link_url}")
            
            thread_scraper = get_scraper() 
            
            if 'hubcloud' in link_url:
                future = executor.submit(extract_hubcloud_ultimate, item['original_link'], thread_scraper)
            elif 'hubcdn' in link_url:
                future = executor.submit(extract_hubcdn, item['original_link'], thread_scraper)
            elif 'hubdrive' in link_url:
                future = executor.submit(extract_hubdrive, item['original_link'], thread_scraper)
            else:
                item['final_link'] = item['original_link']
                item['is_bypassed'] = False
                final_data.append(item)
                continue
                
            future_map[future] = item
                
        # Har ek thread ka result check kar rahe hain
        for future, item in future_map.items():
            try:
                # Sirf 15 seconds ka strict wait karega
                bypassed_link = future.result(timeout=15) 
                item['final_link'] = bypassed_link
                item['is_bypassed'] = True if bypassed_link != item['original_link'] else False
                
                if item['is_bypassed']:
                    print(f"[🎯] SUCCESS: Bypassed {item['quality']}!")
                else:
                    print(f"[⚠️] SKIPPED: Bypasser returned original link for {item['quality']}")
                    
            except concurrent.futures.TimeoutError:
                print(f"[⏱️] TIMEOUT ZOMBIE: {item['quality']} is stuck! Moving on without it.")
                item['final_link'] = item['original_link']
                item['is_bypassed'] = False
            except Exception as e:
                print(f"[❌] ERROR in {item['quality']}: {str(e)}")
                item['final_link'] = item['original_link']
                item['is_bypassed'] = False
                
            final_data.append(item)
            
        # THE MAGIC LOCK-BREAKER: Background threads ko force chhod do, app ko aage badhao!
        executor.shutdown(wait=False)
            
        print(f"[🏁] FINISHED processing all servers. Sending data to browser.\n")
        return jsonify({"status": "success", "links_found": len(final_data), "data": final_data})

    else:
        try:
            base_domain = urllib.parse.urlparse(target_url).netloc.replace('www.', '')
            core_name = base_domain.split('.')[-2] if len(base_domain.split('.')) >= 2 else base_domain
            
            headers = {"User-Agent": "Mozilla/5.0"}
            res = scraper.get(target_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            content_area = soup.find('div', class_=['entry-content', 'post-content', 'thecontent'])
            search_area = content_area if content_area else soup
            
            links = []
            unique = set()
            valid_hosts = ['mega.nz', 'gadgetsweb', 'linkstaker', 'vcloud', 'hubcloud']
            quality_keywords = ['480p', '720p', '1080p', '2160p', '4k', 'hevc', 'x264', 'mb', 'gb']
            
            for a in search_area.find_all('a', href=True):
                href = a['href']
                text_lower = a.text.lower()
                
                if href == '#' or href.startswith('/') or core_name in href.lower(): continue
                
                has_valid_host = any(h in href.lower() for h in valid_hosts)
                has_download_text = 'download' in text_lower
                has_quality_text = any(q in text_lower for q in quality_keywords)
                
                if (has_valid_host or has_download_text or has_quality_text) and href.startswith('http'):
                    if href not in unique:
                        unique.add(href)
                        links.append({"quality": a.text.strip()[:35], "url": href, "type": "intermediate_link"})
                        
            return jsonify({"status": "success", "links_found": len(links), "data": links})
        except Exception as e:
            return jsonify({"error": str(e)})

if __name__ == "__main__":
    print("🚀 Ultimate API v4.2 (Zombie Killer Edition) is Running on http://localhost:8000")
    app.run(host="0.0.0.0", port=8000)