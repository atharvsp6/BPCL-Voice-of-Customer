"""
BPCL Reviews - Enhanced Multi-Page Analytics Dashboard
======================================================
Features:
- Multi-page layout (Overview, Topics, Sentiment, Data Explorer)
- Keyword & semantic search
- Advanced visualizations (density, violin plots, heatmaps)
- Dark/Light theme toggle
- CSV export for filtered data
- Search across reviews

Launch with: streamlit run 03_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from collections import Counter
import re
from datetime import datetime, timedelta

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="BPCL Reviews Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SESSION STATE & THEME
# =============================================================================
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def get_theme_colors():
    """Get colors based on current theme"""
    if st.session_state.theme == 'dark':
        return {
            'bg': '#0E1117',
            'secondary_bg': '#161B22',
            'text': '#C9D1D9',
            'plot_bg': 'rgba(22, 27, 34, 0.7)',
            'grid': 'rgba(48, 54, 61, 0.5)',
            'positive': '#3FB950',
            'negative': '#F85149',
            'neutral': '#79C0FF'
        }
    else:
        return {
            'bg': '#FFFFFF',
            'secondary_bg': '#F0F2F6',
            'text': '#262730',
            'plot_bg': 'rgba(255, 255, 255, 0.7)',
            'grid': 'rgba(200, 200, 200, 0.3)',
            'positive': '#10b981',
            'negative': '#ef4444',
            'neutral': '#f59e0b'
        }

def apply_theme_css():
    """Apply theme-specific CSS"""
    theme_colors = get_theme_colors()
    st.markdown(f"""
    <style>
        :root {{
            --bg-color: {theme_colors['bg']};
            --secondary-bg: {theme_colors['secondary_bg']};
            --text-color: {theme_colors['text']};
        }}
        
        .main-header {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        
        .sub-header {{
            font-size: 1rem;
            opacity: 0.8;
            margin-bottom: 2rem;
        }}
        
        .metric-card {{
            background-color: {theme_colors['secondary_bg']};
            padding: 1.2rem;
            border-radius: 0.75rem;
            border: 1px solid rgba(28, 131, 225, 0.2);
        }}
        
        div[data-testid="stSidebarContent"] {{
            background-color: {theme_colors['secondary_bg']};
        }}
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
            font-weight: 600;
        }}
        
        .js-plotly-plot {{
            background: transparent !important;
        }}
    </style>
    """, unsafe_allow_html=True)

apply_theme_css()

# =============================================================================
# DATA LOADING & CACHING
# =============================================================================
@st.cache_data
def load_data():
    """Load the enriched dataset with sentiment and topic labels"""
    try:
        df = pd.read_csv('df_final_enriched.csv')
        
        # Parse dates
        if 'at' in df.columns:
            df['at'] = pd.to_datetime(df['at'], errors='coerce')
            df['month_year'] = df['at'].dt.to_period('M').astype(str)
            df['year'] = df['at'].dt.year
            df['month'] = df['at'].dt.month
            df['week'] = df['at'].dt.isocalendar().week
        
        # Ensure required columns exist
        if 'Topic_Label' not in df.columns and 'dominant_topic' in df.columns:
            df['Topic_Label'] = 'Topic ' + (df['dominant_topic'] + 1).astype(str)
        
        return df
    except FileNotFoundError:
        st.error("⚠️ Data file 'df_final_enriched.csv' not found.")
        return None

@st.cache_data
def load_confusion_matrix():
    """Load confusion matrix data from sentiment analysis"""
    try:
        with open('confusion_matrix_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@st.cache_data
def load_topic_keywords():
    """Load topic keyword mappings"""
    default_keywords = {
        "1": ["login", "app", "open", "otp", "verification"],
        "2": ["payment", "transaction", "money", "account", "bank"],
        "3": ["update", "version", "new", "work", "crash"],
        "4": ["reward", "point", "redeem", "offer", "discount"]
    }
    try:
        with open('topic_keywords.json', 'r') as f:
            data = json.load(f)
            return data.get('negative_topics', default_keywords)
    except FileNotFoundError:
        return default_keywords

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def format_topic_label(topic_label, topic_keywords):
    """Format topic label with keywords"""
    if not topic_label or pd.isna(topic_label):
        return "Unknown"
    
    match = re.search(r'(\d+)', str(topic_label))
    if match:
        topic_num = match.group(1)
        if topic_num in topic_keywords:
            keywords = ', '.join(topic_keywords[topic_num][:3])
            return f"Topic {topic_num} ({keywords}...)"
    
    return str(topic_label)

def get_top_keywords(texts, n=10):
    """Extract top keywords from texts"""
    stop_words = {'the', 'a', 'an', 'is', 'it', 'to', 'and', 'of', 'for', 'in', 'on', 'with', 
                  'this', 'that', 'app', 'i', 'my', 'me', 'not', 'very', 'good', 'bad', 'nice',
                  'like', 'just', 'now', 'would', 'could', 'get', 'go', 'want', 'see', 'use'}
    
    all_words = []
    for text in texts:
        if pd.notna(text):
            words = re.findall(r'\b[a-z]{3,}\b', str(text).lower())
            all_words.extend([w for w in words if w not in stop_words])
    
    word_counts = Counter(all_words)
    return word_counts.most_common(n)

def search_reviews(df, query):
    """Search reviews by keyword"""
    if not query:
        return df
    
    query_lower = query.lower()
    mask = df['content'].str.lower().str.contains(query_lower, na=False)
    return df[mask]

def create_density_plot(df, column, title):
    """Create density plot"""
    colors = get_theme_colors()
    
    fig = px.histogram(df, x=column, nbins=50, marginal="box",
                       title=title,
                       color_discrete_sequence=[colors['neutral']])
    
    fig.update_layout(
        height=300,
        showlegend=False,
        plot_bgcolor=colors['plot_bg'],
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_gridcolor=colors['grid']
    )
    
    return fig

def create_violin_plot(df, y_col, x_col, title):
    """Create violin plot for rating distribution"""
    colors = get_theme_colors()
    
    fig = px.violin(df, y=y_col, x=x_col, box=True, points="outliers",
                    title=title)
    
    fig.update_layout(
        height=350,
        plot_bgcolor=colors['plot_bg'],
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_gridcolor=colors['grid']
    )
    
    return fig

def create_sentiment_heatmap(df, topic_keywords):
    """Create sentiment vs topic heatmap"""
    colors = get_theme_colors()
    
    if 'Topic_Label' in df.columns and 'ai_sentiment' in df.columns:
        heatmap_data = pd.crosstab(df['ai_sentiment'], df['Topic_Label'], normalize='index') * 100
        
        fig = px.imshow(
            heatmap_data.values,
            x=heatmap_data.columns.tolist(),
            y=heatmap_data.index.tolist(),
            color_continuous_scale='RdYlGn',
            labels=dict(color='% Distribution'),
            title='Sentiment Distribution by Topic (%)'
        )
        
        fig.update_layout(
            height=350,
            plot_bgcolor=colors['plot_bg'],
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
    
    return None

def create_gauge_chart(value, title="Sentiment Health"):
    """Create gauge chart"""
    normalized = (value + 1) * 50
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=normalized,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18}},
        number={'font': {'size': 36}, 'suffix': '%'},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#3b82f6"},
            'bgcolor': "rgba(128, 128, 128, 0.1)",
            'steps': [
                {'range': [0, 33], 'color': 'rgba(239, 68, 68, 0.2)'},
                {'range': [33, 66], 'color': 'rgba(250, 204, 21, 0.2)'},
                {'range': [66, 100], 'color': 'rgba(16, 185, 129, 0.2)'}
            ]
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=30, r=30, t=60, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def export_to_csv(df):
    """Export filtered dataframe to CSV"""
    return df.to_csv(index=False).encode('utf-8')

# =============================================================================
# SIDEBAR CONFIGURATION
# =============================================================================
def setup_sidebar_filters(df, topic_keywords):
    """Setup sidebar with filters and theme toggle"""
    
    st.sidebar.markdown("## 🎛️ Dashboard Controls")
    
    # Theme toggle
    st.sidebar.markdown("### 🎨 Theme")
    theme_col1, theme_col2 = st.sidebar.columns(2)
    with theme_col1:
        if st.button("☀️ Light", use_container_width=True, 
                    key="light_theme"):
            st.session_state.theme = 'light'
            st.rerun()
    with theme_col2:
        if st.button("🌙 Dark", use_container_width=True,
                    key="dark_theme"):
            st.session_state.theme = 'dark'
            st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filters")
    
    # Search functionality
    search_query = st.sidebar.text_input("🔎 Search reviews (keywords):")
    
    # Version filter
    versions = ['All'] + sorted(df['appVersion'].dropna().unique().tolist(), 
                               key=lambda x: [int(p) if p.isdigit() else 0 for p in str(x).split('.')])
    selected_version = st.sidebar.selectbox("📱 App Version", versions)
    
    # Date range filter
    if 'at' in df.columns:
        min_date = df['at'].min()
        max_date = df['at'].max()
        date_range = st.sidebar.date_input(
            "📅 Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        date_range = None
    
    # Topic filter
    if 'Topic_Label' in df.columns:
        raw_topics = ['All'] + sorted(df['Topic_Label'].dropna().unique().tolist())
        topic_display = ['All'] + [format_topic_label(t, topic_keywords) for t in raw_topics[1:]]
        selected_topic_idx = st.sidebar.selectbox("🏷️ Topic", range(len(topic_display)), 
                                                 format_func=lambda x: topic_display[x])
        selected_topic = raw_topics[selected_topic_idx]
    else:
        selected_topic = 'All'
    
    # Sentiment filter
    sentiments = ['All', 'Negative', 'Neutral', 'Positive']
    selected_sentiment = st.sidebar.selectbox("😊 Sentiment", sentiments)
    
    # Rating filter
    if 'score' in df.columns:
        min_rating, max_rating = st.sidebar.slider(
            "⭐ Rating Range",
            min_value=int(df['score'].min()),
            max_value=int(df['score'].max()),
            value=(int(df['score'].min()), int(df['score'].max()))
        )
    else:
        min_rating, max_rating = None, None
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_query:
        filtered_df = search_reviews(filtered_df, search_query)
    
    if selected_version != 'All':
        filtered_df = filtered_df[filtered_df['appVersion'] == selected_version]
    
    if selected_topic != 'All':
        filtered_df = filtered_df[filtered_df['Topic_Label'] == selected_topic]
    
    if selected_sentiment != 'All':
        filtered_df = filtered_df[filtered_df['ai_sentiment'] == selected_sentiment]
    
    if min_rating is not None and max_rating is not None:
        filtered_df = filtered_df[(filtered_df['score'] >= min_rating) & (filtered_df['score'] <= max_rating)]
    
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df['at'].dt.date >= start_date) & 
                                (filtered_df['at'].dt.date <= end_date)]
    
    # Sidebar stats
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Dataset Stats")
    st.sidebar.metric("Total Reviews", f"{len(df):,}")
    st.sidebar.metric("Filtered Reviews", f"{len(filtered_df):,}")
    st.sidebar.metric("Filter Coverage", f"{len(filtered_df)/len(df)*100:.1f}%")
    
    # Export button
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Export")
    csv = export_to_csv(filtered_df)
    st.sidebar.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=csv,
        file_name=f"bpcl_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    return filtered_df, search_query

# =============================================================================
# PAGE: OVERVIEW
# =============================================================================
def page_overview(df, topic_keywords):
    """Overview page with key metrics and gauges"""
    filtered_df, search_query = setup_sidebar_filters(df, topic_keywords)
    
    st.markdown('<h1 class="main-header">📊 BPCL Reviews Analytics Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Sentiment Analysis & Topic Insights</p>', unsafe_allow_html=True)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        st.metric("🎯 Avg Sentiment", f"{avg_sentiment:.3f}", 
                 "Positive" if avg_sentiment > 0 else "Negative")
    
    with col2:
        neg_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Negative'])
        neg_pct = neg_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🔴 Negative", f"{neg_count:,}", f"{neg_pct:.1f}%")
    
    with col3:
        pos_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Positive'])
        pos_pct = pos_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🟢 Positive", f"{pos_count:,}", f"{pos_pct:.1f}%")
    
    with col4:
        neu_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Neutral'])
        neu_pct = neu_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🟡 Neutral", f"{neu_count:,}", f"{neu_pct:.1f}%")
    
    st.markdown("---")
    
    # Sentiment gauge and distribution
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### 🌡️ Sentiment Health Gauge")
        global_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        gauge_fig = create_gauge_chart(global_sentiment, "Sentiment Score")
        st.plotly_chart(gauge_fig, use_container_width=True)
    
    with col_right:
        st.markdown("### 📊 Sentiment Distribution")
        sentiment_counts = filtered_df['ai_sentiment'].value_counts()
        fig_dist = px.pie(values=sentiment_counts.values, names=sentiment_counts.index,
                         title="Overall Sentiment Breakdown",
                         color_discrete_map={'Positive': '#10b981', 'Negative': '#ef4444', 'Neutral': '#f59e0b'})
        fig_dist.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    
    # Timeline
    if 'at' in filtered_df.columns and len(filtered_df) > 0:
        st.markdown("### 📈 Sentiment Trends Over Time")
        daily_sentiment = filtered_df.groupby(filtered_df['at'].dt.date).agg({'sentiment_score': 'mean'}).reset_index()
        
        fig_timeline = px.line(
            daily_sentiment,
            x='at', y='sentiment_score',
            title="Daily Average Sentiment Trend",
            markers=True
        )
        fig_timeline.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_timeline, use_container_width=True)

# =============================================================================
# PAGE: TOPICS
# =============================================================================
def page_topics(df, topic_keywords):
    """Topics analysis page"""
    filtered_df, search_query = setup_sidebar_filters(df, topic_keywords)
    
    st.markdown('<h1 class="main-header">🏷️ Topic Analysis</h1>', unsafe_allow_html=True)
    
    if 'Topic_Label' not in filtered_df.columns:
        st.error("Topic data not available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Topic Distribution")
        topic_counts = filtered_df['Topic_Label'].value_counts()
        fig_topics = px.bar(x=topic_counts.values, y=topic_counts.index,
                           orientation='h', title="Topics by Review Count")
        fig_topics.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_topics, use_container_width=True)
    
    with col2:
        st.markdown("### 🎯 Topic-Sentiment Heatmap")
        fig_heatmap = create_sentiment_heatmap(filtered_df, topic_keywords)
        if fig_heatmap:
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.markdown("---")
    
    # Topic-specific analysis
    st.markdown("### 🔍 Topic Deep Dive")
    
    if 'Topic_Label' in filtered_df.columns:
        raw_topics = sorted(filtered_df['Topic_Label'].dropna().unique().tolist())
        selected_topic = st.selectbox("Select Topic:", 
                                     [format_topic_label(t, topic_keywords) for t in raw_topics],
                                     key="topic_deepdive")
        
        # Find original topic label
        topic_idx = [format_topic_label(t, topic_keywords) for t in raw_topics].index(selected_topic)
        selected_topic_label = raw_topics[topic_idx]
        
        topic_df = filtered_df[filtered_df['Topic_Label'] == selected_topic_label]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Reviews", len(topic_df))
        with col2:
            pos_pct = len(topic_df[topic_df['ai_sentiment'] == 'Positive']) / len(topic_df) * 100
            st.metric("Positive %", f"{pos_pct:.1f}%")
        with col3:
            neg_pct = len(topic_df[topic_df['ai_sentiment'] == 'Negative']) / len(topic_df) * 100
            st.metric("Negative %", f"{neg_pct:.1f}%")
        
        st.markdown(f"**Top Keywords for {selected_topic}:**")
        top_kw = get_top_keywords(topic_df['content'].tolist(), n=15)
        kw_text = ", ".join([f"{word}({count})" for word, count in top_kw])
        st.write(kw_text)

# =============================================================================
# PAGE: SENTIMENT ANALYSIS
# =============================================================================
def page_sentiment(df, topic_keywords):
    """Sentiment analysis page with advanced visualizations"""
    filtered_df, search_query = setup_sidebar_filters(df, topic_keywords)
    
    st.markdown('<h1 class="main-header">😊 Sentiment Analysis</h1>', unsafe_allow_html=True)
    
    # Rating distribution with violin plot
    if 'score' in filtered_df.columns:
        st.markdown("### ⭐ Rating Distribution (Violin Plot)")
        
        if 'ai_sentiment' in filtered_df.columns:
            fig_violin = create_violin_plot(filtered_df, 'score', 'ai_sentiment', 
                                           "Rating Distribution by Sentiment")
            st.plotly_chart(fig_violin, use_container_width=True)
    
    st.markdown("---")
    
    # Density plots
    col1, col2 = st.columns(2)
    
    with col1:
        if 'sentiment_score' in filtered_df.columns:
            st.markdown("### 📈 Sentiment Score Distribution")
            fig_density = create_density_plot(filtered_df, 'sentiment_score', 
                                            "Sentiment Score Density")
            st.plotly_chart(fig_density, use_container_width=True)
    
    with col2:
        if 'score' in filtered_df.columns:
            st.markdown("### ⭐ Rating Density")
            fig_rating = create_density_plot(filtered_df, 'score', "Rating Density")
            st.plotly_chart(fig_rating, use_container_width=True)
    
    st.markdown("---")
    
    # Keyword comparison
    st.markdown("### 📝 Keyword Comparison")
    
    neg_texts = filtered_df[filtered_df['ai_sentiment'] == 'Negative']['content'].tolist()
    pos_texts = filtered_df[filtered_df['ai_sentiment'] == 'Positive']['content'].tolist()
    
    neg_keywords = get_top_keywords(neg_texts, n=10)
    pos_keywords = get_top_keywords(pos_texts, n=10)
    
    if neg_keywords and pos_keywords:
        fig_comp = make_subplots(
            rows=1, cols=2,
            subplot_titles=("🔴 Negative Keywords", "🟢 Positive Keywords"),
            horizontal_spacing=0.15
        )
        
        neg_words, neg_counts = zip(*neg_keywords) if neg_keywords else ([], [])
        fig_comp.add_trace(
            go.Bar(x=list(neg_counts), y=list(neg_words), orientation='h',
                  marker_color='#ef4444', name='Negative'),
            row=1, col=1
        )
        
        pos_words, pos_counts = zip(*pos_keywords) if pos_keywords else ([], [])
        fig_comp.add_trace(
            go.Bar(x=list(pos_counts), y=list(pos_words), orientation='h',
                  marker_color='#10b981', name='Positive'),
            row=1, col=2
        )
        
        fig_comp.update_layout(height=350, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_comp, use_container_width=True)

# =============================================================================
# PAGE: DATA EXPLORER
# =============================================================================
def page_explorer(df, topic_keywords):
    """Data explorer page with search and filtering"""
    filtered_df, search_query = setup_sidebar_filters(df, topic_keywords)
    
    st.markdown('<h1 class="main-header">🔍 Data Explorer</h1>', unsafe_allow_html=True)
    
    st.markdown(f"**Total Reviews Found:** {len(filtered_df):,}")
    
    if len(filtered_df) == 0:
        st.warning("No reviews match your filters.")
        return
    
    # Sort and display options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        sort_by = st.selectbox("Sort by:", 
                              ["Latest First", "Oldest First", "Highest Rating", 
                               "Lowest Rating", "Most Positive", "Most Negative"])
    
    with col2:
        display_count = st.number_input("Show reviews:", min_value=1, max_value=100, value=10)
    
    # Sort dataframe
    sort_map = {
        "Latest First": ('at', False),
        "Oldest First": ('at', True),
        "Highest Rating": ('score', False),
        "Lowest Rating": ('score', True),
        "Most Positive": ('sentiment_score', False),
        "Most Negative": ('sentiment_score', True)
    }
    
    sort_col, ascending = sort_map[sort_by]
    if sort_col in filtered_df.columns:
        display_df = filtered_df.sort_values(by=sort_col, ascending=ascending).head(display_count)
    else:
        display_df = filtered_df.head(display_count)
    
    # Display reviews
    for idx, row in display_df.iterrows():
        topic_display = format_topic_label(row.get('Topic_Label', 'N/A'), topic_keywords) if 'Topic_Label' in row else 'N/A'
        sentiment = row.get('ai_sentiment', 'N/A')
        rating = row.get('score', 'N/A')
        
        # Color based on sentiment
        sentiment_emoji = {'Positive': '🟢', 'Negative': '🔴', 'Neutral': '🟡'}.get(sentiment, '⚪')
        
        with st.expander(f"{sentiment_emoji} ⭐ {rating} | {topic_display} | {row.get('at', 'N/A')}"):
            st.write(row.get('content', 'No content'))
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.caption(f"Version: {row.get('appVersion', 'N/A')}")
            with col2:
                st.caption(f"Sentiment: {sentiment}")
            with col3:
                st.caption(f"Confidence: {row.get('ai_confidence', 0):.2f}")
            with col4:
                st.caption(f"Date: {row.get('at', 'N/A')}")
    
    st.markdown("---")
    
    # Stats table
    st.markdown("### 📊 Summary Statistics")
    
    stats_data = {
        'Metric': ['Total Reviews', 'Avg Rating', 'Avg Sentiment', 'Positive %', 'Negative %', 'Neutral %'],
        'Value': [
            len(filtered_df),
            f"{filtered_df['score'].mean():.2f}" if 'score' in filtered_df.columns else 'N/A',
            f"{filtered_df['sentiment_score'].mean():.3f}" if 'sentiment_score' in filtered_df.columns else 'N/A',
            f"{len(filtered_df[filtered_df['ai_sentiment']=='Positive'])/len(filtered_df)*100:.1f}%" if len(filtered_df) > 0 else '0%',
            f"{len(filtered_df[filtered_df['ai_sentiment']=='Negative'])/len(filtered_df)*100:.1f}%" if len(filtered_df) > 0 else '0%',
            f"{len(filtered_df[filtered_df['ai_sentiment']=='Neutral'])/len(filtered_df)*100:.1f}%" if len(filtered_df) > 0 else '0%'
        ]
    }
    
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

# =============================================================================
# MAIN APP
# =============================================================================
def main():
    # Load data
    df = load_data()
    cm_data = load_confusion_matrix()
    topic_keywords = load_topic_keywords()
    
    if df is None:
        st.stop()
    
    # Navigation
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📄 Pages")
    
    page = st.sidebar.radio("Select Page:", 
                           ["📊 Overview", "🏷️ Topics", "😊 Sentiment", "🔍 Explorer"],
                           label_visibility="collapsed")
    
    # Route to page
    if page == "📊 Overview":
        page_overview(df, topic_keywords)
    elif page == "🏷️ Topics":
        page_topics(df, topic_keywords)
    elif page == "😊 Sentiment":
        page_sentiment(df, topic_keywords)
    elif page == "🔍 Explorer":
        page_explorer(df, topic_keywords)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #6b7280; padding: 1rem;'>
            <p>📊 BPCL Reviews Analytics Dashboard | Built with Streamlit & Plotly</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# =============================================================================
# RUN APP
# =============================================================================
if __name__ == "__main__":
    main()
