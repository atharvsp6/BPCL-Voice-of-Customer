import requests
import pandas as pd
from datetime import datetime
import time

APP_ID = '594797915'  # HelloBPCL on Apple App Store
COUNTRY = 'in'
TARGET_COUNT = 5000

print(f"[{datetime.now()}] 🚀 Starting MASS HARVEST for Apple App Store...")
print(f"Note: Apple limits free API access. Fetching available reviews...")

try:
    # FETCH - Using Apple App Store RSS feed
    reviews_list = []
    
    # Apple's RSS feed URL
    url = f"https://itunes.apple.com/{COUNTRY}/rss/customerreviews/id/{APP_ID}/sortBy=mostRecent/json"
    
    print(f"  📄 Fetching reviews from Apple RSS feed...")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Extract reviews from the feed
    if 'feed' in data and 'entry' in data['feed']:
        entries = data['feed']['entry']
        
        # Handle both single entry and list of entries
        if not isinstance(entries, list):
            entries = [entries]
        
        for entry in entries:
            # Skip the first entry if it's metadata
            if 'id' not in entry or 'label' not in entry['id']:
                continue
                
            review = {
                'reviewId': entry.get('id', {}).get('label', f'apple_{len(reviews_list)}'),
                'content': entry.get('content', {}).get('label', ''),
                'score': int(entry.get('rating', {}).get('label', 0)),
                'at': entry.get('updated', {}).get('label', ''),
                'thumbsUpCount': 0,
                'reviewCreatedVersion': entry.get('im:version', {}).get('label', None),
                'replyContent': None,
                'repliedAt': None,
                'appVersion': None,
                'source': 'AppleStore'
            }
            reviews_list.append(review)
    
    # TRANSFORM
    if not reviews_list:
        print("⚠️  No reviews found. Apple RSS feed may be unavailable or empty.")
        print("Note: Apple Store scraping has strict limitations. Consider manual collection.")
        raise ValueError("Failed to fetch reviews from Apple App Store")
    
    df_clean = pd.DataFrame(reviews_list)
    
    # SAVE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f'reviews_apple_{len(reviews_list)}_{timestamp}.csv'
    
    df_clean.to_csv(output_filename, index=False)
    
    print(f"✅ DONE! Collected {len(df_clean)} reviews from Apple App Store.")
    print(f"📁 Saved to: {output_filename}")
    print(f"\nNote: Apple limits free review access to ~500-1000 most recent reviews.")
    print(f"For full {TARGET_COUNT} reviews, consider using iTunes API with authentication.")

except requests.exceptions.RequestException as e:
    print(f"❌ Network Error: {e}")
    print("Note: Apple may be blocking requests. Try again later.")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()