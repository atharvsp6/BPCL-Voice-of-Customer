import tweepy
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

if not BEARER_TOKEN:
    print("❌ TWITTER_BEARER_TOKEN not found in .env file")
    print("Add it to .env: TWITTER_BEARER_TOKEN=your_token_here")
    exit(1)

# Twitter/X search queries for BPCL
SEARCH_QUERIES = [
    '@BPCLimited',
    'BharatGas',
    'HelloBPCL',
    'BPCL app'
]

TARGET_COUNT = 50  # 50 tweets total

print(f"[{datetime.now()}] 🚀 Starting MASS HARVEST for Twitter/X (via API v2)...")
print(f"Targeting {TARGET_COUNT} tweets from: {', '.join(SEARCH_QUERIES)}\n")

try:
    # Initialize Tweepy client
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    
    all_tweets = []
    tweets_per_query = TARGET_COUNT // len(SEARCH_QUERIES)
    
    for idx, query in enumerate(SEARCH_QUERIES):
        print(f"  🔍 Searching for: '{query}'")
        
        try:
            # Search tweets
            tweets_response = client.search_recent_tweets(
                query=query,
                max_results=min(100, tweets_per_query),
                tweet_fields=['created_at', 'public_metrics'],
                expansions=['author_id'],
                user_fields=['username']
            )
            
            if tweets_response.data:
                # Create user lookup dictionary
                users = {user.id: user for user in tweets_response.includes['users']} if tweets_response.includes else {}
                
                for tweet in tweets_response.data:
                    author_info = users.get(tweet.author_id, {})
                    
                    tweet_obj = {
                        'reviewId': str(tweet.id),
                        'content': tweet.text,
                        'score': None,  # Will be filled by Gemini sentiment analysis
                        'at': tweet.created_at.isoformat() if tweet.created_at else '',
                        'thumbsUpCount': tweet.public_metrics['like_count'],
                        'reviewCreatedVersion': None,
                        'replyContent': None,
                        'repliedAt': None,
                        'appVersion': None,
                        'source': 'Twitter',
                        'author': getattr(author_info, 'username', 'Unknown'),
                        'retweets': tweet.public_metrics['retweet_count'],
                        'replies': tweet.public_metrics['reply_count']
                    }
                    all_tweets.append(tweet_obj)
                
                print(f"    ✅ Found {len(tweets_response.data)} tweets")
            else:
                print(f"    ⚠️  No tweets found for: '{query}'")
            
            # Add delay between queries to avoid rate limiting
            if idx < len(SEARCH_QUERIES) - 1:
                print(f"    ⏳ Waiting 5 seconds before next query...")
                time.sleep(5)
            
        except tweepy.TweepyException as e:
            if '429' in str(e):
                print(f"    ⚠️  Rate limit hit. Waiting 60 seconds...")
                time.sleep(60)
            else:
                print(f"    ❌ Twitter API Error: {e}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    # TRANSFORM
    if not all_tweets:
        raise ValueError("No tweets collected from Twitter/X")
    
    df_tweets = pd.DataFrame(all_tweets)
    
    # Remove duplicates
    df_tweets = df_tweets.drop_duplicates(subset=['reviewId'])
    
    # Reorder columns
    column_order = ['reviewId', 'content', 'score', 'at', 'thumbsUpCount', 'reviewCreatedVersion',
                    'replyContent', 'repliedAt', 'appVersion', 'source', 'author', 'retweets', 'replies']
    df_tweets = df_tweets[[col for col in column_order if col in df_tweets.columns]]
    
    # SAVE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f'reviews_twitter_{len(df_tweets)}_{timestamp}.csv'
    
    df_tweets.to_csv(output_filename, index=False)
    
    print(f"\n✅ DONE! Collected {len(df_tweets)} tweets.")
    print(f"📁 Saved to: {output_filename}")

except tweepy.TweepyException as e:
    print(f"❌ Twitter API Error: {e}")
    print("Note: Check if your Bearer Token is valid and API access is approved")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()