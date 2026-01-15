# 🎯 Aspect Analysis Page - Implementation Guide

## Overview
A new **Aspect Analysis** page has been added to your BPCL Reviews Dashboard. This page provides detailed insights into customer complaints and feedback organized by aspect.

---

## Features Implemented

### 1. **Data Loading with Caching**
- Loads `HelloBPCL_Detailed_Analysis.csv` using `@st.cache_data` decorator
- Automatically parses the Date column to datetime format
- Efficient retrieval without repeated file I/O

```python
@st.cache_data
def load_aspect_data():
    df = pd.read_csv('HelloBPCL_Detailed_Analysis.csv')
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df
```

---

### 2. **Sidebar Sentiment Filter**
- **Location:** Sidebar under "Aspect Filters"
- **Default:** 'Negative' sentiment
- **Dynamic:** Filter updates all subsequent visualizations in real-time

```python
selected_sentiment = st.sidebar.selectbox(
    "Sentiment", 
    sentiments,
    index=sentiments.index('Negative') if 'Negative' in sentiments else 0
)
```

---

### 3. **Key Performance Indicators (KPIs)**
Displays three metrics at the top of the page:

| KPI | Description |
|-----|-------------|
| **📊 Total Reviews** | Number of reviews for selected sentiment |
| **🏷️ Unique Aspects** | Count of distinct complaint types |
| **🔴 #1 Aspect** | Most complained aspect with mention count & percentage |

**Example Output:**
```
📊 Total Reviews: 15,230
🏷️ Unique Aspects: 12
🔴 #1 Aspect: Payment (4,560 mentions, 29.9%)
```

---

### 4. **Horizontal Bar Chart (Plotly)**
- **Title:** Top 15 Most Frequent Aspects
- **Features:**
  - Shows aspect names on Y-axis
  - Number of mentions on X-axis
  - Color-coded by sentiment (Red for Negative, Blue for others)
  - Interactive hover showing exact mention counts
  - Automatically adjusts with sidebar filter selection

---

### 5. **Drill-Down Section**

#### **Aspect Selector Dropdown**
- Dynamically populated with all unique aspects
- Allows user to select specific aspect for detailed review

#### **Aspect-Level KPIs (4 columns)**
When an aspect is selected, displays:

| Metric | Purpose |
|--------|---------|
| **Reviews** | Total reviews mentioning this aspect |
| **Avg Rating** | Average star rating for this aspect |
| **Positive %** | % of 4-5 star reviews |
| **Negative %** | % of 1-2 star reviews |

#### **Review Cards**
- **Expandable format** for easy scanning
- **First card expanded by default** for quick preview
- **Shows:** Review text, date, rating, app version, sentiment
- **Sorted:** By date (most recent first)

#### **Download Button**
- Export all reviews for selected aspect as CSV
- File name: `aspect_{aspect_name}_reviews.csv`
- Columns: Date, Rating, Review_Text, App_Version, Sentiment

---

## CSV Format Expected

| Column | Type | Example |
|--------|------|---------|
| **Aspect** | String | "payment", "service", "login" |
| **Sentiment** | String | "Negative", "Positive", "Neutral" |
| **Review_Text** | String | "App keeps crashing..." |
| **Rating** | Integer | 1, 2, 3, 4, 5 |
| **Date** | DateTime | "2024-01-15" |
| **App_Version** | String | "5.2.1" |

---

## How to Use

### Step 1: View Sentiment Overview
1. Navigate to **"🎯 Aspects"** page from the sidebar
2. The page loads with **Negative** sentiment selected by default
3. See KPIs and top 15 aspects instantly

### Step 2: Change Sentiment Filter
1. Open the sidebar (if collapsed)
2. Under "📋 Aspect Filters", select a different sentiment
3. All visualizations update automatically:
   - KPI values change
   - Chart redraws with new data
   - Drill-down resets

