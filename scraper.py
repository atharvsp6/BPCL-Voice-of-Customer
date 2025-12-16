from google_play_scraper import reviews, Sort
import pandas as pd

# Setup the target
APP_ID = 'com.cgt.bharatgas'

print(f"Starting to scrape reviews for: {APP_ID} ...")

# Fetch the reviews
# We are asking for 5,000 reviews to start
result, continuation_token = reviews(
    APP_ID,
    lang='en',             # Language
    country='in',          # Country (India)
    sort=Sort.NEWEST,      # Sort by newest first
    count=5000             # How many reviews do we want?
)

# Convert the list of reviews (JSON) into a Pandas DataFrame (Table)
df = pd.DataFrame(result)

# Save to a CSV file
file_name = 'raw_reviews.csv'
df.to_csv(file_name, index=False)

print(f"Success! Scraped {len(df)} reviews and saved to {file_name}")