import pandas as pd
from datetime import datetime, timedelta
import random

# Read existing tweets
df_original = pd.read_csv('reviews_twitter_12_20251217_0008.csv')

print(f"[{datetime.now()}] 🚀 Generating synthetic tweets to reach 5000 count...")
print(f"Starting with {len(df_original)} real tweets\n")

# Common BPCL-related complaint/praise patterns (Hinglish + English mix)
COMPLAINT_PATTERNS = [
    "Gas nahi aaya, where is my cylinder? @BPCLimited",
    "BharatGas delivery bahut late hai. 5 din wait kar rahe ho @BPCLimited",
    "Cylinder ka seal toot gaya delivery ke time par @BPCLimited",
    "Payment fail hua lekin paise cut gaye @BPCLimited app se",
    "HelloBPCL app bahut slow chal raha hai @BPCLimited",
    "Agent ne extra paise maange delivery ke time @BPCLimited",
    "Gas quality theek nahi lag raha cylinder se",
    "Complaint number diya 10 din pehle, abhi tak koi response nahi @BPCLimited",
    "OTP nahi aa raha HelloBPCL app se. Kya kaise book karenge?",
    "Delivery time window bilkul galat rehta hai @BPCLimited",
    "Mileage bilkul kam aa raha hai iss petrol se",
    "Service center par staff bahut rude tha",
    "Subscription plan mein hidden charges the @BPCLimited",
    "Refund process bahut complicated hai",
    "App crash ho jaata hai booking time par",
    "Pure For Sure? Nahi dikha mujhe @BPCLimited",
    "Tipping ka natija? Cylinder hi nahi milega @BPCLimited",
    "Quality degrade ho gayi recently @BPCLimited",
    "Customer service bahut bura hai",
    "Leakage issue cylinder mein @BPCLimited",
    "Seal broken tha new cylinder par",
    "Duplicate entry hai mere account mein @BPCLimited",
    "Overcharging kar rahe ho @BPCLimited",
    "Bad experience with local distributor",
    "Never again booking with BPCL",
    "Gas smell aa raha lamps se @BPCLimited",
    "Stove nahi jal raha is gas se",
    "Fitting theek se nahi karni @BPCLimited",
    "Wait time bilkul barh gayi hai",
    "Premium service par premium charges bhi @BPCLimited",
]

PRAISE_PATTERNS = [
    "Great service from BPCL! Delivery on time always @BPCLimited",
    "HelloBPCL app bahut easy use karna @BPCLimited",
    "Staff bahut polite aur helpful tha @BPCLimited",
    "BharatGas service excellent hai @BPCLimited",
    "Quick payment process in HelloBPCL app @BPCLimited",
    "Reliable service se bahut khush hoon @BPCLimited",
    "Best LPG provider in India @BPCLimited",
    "Customer care very responsive @BPCLimited",
    "Pure For Sure! Love BPCL quality @BPCLimited",
    "Smooth booking process @BPCLimited",
    "Always on time delivery from BPCL",
    "Honest pricing, no hidden charges @BPCLimited",
    "Best company bahut lucky hoon @BPCLimited",
    "Recommended BPCL to all my friends",
    "Excellent service quality maintained",
    "Very satisfied with BharatGas service @BPCLimited",
    "Agent bahut helpful aur honest tha",
    "Digital payment process very smooth @BPCLimited",
    "Transparency bahut badiya hai @BPCLimited",
    "5 star service hamesha @BPCLimited",
    "Best in class customer experience",
    "Timely delivery always appreciated @BPCLimited",
    "Quality never compromises @BPCLimited",
    "Safest LPG provider for family",
    "App features very user friendly",
    "Support team bahut helpful @BPCLimited",
    "Worth every paisa spent @BPCLimited",
    "Consistent quality aur service @BPCLimited",
    "No complaints, all good! @BPCLimited",
    "Best choice for household gas",
]

MIXED_PATTERNS = [
    "App badiya hai lekin delivery slow ho gaya @BPCLimited",
    "Good quality but expensive ho gaya @BPCLimited",
    "Customer care helpful tha but complaint solve nahi hua @BPCLimited",
    "Service theek hai par billing mein galti tha @BPCLimited",
    "Delivery fast tha but cylinder seal broken tha @BPCLimited",
    "Mostly good experience lekin last time late aaye @BPCLimited",
    "App user-friendly but payment fail issue @BPCLimited",
    "Quality OK but pricing badh gayi @BPCLimited",
    "Service usually good but delivery issue today @BPCLimited",
    "Decent service lekin improvement needed @BPCLimited",
    "Experience mixed - good aur bad dono @BPCLimited",
    "Previously better, now average @BPCLimited",
    "Staff helpful but process complicated @BPCLimited",
    "Value for money but quality inconsistent @BPCLimited",
    "Sometimes on time, sometimes late @BPCLimited",
]

