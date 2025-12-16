from google_play_scraper import Sort, reviews
import pandas as pd
from datetime import datetime

APP_ID =  'com.cgt.bharatgas'
TARGET_COUNT = 5000 

print(f"[{datetime.now()}] 🚀 Starting MASS HARVEST for Google Play...")
print(f"Targeting {TARGET_COUNT} reviews. This may take 1-2 minutes...")

try:
    # FETCH
    result, _ = reviews(
        APP_ID,
        lang='en',
        country='in',
        sort=Sort.NEWEST,
        count=TARGET_COUNT
    )

    # TRANSFORM
    df = pd.DataFrame(result)

    # Guard against API shape changes or empty responses
    # Critical columns for analysis + metadata for deduplication and trend tracking
    expected_cols = ['reviewId', 'content', 'score', 'at', 'thumbsUpCount', 'reviewCreatedVersion', 
                     'replyContent', 'repliedAt', 'appVersion']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None  # fill missing columns so selection does not fail

    if df.empty:
        raise ValueError("No reviews returned from Google Play API")

    df_clean = df[expected_cols].copy()
    df_clean['source'] = 'GooglePlay'

    # SAVE (With Timestamp to prevent overwriting)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f'reviews_google_10k_{timestamp}.csv'
    
    df_clean.to_csv(output_filename, index=False)
    
    print(f"✅ DONE! Collected {len(df_clean)} reviews.")
    print(f"📁 Saved to: {output_filename}")

except Exception as e:
    print(f"❌ Error: {e}")