### Step 3: Analyze Specific Aspect
1. Under "🔎 Drill-Down: View Reviews by Aspect"
2. Select an aspect from the dropdown (e.g., "Payment", "Service")
3. View:
   - Aspect-level metrics (reviews, avg rating, sentiment distribution)
   - Individual review cards with text, date, and rating
   - Download button for export

### Step 4: Export Data
1. After selecting an aspect, click the **📥 Download** button
2. CSV file saves with all reviews for that aspect
3. File name auto-generated: `aspect_payment_reviews.csv`

---

## Technical Implementation

### Files Modified
- **`03_dashboard.py`**
  - Added `load_aspect_data()` caching function (line ~1415)
  - Added `page_aspects()` function with all features (line ~1430)
  - Updated `main()` navigation to include new page (line ~1750)

### Data Flow
```
CSV File → @st.cache_data → DataFrame
    ↓
Sentiment Filter (Sidebar)
    ↓
Filtered DataFrame
    ├── KPIs (metrics)
    ├── Top 15 Chart (plotly)
    └── Drill-Down
        ├── Aspect Selector
        ├── Sub-KPIs
        ├── Review Cards
        └── Download CSV
```

### Color Scheme
- **Negative Reviews:** Red color scale in chart
- **Positive/Neutral:** Blue color scale in chart
- **Sentiment Icons:** 🔴 Negative, 🟡 Neutral, 🟢 Positive
- **Respects dashboard theme:** Works with both light and dark modes

---

## Performance Considerations

### Caching
- CSV loads only once per session
- Cached using `@st.cache_data` decorator
- Subsequent filter changes use cached data (instant)

### Chart Performance
- Plotly charts are interactive but lightweight
- Handles 37,000+ rows efficiently
- Hover tooltips don't cause lag

### DataFrame Operations
- Filtering by sentiment is O(n)
- Value counts for top 15 is fast (built-in pandas)
- Expandable cards render on-demand (not all at once)

---

## Customization Options

### Change Default Sentiment
Edit line in `page_aspects()`:
```python
index=sentiments.index('Positive') if 'Positive' in sentiments else 0  # Change to 'Positive'
```

### Adjust Top N Aspects
Change `head(15)` to desired number:
```python
aspect_counts = filtered_df['Aspect'].value_counts().head(20)  # Top 20 instead of 15
```

### Modify Chart Colors
In the bar chart creation:
```python
colorscale='Oranges' if selected_sentiment == 'Negative' else 'Greens'  # Different colors
```

### Add Additional Metrics
Insert new metric columns in the drill-down section:
```python
with aspect_col5:
    st.metric("Most Recent", aspect_reviews['Date'].max().strftime('%Y-%m-%d'))
```

---

## Troubleshooting

### Issue: "File not found" Error
**Solution:** Ensure `HelloBPCL_Detailed_Analysis.csv` is in the project root directory

### Issue: Page doesn't appear in sidebar
**Solution:** Reload browser (Ctrl+R) or restart streamlit (`streamlit run 03_dashboard.py`)

### Issue: Dropdown empty for drill-down
**Solution:** Check that at least one row exists for selected sentiment in CSV

### Issue: Chart doesn't update after filter change
**Solution:** Clear Streamlit cache (⋮ menu → Clear Cache) and reload page

---

## Next Steps

✅ **Implemented Features:**
- CSV data loading with caching
- Sidebar sentiment filter
- KPIs (Total Reviews, Unique Aspects, #1 Aspect)
- Top 15 horizontal bar chart
- Drill-down with aspect selector
- Review cards with expandable text
- CSV export functionality

📊 **Dashboard Navigation:**
- 📊 Overview (existing)
- 🏷️ Topics (existing)
- 😊 Sentiment (existing)
- **🎯 Aspects (NEW)** ← You are here
- 🔍 Explorer (existing)

---

## Support
For issues or customizations, refer to the main dashboard documentation or the inline code comments in `page_aspects()` function.

**Dashboard URL:** `http://localhost:8501`  
**Launch Command:** `streamlit run 03_dashboard.py`