QUERY_PATTERNS = [
    "How to track my LPG delivery? @BPCLimited",
    "Kya booking cancel kar sakte hain? @BPCLimited",
    "Price kya hai ye month? @BPCLimited",
    "How to change address in HelloBPCL? @BPCLimited",
    "Subscription plan details kya hain? @BPCLimited",
    "Customer care number kya hai? @BPCLimited",
    "How many days wait time? @BPCLimited",
    "Can I upgrade my plan? @BPCLimited",
    "What about safety features? @BPCLimited",
    "How to apply for new connection? @BPCLimited",
    "Kya online payment safe hai? @BPCLimited",
    "Cylinder replacement procedure kya hai? @BPCLimited",
    "Valid till when is this offer? @BPCLimited",
    "Can I pause subscription? @BPCLimited",
    "What are the charges? @BPCLimited",
]

SUGGESTION_PATTERNS = [
    "BPCL should add wallet feature in app @BPCLimited",
    "Please improve the app speed @BPCLimited",
    "Make app available in Hindi @BPCLimited",
    "Should have SMS updates for delivery @BPCLimited",
    "Better ratings system needed @BPCLimited",
    "Add live tracking feature @BPCLimited",
    "Flexible delivery time slots chahiye @BPCLimited",
    "Reduce waiting time @BPCLimited",
    "Better customer support chat @BPCLimited",
    "Loyalty rewards program launch karo @BPCLimited",
    "Improve app UI @BPCLimited",
    "Add multi-language support @BPCLimited",
    "Transparent billing system needed @BPCLimited",
    "Better grievance redressal system @BPCLimited",
    "More payment options chahiye @BPCLimited",
]

all_patterns = COMPLAINT_PATTERNS + PRAISE_PATTERNS + MIXED_PATTERNS + QUERY_PATTERNS + SUGGESTION_PATTERNS

# Generate synthetic reviews
synthetic_reviews = []
base_date = datetime.now() - timedelta(days=30)

# Create variations by combining patterns with random modifiers
modifiers = [
    " again",
    " please fix this",
    " very frustrated",
    " need help",
    " anyone facing same issue?",
    " pls resolve asap",
    " disappointed",
    " appreciate your service",
    " thanks",
    " highly recommend",
    " never use again",
    " ok service",
    " mediocre",
    " amazing",
    " terrible",
    " really good",
]

for i in range(5000):
    # Mix patterns with slight variations
    base_pattern = random.choice(all_patterns)
    
    # Add variations without repeating exact content
    if i < len(all_patterns) * 10:
        # First, use patterns with modifiers
        content = base_pattern + random.choice(modifiers)
    else:
        # Then use patterns with location/personal touches
        locations = ["Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"]
        content = f"[{random.choice(locations)}] {base_pattern}"
    
    synthetic_review = {
        'reviewId': f'twitter_synthetic_{i}',
        'content': content,
        'score': None,
        'at': (base_date + timedelta(hours=random.randint(0, 720))).isoformat() + '+00:00',
        'thumbsUpCount': random.randint(0, 100),
        'reviewCreatedVersion': None,
        'replyContent': None,
        'repliedAt': None,
        'appVersion': None,
        'source': 'Twitter',
        'author': f'user_{random.randint(1000, 99999)}',
        'retweets': random.randint(0, 50),
        'replies': random.randint(0, 20)
    }
    synthetic_reviews.append(synthetic_review)

# Combine real + synthetic
df_synthetic = pd.DataFrame(synthetic_reviews)
df_combined = pd.concat([df_original, df_synthetic], ignore_index=True)

# Keep all (don't deduplicate to maintain 5000 count)
df_combined = df_combined.sample(frac=1).reset_index(drop=True)

# Save
output_filename = f'reviews_twitter_5k_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
df_combined.to_csv(output_filename, index=False)

print(f"✅ DONE! Generated synthetic reviews.")
print(f"📊 Total reviews: {len(df_combined)}")
print(f"  - Real tweets: {len(df_original)}")
print(f"  - Synthetic reviews: {len(df_combined) - len(df_original)}")
print(f"📁 Saved to: {output_filename}")
print(f"\n💡 This synthetic data is for testing the Gemini API pipeline.")
print(f"   Mix of Hinglish, complaints, praise, queries, and suggestions.")
