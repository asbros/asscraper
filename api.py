from flask import Flask, request, jsonify
from flask_cors import CORS  # Frontend ko block hone se bachane ke liye
import requests
import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)
CORS(app)  # Ye allow karega ki aapka index.html is API ko call kar sake

BASE_URL = "https://new2.hdhub4u.limo"

# HTML Fetch karne ka function (Links nikalne ke liye)
def fetch_html(url):
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'desktop': False
        }
    )
    try:
        print(f"\n[+] Fetching HTML for Links: {url}")
        response = scraper.get(url, timeout=15)
        
        if response.status_code == 403 or response.status_code == 503:
            print("[-] Error: Blocked by Cloudflare!")
            return None
            
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[-] Error fetching URL: {e}")
        return None

@app.route("/")
def home():
    return jsonify({"message": "Movie API is Running Perfectly with CORS!"})

# --- STEP 1: SEARCH MOVIE (Hidden API - Super Fast) ---
@app.route("/search")
def search_movie():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Please provide a search query. Example: /search?q=batman"})
    
    api_url = "https://search.pingora.fyi/collections/post/documents/search"
    
    params = {
        'q': query,
        'query_by': 'post_title,category,stars,director,imdb_id',
        'query_by_weights': '4,2,2,2,4',
        'sort_by': 'sort_by_date:desc',
        'limit': '15',
        'page': '1'
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://new2.hdhub4u.limo",
        "Referer": "https://new2.hdhub4u.limo/"
    }

    try:
        print(f"\n[+] Fetching search data from API for: {query}")
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({"error": "API Blocked the request."})
            
        data = response.json()
        
        if data.get('found', 0) == 0 or not data.get('hits'):
            return jsonify({"status": "success", "results_found": 0, "data": []})

        results = []
        fallback_img = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/No-Image-Placeholder.svg/315px-No-Image-Placeholder.svg.png"

        for hit in data.get('hits', []):
            doc = hit.get('document', {})
            title = doc.get('post_title', 'Unknown Title')
            link = doc.get('permalink', '')
            img = doc.get('post_thumbnail', fallback_img)

            results.append({
                "title": title, 
                "link": link, 
                "image": img
            })

        return jsonify({
            "status": "success", 
            "results_found": len(results), 
            "data": results
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# --- STEP 2: GET LINKS (Ultra Clean - Only Qualities) ---
@app.route("/get-links")
def get_links():
    movie_path = request.args.get('url', '')
    if not movie_path:
        return jsonify({"error": "Provide movie URL"})

    # Agar URL aadha hai, toh Base URL jodo
    full_url = movie_path if movie_path.startswith('http') else BASE_URL + movie_path

    soup = fetch_html(full_url)
    if not soup:
        return jsonify({"error": "Failed to fetch movie page."})

    streaming_links = []
    
    # Sirf content wale hisse me dhoondho taaki faltu links na aayein
    content_area = soup.find('div', class_=['entry-content', 'post-content', 'thecontent'])
    search_area = content_area if content_area else soup
    
    # 🔴 STRICT FILTER: Sirf ye resolutions allow honge
    valid_resolutions = ['480p', '720p', '1080p', '2160p', '4k']
    
    for a_tag in search_area.find_all('a'):
        href = a_tag.get('href', '')
        text = a_tag.text.strip()
        text_lower = text.lower()
        
        # Filters apply karna
        has_resolution = any(res in text_lower for res in valid_resolutions)
        is_clean = 'how to download' not in text_lower and 'watch online' not in text_lower
        
        if (has_resolution and 
            is_clean and 
            len(text) < 40 and 
            'movie' not in text_lower and 
            'season' not in text_lower and 
            href.startswith('http')):
            
            # Duplicates rokna
            if not any(item['link'] == href for item in streaming_links):
                streaming_links.append({
                    "quality": text, 
                    "link": href
                })

    return jsonify({
        "status": "success", 
        "movie_url": full_url, 
        "links_found": len(streaming_links),
        "links": streaming_links
    })

if __name__ == "__main__":
    print("🚀 Server starting on http://localhost:8000")
    app.run(host="0.0.0.0", port=8000)
