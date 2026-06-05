import cloudscraper
import re
import base64
import codecs
import json

def test_god_mode_bypass(url):
    print(f"\n[*] Starting God-Mode Bypass for: {url[:50]}...\n")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        # Step 1: Requesting the page with Fake Referer
        print("[⏳] Step 1: Fetching GadgetsWeb...")
        headers = {
            "Referer": "https://new2.hdhub4u.limo/", 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res1 = scraper.get(url, headers=headers, timeout=10)
        
        # Step 2: Finding the Encrypted Token
        match = re.search(r"s\(['\"]o['\"]\s*,\s*['\"]([^'\"]+)['\"]", res1.text)
        if not match:
            print("[-] Token not found! Make sure the link is FRESH (not expired).")
            return
            
        token = match.group(1)
        print(f"[+] Token Found: {token[:20]}...")
        
        # Step 3: The Decryption Chain (Double B64 -> ROT13 -> B64)
        print("[⏳] Step 2: Decrypting Vault...")
        token += "=" * ((4 - len(token) % 4) % 4)
        layer1 = base64.b64decode(token).decode('utf-8')
        
        layer1 += "=" * ((4 - len(layer1) % 4) % 4)
        layer2 = base64.b64decode(layer1).decode('utf-8')
        
        layer3 = codecs.encode(layer2, 'rot_13')
        
        layer3 += "=" * ((4 - len(layer3) % 4) % 4)
        layer4 = base64.b64decode(layer3).decode('utf-8')
        
        print("[+] Vault Opened! Extracting Original Target...")
        
        # Step 4: Parsing JSON and finding 'o'
        data = json.loads(layer4)
        if 'o' in data:
            final_b64 = data['o']
            
            # Final Base64 Decode
            final_b64 += "=" * ((4 - len(final_b64) % 4) % 4)
            final_url = base64.b64decode(final_b64).decode('utf-8')
            
            print(f"\n[🚀] SUCCESS! Bypassed in 0.1 Seconds!")
            print(f"{"="*50}")
            print(f"[🎯] FINAL HBLINKS URL: {final_url}")
            print(f"{"="*50}\n")
        else:
            print("[-] Decrypted successfully, but 'o' (Original Link) was missing.")
            print(f"JSON Output: {data}")
            
    except Exception as e:
        print(f"\n[❌] Error: {e}")

# 🔥 CRITICAL STEP: Vega App se ek dum NAYA link nikal kar yahan paste karna. 
# Purana link use karoge toh site token nahi degi.
fresh_test_url = "TUMHARA_EK_DUM_NAYA_GADGETSWEB_LINK_YAHAN_DAALO"

test_god_mode_bypass(fresh_test_url)