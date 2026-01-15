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
import altair as alt

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
    """Get colors based on current theme - BPCL Enterprise color palette"""
    if st.session_state.theme == 'dark':
        return {
            # BPCL Dark Theme - Deep Navy Base
            'bg': '#0f1419',              # Deep charcoal navy (page background)
            'secondary_bg': '#1a2332',    # Elevated navy (sidebar, elevated sections)
            'card_bg': '#212d3d',         # Card background with depth
            'card_hover': '#263447',      # Card hover state
            
            # Text Hierarchy
            'text': '#f0f3f7',            # Primary text - high contrast white
            'text_bright': '#ffffff',     # KPI values - brightest
            'secondary_text': '#8a98ab',  # Labels and secondary info
            'tertiary_text': '#5e6c7f',   # Captions and hints
            
            # BPCL Brand Accents
            'primary': '#1e88e5',         # Petroleum blue (BPCL primary)
            'primary_glow': 'rgba(30, 136, 229, 0.25)',
            'accent_green': '#00c853',    # Energy green (success, positive)
            'accent_orange': '#ff6f00',   # Petroleum orange (warnings, highlights)
            
            # Sentiment Colors (Energy industry)
            'positive': '#00c853',        # Energy green
            'negative': '#ff3d00',        # Alert red
            'neutral': '#ffa726',         # Amber
            
            # UI Elements
            'border': 'rgba(138, 152, 171, 0.15)',
            'border_bright': 'rgba(30, 136, 229, 0.4)',
            'divider': 'rgba(138, 152, 171, 0.1)',
            
            # Chart Styling
            'plot_bg': '#1a2332',
            'grid': 'rgba(138, 152, 171, 0.08)',
            'grid_major': 'rgba(138, 152, 171, 0.12)'
        }
    else:
        return {
            'bg': '#ffffff',
            'secondary_bg': '#f8f9fa',
            'text': '#1f2937',
            'text_bright': '#111827',
            'secondary_text': '#6b7280',
            'tertiary_text': '#9ca3af',
            'plot_bg': '#ffffff',
            'grid': 'rgba(107, 114, 128, 0.2)',
            'grid_major': 'rgba(107, 114, 128, 0.3)',
            'positive': '#10b981',
            'negative': '#ef4444',
            'neutral': '#f59e0b',
            'primary': '#1e88e5',
            'accent_green': '#10b981',
            'accent_orange': '#f59e0b',
            'border': 'rgba(229, 231, 235, 1)',
            'card_bg': '#ffffff',
            'card_hover': '#f9fafb',
            'divider': 'rgba(229, 231, 235, 0.8)',
            'primary_glow': 'rgba(30, 136, 229, 0.15)',
            'border_bright': 'rgba(30, 136, 229, 0.3)'
        }

def apply_theme_css():
    """Apply BPCL Enterprise Dark Theme CSS"""
    theme_colors = get_theme_colors()
    is_dark = st.session_state.theme == 'dark'
    
    # BPCL Dark Theme CSS
    if is_dark:
        st.markdown(f"""
        <style>
            /* ============================================
               BPCL ENTERPRISE DARK THEME
               Deep Navy Base with Petroleum Blue Accents
            ============================================ */
            
            /* Global Background Layering */
            .stApp {{
                background-color: {theme_colors['bg']} !important;
            }}
            
            .main .block-container {{
                background-color: {theme_colors['bg']} !important;
                padding-top: 2rem !important;
            }}
            
            /* Typography Hierarchy */
            .main-header {{
                font-size: 2.8rem;
                font-weight: 800;
                letter-spacing: -0.02em;
                margin-bottom: 0.5rem;
                color: {theme_colors['text_bright']} !important;
                text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }}
            
            .sub-header {{
                font-size: 1.1rem;
                font-weight: 400;
                letter-spacing: 0.01em;
                margin-bottom: 2.5rem;
                color: {theme_colors['secondary_text']} !important;
            }}
            
            /* All Markdown Text - Ensure Visibility - AGGRESSIVE */
            .stMarkdown h1, .stMarkdown h2 {{
                font-weight: 700;
                color: #ffffff !important;
            }}
            
            .stMarkdown h3 {{
                font-weight: 600;
                font-size: 1.4rem;
                color: {theme_colors['text']} !important;
                margin-top: 2rem;
                margin-bottom: 1rem;
                border-bottom: 2px solid {theme_colors['divider']};
                padding-bottom: 0.5rem;
            }}
            
            .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
                font-weight: 600;
                color: {theme_colors['text']} !important;
            }}
            
            .stMarkdown p, .stMarkdown div, .stMarkdown span, .stMarkdown li {{
                color: {theme_colors['text']} !important;
            }}
            
            /* Force all text elements to be visible */
            p, div, span, label, input, textarea, select, button {{
                color: {theme_colors['text']} !important;
            }}
            
            /* Expander content text */
            .streamlit-expanderContent p,
            .streamlit-expanderContent div,
            .streamlit-expanderContent span {{
                color: {theme_colors['text']} !important;
            }}
            
            /* Dataframe text */
            .stDataFrame, .stDataFrame * {{
                color: {theme_colors['text']} !important;
            }}
            
            /* ============================================
               KPI METRIC CARDS - Enterprise Style
            ============================================ */
            [data-testid="metric-container"] {{
                background: linear-gradient(135deg, {theme_colors['card_bg']} 0%, {theme_colors['secondary_bg']} 100%) !important;
                padding: 1.25rem 1.5rem !important;
                border-radius: 12px !important;
                border: 1px solid {theme_colors['border_bright']} !important;
                box-shadow: 
                    0 4px 12px rgba(0, 0, 0, 0.3),
                    0 0 20px {theme_colors['primary_glow']},
                    inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
                transition: all 0.3s ease !important;
                position: relative;
                overflow: hidden;
            }}
            
            [data-testid="metric-container"]::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: linear-gradient(180deg, {theme_colors['primary']} 0%, {theme_colors['accent_green']} 100%);
            }}
            
            [data-testid="metric-container"]:hover {{
                transform: translateY(-2px);
                box-shadow: 
                    0 8px 24px rgba(0, 0, 0, 0.4),
                    0 0 30px {theme_colors['primary_glow']},
                    inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
                border-color: {theme_colors['primary']} !important;
            }}
            
            /* Metric Labels - Uppercase, Tracked */
            [data-testid="metric-container"] label,
            [data-testid="metric-container"] > div > div:first-child {{
                color: {theme_colors['secondary_text']} !important;
                font-size: 0.75rem !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.08em !important;
            }}
            
            /* Metric Values - Maximum Brightness - FORCE */
            [data-testid="metric-container"] [data-testid="stMetricValue"],
            [data-testid="metric-container"] > div > div:nth-child(2),
            [data-testid="metric-container"] div[data-testid="stMetricValue"] > div {{
                color: #ffffff !important;
                font-size: 2rem !important;
                font-weight: 700 !important;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
            }}
            
            /* Metric Delta */
            [data-testid="metric-container"] [data-testid="stMetricDelta"],
            [data-testid="metric-container"] [data-testid="stMetricDelta"] > div {{
                color: {theme_colors['accent_green']} !important;
                font-size: 0.9rem !important;
                font-weight: 500 !important;
            }}
            
            /* ============================================
               SIDEBAR - Elevated Dark Panel
            ============================================ */
            section[data-testid="stSidebar"] {{
                background: linear-gradient(180deg, {theme_colors['secondary_bg']} 0%, {theme_colors['card_bg']} 100%) !important;
                border-right: 1px solid {theme_colors['border']} !important;
                box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3) !important;
            }}
            
            section[data-testid="stSidebar"] > div {{
                background: transparent !important;
            }}
            
            /* Sidebar Headers */
            div[data-testid="stSidebarContent"] h1,
            div[data-testid="stSidebarContent"] h2 {{
                color: {theme_colors['text_bright']} !important;
                font-weight: 700 !important;
                font-size: 1.4rem !important;
                margin-top: 1.5rem !important;
                margin-bottom: 1rem !important;
            }}
            
            div[data-testid="stSidebarContent"] h3 {{
                color: {theme_colors['text']} !important;
                font-weight: 600 !important;
                font-size: 1.1rem !important;
                margin-top: 1.2rem !important;
            }}
            
            /* Sidebar Text - FORCE VISIBILITY */
            div[data-testid="stSidebarContent"] p,
            div[data-testid="stSidebarContent"] label,
            div[data-testid="stSidebarContent"] span,
            div[data-testid="stSidebarContent"] div {{
                color: {theme_colors['text']} !important;
            }}
            
            /* Sidebar Metric Values - Extra Bright */
            div[data-testid="stSidebarContent"] [data-testid="stMetricValue"],
            div[data-testid="stSidebarContent"] [data-testid="stMetricValue"] div {{
                color: #ffffff !important;
                font-size: 1.5rem !important;
                font-weight: 700 !important;
            }}
            
            /* Sidebar Metric Labels */
            div[data-testid="stSidebarContent"] [data-testid="metric-container"] label {{
                color: {theme_colors['secondary_text']} !important;
                font-size: 0.7rem !important;
            }}
            
            /* Sidebar Input Fields */
            div[data-testid="stSidebarContent"] input,
            div[data-testid="stSidebarContent"] textarea {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border']} !important;
                color: {theme_colors['text']} !important;
                border-radius: 8px !important;
            }}
            
            div[data-testid="stSidebarContent"] input:focus,
            div[data-testid="stSidebarContent"] textarea:focus {{
                border-color: {theme_colors['primary']} !important;
                box-shadow: 0 0 0 3px {theme_colors['primary_glow']} !important;
            }}
            
            /* Sidebar Selectbox */
            div[data-testid="stSidebarContent"] [data-baseweb="select"] {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border']} !important;
                border-radius: 8px !important;
            }}
            
            div[data-testid="stSidebarContent"] [data-baseweb="select"] * {{
                color: {theme_colors['text']} !important;
            }}
            
            /* Selectbox dropdown items */
            [data-baseweb="popover"] {{
                background-color: {theme_colors['card_bg']} !important;
            }}
            
            [role="option"] {{
                color: {theme_colors['text']} !important;
                background-color: {theme_colors['card_bg']} !important;
            }}
            
            [role="option"]:hover {{
                background-color: {theme_colors['card_hover']} !important;
            }}
            
            /* Sidebar Buttons */
            div[data-testid="stSidebarContent"] button {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border_bright']} !important;
                color: {theme_colors['text']} !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                transition: all 0.2s ease !important;
            }}
            
            div[data-testid="stSidebarContent"] button:hover {{
                background-color: {theme_colors['card_hover']} !important;
                border-color: {theme_colors['primary']} !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3) !important;
            }}
            
            /* ============================================
               INTERACTIVE ELEMENTS
            ============================================ */
            
            /* Expanders */
            .streamlit-expanderHeader {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border']} !important;
                border-radius: 8px !important;
                color: {theme_colors['text']} !important;
                font-weight: 600 !important;
            }}
            
            .streamlit-expanderHeader:hover {{
                border-color: {theme_colors['primary']} !important;
                background-color: {theme_colors['card_hover']} !important;
            }}
            
            /* Expander Content - CRITICAL for review text visibility */
            .streamlit-expanderContent {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border']} !important;
                border-top: none !important;
                border-radius: 0 0 8px 8px !important;
                padding: 1rem !important;
            }}
            
            .streamlit-expanderContent p,
            .streamlit-expanderContent div,
            .streamlit-expanderContent span,
            .streamlit-expanderContent pre,
            .streamlit-expanderContent code {{
                color: {theme_colors['text']} !important;
                background-color: transparent !important;
            }}
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 8px;
                background-color: {theme_colors['secondary_bg']};
                padding: 0.5rem;
                border-radius: 10px;
            }}
            
            .stTabs [data-baseweb="tab"] {{
                color: {theme_colors['secondary_text']} !important;
                font-weight: 600;
                border-radius: 6px;
                padding: 0.5rem 1rem;
            }}
            
            .stTabs [aria-selected="true"] {{
                background-color: {theme_colors['card_bg']} !important;
                color: {theme_colors['text_bright']} !important;
                border: 1px solid {theme_colors['border_bright']} !important;
            }}
            
            /* Dataframes */
            .stDataFrame {{
                background-color: {theme_colors['card_bg']} !important;
                border: 1px solid {theme_colors['border']} !important;
                border-radius: 8px !important;
            }}
            
            /* Dividers */
            hr {{
                border-color: {theme_colors['divider']} !important;
                margin: 2rem 0 !important;
            }}
            
            /* ============================================
               CHARTS & VISUALIZATIONS
            ============================================ */
            .js-plotly-plot {{
                background: transparent !important;
            }}
            
            .plot-container {{
                background-color: {theme_colors['card_bg']} !important;
                border-radius: 12px !important;
                padding: 1rem !important;
                border: 1px solid {theme_colors['border']} !important;
            }}
            
            /* Caption text */
            .stCaption {{
                color: {theme_colors['tertiary_text']} !important;
                font-size: 0.85rem !important;
            }}
        </style>
        """, unsafe_allow_html=True)
    else:
        # Light theme - minimal styling
        st.markdown("""
        <style>
            .main-header {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            }}
            
            .sub-header {{
                font-size: 1rem;
                margin-bottom: 2rem;
                opacity: 0.8;
            }}
            
            /* Button text */
            .stButton button {{
                color: inherit;
            }}
            
            /* Input field text */
            .stTextInput input {{
                color: inherit;
            }}
            
            .stSelectbox select {{
                color: inherit;
            }}
            
            .stSlider {{
                color: inherit;
            }}
            
            /* Legend and annotations */
            .plotly-notifier {{
                color: inherit;
            }}
            
            /* Divider line */
            hr {{
                border-color: rgba(200, 200, 200, 0.2);
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

@st.cache_data
def analyze_aspects(text):
    """
    Analyze sentiment for specific aspects in review text.
    Returns dict with aspect sentiment scores.
    """
    if pd.isna(text):
        return {}
    
    text_lower = str(text).lower()
    
    # Define aspect keywords and their related terms
    aspects = {
        'Price': {
            'keywords': ['price', 'expensive', 'cheap', 'cost', 'rate', 'charges', 'overpriced', 'discount', 'refund'],
            'positive': ['affordable', 'reasonable', 'fair', 'cheap', 'good price', 'value'],
            'negative': ['expensive', 'costly', 'overpriced', 'high price']
        },
        'Service': {
            'keywords': ['service', 'staff', 'attendant', 'customer service', 'support', 'help', 'response', 'assist'],
            'positive': ['helpful', 'friendly', 'quick', 'efficient', 'good service', 'professional'],
            'negative': ['rude', 'slow', 'poor service', 'unhelpful', 'bad staff', 'ignorant']
        },
        'App/Interface': {
            'keywords': ['app', 'interface', 'ui', 'ux', 'design', 'button', 'feature', 'bug', 'crash', 'loading', 'freeze'],
            'positive': ['smooth', 'easy', 'fast', 'intuitive', 'user-friendly', 'clean'],
            'negative': ['crashes', 'slow', 'buggy', 'confusing', 'broken', 'laggy', 'freezes']
        },
        'Fuel Quality': {
            'keywords': ['fuel', 'petrol', 'diesel', 'quality', 'purity', 'contamination', 'water', 'adulterated'],
            'positive': ['good quality', 'pure', 'clean', 'premium'],
            'negative': ['poor quality', 'contaminated', 'water', 'adulterated', 'fake', 'cheated']
        },
        'Location/Parking': {
            'keywords': ['location', 'parking', 'place', 'pump', 'station', 'access', 'crowded', 'distance'],
            'positive': ['convenient', 'accessible', 'easy access', 'good location', 'spacious'],
            'negative': ['inconvenient', 'poor location', 'parking issue', 'crowded', 'hard to find']
        }
    }
    
    aspect_scores = {}
    
    for aspect, keywords_dict in aspects.items():
        if any(kw in text_lower for kw in keywords_dict['keywords']):
            sentiment_score = 0.5  # neutral default
            
            # Check for positive keywords
            positive_count = sum(1 for kw in keywords_dict['positive'] if kw in text_lower)
            negative_count = sum(1 for kw in keywords_dict['negative'] if kw in text_lower)
            
            if positive_count > negative_count:
                sentiment_score = 0.7 + (positive_count * 0.05)
            elif negative_count > positive_count:
                sentiment_score = 0.3 - (negative_count * 0.05)
            else:
                sentiment_score = 0.5
            
            aspect_scores[aspect] = max(0.0, min(1.0, sentiment_score))
    
    return aspect_scores

def enrich_dataframe_with_aspects(df):
    """Add aspect-based sentiment scores to dataframe"""
    if 'aspect_sentiments' not in df.columns:
        df['aspect_sentiments'] = df['content'].apply(analyze_aspects)
    return df

def create_density_plot(df, column, title):
    """Create BPCL-style density plot with dark theme support"""
    colors = get_theme_colors()
    is_dark = st.session_state.theme == 'dark'
    
    fig = px.histogram(df, x=column, nbins=50, marginal="box",
                       title=title,
                       color_discrete_sequence=[colors['primary']])
    
    fig.update_traces(
        marker_line_color=colors.get('border_bright', colors['border']),
        marker_line_width=0.5,
        opacity=0.85
    )
    
    fig.update_layout(
        height=320,
        showlegend=False,
        plot_bgcolor=colors['plot_bg'],
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            gridcolor=colors['grid'],
            gridwidth=1,
            tickfont=dict(color=colors['secondary_text'], size=11),
            title=dict(font=dict(color=colors['text'], size=13))
        ),
        yaxis=dict(
            gridcolor=colors.get('grid_major', colors['grid']),
            gridwidth=1,
            tickfont=dict(color=colors['secondary_text'], size=11),
            title=dict(font=dict(color=colors['text'], size=13))
        ),
        title=dict(
            font=dict(color=colors.get('text_bright', colors['text']), size=16),
            x=0.05
        ),
        font=dict(color=colors['text'], family='Inter, system-ui, sans-serif'),
        margin=dict(l=50, r=30, t=60, b=50)
    )
    
    return fig

def create_violin_plot(df, y_col, x_col, title):
    """Create BPCL-style violin plot with dark theme support"""
    colors = get_theme_colors()
    is_dark = st.session_state.theme == 'dark'
    
    fig = px.violin(df, y=y_col, x=x_col, box=True, points="outliers",
                    title=title,
                    color_discrete_sequence=[colors['primary'], colors['accent_green'], colors.get('accent_orange', colors['neutral'])])
    
    fig.update_traces(
        marker_line_width=1.5,
        marker_line_color=colors.get('border_bright', colors['border']),
        opacity=0.8
    )
    
    fig.update_layout(
        height=380,
        plot_bgcolor=colors['plot_bg'],
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            gridcolor=colors['grid'],
            gridwidth=1,
            tickfont=dict(color=colors['secondary_text'], size=11),
            title=dict(font=dict(color=colors['text'], size=13))
        ),
        yaxis=dict(
            gridcolor=colors.get('grid_major', colors['grid']),
            gridwidth=1,
            tickfont=dict(color=colors['secondary_text'], size=11),
            title=dict(font=dict(color=colors['text'], size=13))
        ),
        title=dict(
            font=dict(color=colors.get('text_bright', colors['text']), size=16),
            x=0.05
        ),
        font=dict(color=colors['text'], family='Inter, system-ui, sans-serif'),
        margin=dict(l=50, r=30, t=60, b=50)
    )
    
    return fig

def create_sentiment_heatmap(df, topic_keywords):
    """Create BPCL-style sentiment vs topic heatmap with dark theme support"""
    colors = get_theme_colors()
    is_dark = st.session_state.theme == 'dark'
    
    if 'Topic_Label' in df.columns and 'ai_sentiment' in df.columns:
        heatmap_data = pd.crosstab(df['ai_sentiment'], df['Topic_Label'], normalize='index') * 100
        
        # BPCL color scale - green to red for sentiment
        color_scale = [[0, colors['negative']], [0.5, colors['neutral']], [1, colors['positive']]]
        
        fig = px.imshow(
            heatmap_data.values,
            x=heatmap_data.columns.tolist(),
            y=heatmap_data.index.tolist(),
            color_continuous_scale=color_scale,
            labels=dict(color='% Distribution'),
            title='Sentiment Distribution by Topic (%)',
            aspect='auto'
        )
        
        fig.update_traces(
            text=heatmap_data.values.round(1),
            texttemplate='%{text}%',
            textfont=dict(size=11, color=colors.get('text_bright', colors['text']))
        )
        
        fig.update_layout(
            height=380,
            plot_bgcolor=colors['plot_bg'],
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                tickfont=dict(color=colors['secondary_text'], size=11),
                title=dict(font=dict(color=colors['text'], size=13)),
                side='bottom'
            ),
            yaxis=dict(
                tickfont=dict(color=colors['secondary_text'], size=11),
                title=dict(font=dict(color=colors['text'], size=13))
            ),
            title=dict(
                font=dict(color=colors.get('text_bright', colors['text']), size=16),
                x=0.05
            ),
            font=dict(color=colors['text'], family='Inter, system-ui, sans-serif'),
            coloraxis_colorbar=dict(
                tickfont=dict(color=colors['secondary_text'], size=10),
                title=dict(font=dict(color=colors['text'], size=12))
            ),
            margin=dict(l=50, r=30, t=60, b=50)
        )
        
        return fig
    
    return None

def create_gauge_chart(value, title="Sentiment Health"):
    """Create BPCL-style gauge chart with dark theme support"""
    colors = get_theme_colors()
    is_dark = st.session_state.theme == 'dark'
    normalized = (value + 1) * 50
    
    # BPCL color scheme for gauge
    bar_color = colors['primary']
    if normalized >= 66:
        bar_color = colors['accent_green']
    elif normalized <= 33:
        bar_color = colors['negative']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=normalized,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 20, 'color': colors.get('text_bright', colors['text'])}},
        number={
            'font': {'size': 42, 'color': colors.get('text_bright', colors['text'])}, 
            'suffix': '%'
        },
        gauge={
            'axis': {
                'range': [0, 100], 
                'tickcolor': colors.get('grid_major', colors['grid']), 
                'tickfont': {'color': colors['secondary_text'], 'size': 11}
            },
            'bar': {'color': bar_color, 'thickness': 0.8},
            'bgcolor': "rgba(128, 128, 128, 0.05)" if is_dark else "rgba(128, 128, 128, 0.1)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 33], 'color': f'rgba(255, 61, 0, {0.12 if is_dark else 0.2})'},
                {'range': [33, 66], 'color': f'rgba(255, 167, 38, {0.12 if is_dark else 0.2})'},
                {'range': [66, 100], 'color': f'rgba(0, 200, 83, {0.12 if is_dark else 0.2})'}
            ],
            'threshold': {
                'line': {'color': colors.get('text_bright', colors['text']), 'width': 2},
                'thickness': 0.75,
                'value': normalized
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=70, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': colors['text'], 'family': 'Inter, system-ui, sans-serif'}
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
        
        st.sidebar.markdown(f"📅 **Date Range** (Latest: {max_date.date()})")
        
        # Preset date ranges based on max_date
        date_preset = st.sidebar.selectbox(
            "Quick Select:",
            ["All Data", "Past Week", "Past Month", "Past 3 Months", "Past Year", "Custom"],
            label_visibility="collapsed"
        )
        
        if date_preset == "All Data":
            date_range = (min_date.date(), max_date.date())
        elif date_preset == "Past Week":
            start = max_date - timedelta(days=7)
            date_range = (start.date(), max_date.date())
        elif date_preset == "Past Month":
            start = max_date - timedelta(days=30)
            date_range = (start.date(), max_date.date())
        elif date_preset == "Past 3 Months":
            start = max_date - timedelta(days=90)
            date_range = (start.date(), max_date.date())
        elif date_preset == "Past Year":
            start = max_date - timedelta(days=365)
            date_range = (start.date(), max_date.date())
        else:  # Custom
            date_range = st.sidebar.date_input(
                "Select custom range:",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date(),
                label_visibility="collapsed"
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
    colors = get_theme_colors()
    
    st.markdown('<h1 class="main-header">📊 BPCL Reviews Analytics Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Sentiment Analysis & Topic Insights</p>', unsafe_allow_html=True)
    
    # Key metrics row 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_rating = filtered_df['score'].mean() if 'score' in filtered_df.columns else 0
        st.metric("⭐ Average Rating", f"{avg_rating:.2f}", 
                 f"{(avg_rating/5*100):.1f}%")
    
    with col2:
        total_reviews = len(filtered_df)
        st.metric("📊 Total Reviews", f"{total_reviews:,}", 
                 f"{len(df):,} all-time")
    
    with col3:
        avg_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        st.metric("🎯 Avg Sentiment", f"{avg_sentiment:.3f}", 
                 "Positive" if avg_sentiment > 0 else "Negative")
    
    with col4:
        if 'at' in filtered_df.columns and len(filtered_df) > 0:
            latest_date = filtered_df['at'].max()
            days_ago = (datetime.now() - latest_date).days
            st.metric("📅 Latest Review", latest_date.strftime('%Y-%m-%d'), 
                     f"{days_ago} days ago")
        else:
            st.metric("📋 Unique Versions", filtered_df['appVersion'].nunique())
    
    st.markdown("---")
    
    # Sentiment breakdown - Key metrics row 2
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        neg_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Negative'])
        neg_pct = neg_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🔴 Negative", f"{neg_count:,}", f"{neg_pct:.1f}%")
    
    with col2:
        neu_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Neutral'])
        neu_pct = neu_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🟡 Neutral", f"{neu_count:,}", f"{neu_pct:.1f}%")
    
    with col3:
        pos_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Positive'])
        pos_pct = pos_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🟢 Positive", f"{pos_count:,}", f"{pos_pct:.1f}%")
    
    with col4:
        if len(filtered_df) > 0:
            response_rate = (neg_pct + pos_pct)
            st.metric("💬 Response Rate", f"{response_rate:.2f}%", 
                     f"{100-response_rate:.1f}% neutral")
    
    st.markdown("---")
    
    # Main timeline chart with Altair
    if 'at' in filtered_df.columns and len(filtered_df) > 0:
        st.markdown("### 📈 Review Volume & Sentiment Trends")
        
        # Prepare daily data
        daily_data = filtered_df.copy()
        daily_data['date'] = daily_data['at'].dt.date
        
        # Aggregate by date and sentiment
        timeline_df = daily_data.groupby(['date', 'ai_sentiment']).size().reset_index(name='count')
        
        # Create BPCL-styled Altair chart
        is_dark = st.session_state.theme == 'dark'
        
        base = alt.Chart(timeline_df).encode(
            x=alt.X('date:T', 
                   title='Date', 
                   axis=alt.Axis(
                       format='%b %Y', 
                       labelAngle=-45,
                       labelColor=colors['secondary_text'],
                       titleColor=colors['text'],
                       titleFontSize=13,
                       labelFontSize=10,
                       gridColor=colors['grid'],
                       domainColor=colors['border']
                   ))
        )
        
        line = base.mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=3, interpolate='monotone').encode(
            y=alt.Y('count:Q', 
                   title='Number of Reviews',
                   axis=alt.Axis(
                       labelColor=colors['secondary_text'],
                       titleColor=colors['text'],
                       titleFontSize=13,
                       labelFontSize=10,
                       gridColor=colors.get('grid_major', colors['grid']),
                       domainColor=colors['border']
                   )),
            color=alt.Color('ai_sentiment:N', 
                          scale=alt.Scale(
                              domain=['Negative', 'Neutral', 'Positive'],
                              range=[colors['negative'], colors['neutral'], colors['positive']]
                          ),
                          legend=alt.Legend(
                              title='Sentiment',
                              titleColor=colors['text'],
                              titleFontSize=12,
                              labelColor=colors['text'],
                              labelFontSize=11,
                              orient='top-right',
                              fillColor=colors.get('card_bg', colors['secondary_bg']) if is_dark else 'white',
                              strokeColor=colors['border'],
                              padding=10,
                              cornerRadius=8
                          )),
            tooltip=[
                alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
                alt.Tooltip('ai_sentiment:N', title='Sentiment'),
                alt.Tooltip('count:Q', title='Reviews', format=',')
            ]
        )
        
        chart = line.properties(
            height=360,
            title=alt.TitleParams(
                text='Daily Review Volume by Sentiment',
                fontSize=16,
                color=colors.get('text_bright', colors['text']),
                anchor='start',
                offset=10
            ),
            background=colors.get('plot_bg', colors['secondary_bg'])
        ).configure_view(
            strokeWidth=0,
            fill=colors.get('plot_bg', colors['secondary_bg'])
        ).configure_axis(
            grid=True
        )
        
        st.altair_chart(chart, use_container_width=True)
    
    st.markdown("---")
    
    # Row: Gauge + Distribution
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### 🌡️ Sentiment Health Gauge")
        global_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        gauge_fig = create_gauge_chart(global_sentiment, "Sentiment Score")
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        # Interpretation
        if global_sentiment > 0.3:
            st.success("✅ Overall sentiment is **POSITIVE**")
        elif global_sentiment < -0.3:
            st.error("⚠️ Overall sentiment is **NEGATIVE**")
        else:
            st.warning("➡️ Overall sentiment is **NEUTRAL**")
    
    with col_right:
        st.markdown("### 📊 Sentiment Distribution")
        sentiment_counts = filtered_df['ai_sentiment'].value_counts()
        fig_dist = px.pie(values=sentiment_counts.values, names=sentiment_counts.index,
                         title="Overall Sentiment Breakdown",
                         color_discrete_map={'Positive': colors['positive'], 
                                           'Negative': colors['negative'], 
                                           'Neutral': colors['neutral']},
                         hole=0.45)
        fig_dist.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont=dict(size=13, color=colors.get('text_bright', colors['text'])),
            marker=dict(line=dict(color=colors.get('border_bright', colors['border']), width=1.5))
        )
        fig_dist.update_layout(
            height=350, 
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            title=dict(
                font=dict(color=colors.get('text_bright', colors['text']), size=16),
                x=0.5,
                xanchor='center'
            ),
            font=dict(color=colors['text'], family='Inter, system-ui, sans-serif'),
            legend=dict(
                font=dict(color=colors['text'], size=12),
                bgcolor='rgba(0,0,0,0)',
                bordercolor=colors['border'],
                borderwidth=1
            ),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    
    # Rating distribution
    if 'score' in filtered_df.columns:
        st.markdown("### ⭐ Rating Distribution")
        
        rating_counts = filtered_df['score'].value_counts().sort_index()
        
        fig_rating = go.Figure(data=[
            go.Bar(
                x=rating_counts.index,
                y=rating_counts.values,
                marker=dict(
                    color=[colors['negative'], colors['negative'], colors['neutral'], 
                          colors['positive'], colors['positive']],
                    line=dict(color=colors.get('border_bright', colors['border']), width=1.2)
                ),
                text=rating_counts.values,
                textposition='outside',
                textfont=dict(size=12, color=colors.get('text_bright', colors['text'])),
                hovertemplate='<b>%{x} Stars</b><br>Count: %{y:,}<extra></extra>',
                opacity=0.9
            )
        ])
        
        fig_rating.update_layout(
            title=dict(
                text="Distribution by Star Rating",
                font=dict(color=colors.get('text_bright', colors['text']), size=16),
                x=0.05
            ),
            xaxis=dict(
                title=dict(text="Star Rating", font=dict(color=colors['text'], size=13)),
                gridcolor=colors['grid'],
                gridwidth=1,
                tickfont=dict(color=colors['secondary_text'], size=11),
                tickmode='linear',
                tick0=1,
                dtick=1
            ),
            yaxis=dict(
                title=dict(text="Number of Reviews", font=dict(color=colors['text'], size=13)),
                gridcolor=colors.get('grid_major', colors['grid']),
                gridwidth=1,
                tickfont=dict(color=colors['secondary_text'], size=11)
            ),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor=colors['plot_bg'],
            font=dict(color=colors['text'], family='Inter, system-ui, sans-serif'),
            margin=dict(l=50, r=30, t=60, b=50),
            bargap=0.3
        )
        
        st.plotly_chart(fig_rating, use_container_width=True)

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
        colors = get_theme_colors()
        topic_counts = filtered_df['Topic_Label'].value_counts()
        fig_topics = px.bar(x=topic_counts.values, y=topic_counts.index,
                           orientation='h', title="Topics by Review Count")
        fig_topics.update_layout(
            height=300, 
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor=colors['plot_bg'],
            xaxis_gridcolor=colors['grid'],
            title_font_color=colors['text'],
            xaxis_title_font_color=colors['text'],
            yaxis_title_font_color=colors['text'],
            xaxis_tickfont_color=colors['text'],
            yaxis_tickfont_color=colors['text'],
            font_color=colors['text']
        )
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
        colors = get_theme_colors()
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
        
        fig_comp.update_layout(
            height=350, 
            showlegend=False, 
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor=colors['plot_bg'],
            xaxis_gridcolor=colors['grid'],
            xaxis2_gridcolor=colors['grid'],
            title_font_color=colors['text'],
            xaxis_title_font_color=colors['text'],
            yaxis_title_font_color=colors['text'],
            xaxis_tickfont_color=colors['text'],
            yaxis_tickfont_color=colors['text'],
            font_color=colors['text']
        )
        fig_comp.update_xaxes(title_text="Count", row=1, col=1)
        fig_comp.update_xaxes(title_text="Count", row=1, col=2)
        st.plotly_chart(fig_comp, use_container_width=True)

# =============================================================================
# PAGE: ASPECT ANALYSIS
# =============================================================================
@st.cache_data
def load_aspect_data():
    """Load the aspect analysis CSV with caching"""
    try:
        df = pd.read_csv('HelloBPCL_Detailed_Analysis.csv')
        # Parse date column
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return df
    except FileNotFoundError:
        st.error("⚠️ File 'HelloBPCL_Detailed_Analysis.csv' not found.")
        return None

def page_aspects(topic_keywords):
    """Aspect Analysis page with detailed insights and drill-down"""
    st.markdown("# 🎯 Aspect Analysis")
    st.markdown("---")
    
    # Load data
    df = load_aspect_data()
    if df is None:
        st.stop()
    
    # Sidebar filter for sentiment
    st.sidebar.markdown("## 📋 Aspect Filters")
    sentiments = sorted(df['Sentiment'].unique())
    selected_sentiment = st.sidebar.selectbox(
        "Sentiment", 
        sentiments,
        index=sentiments.index('Negative') if 'Negative' in sentiments else 0,
        key="aspect_sentiment_filter"
    )
    
    # Filter by sentiment
    filtered_df = df[df['Sentiment'] == selected_sentiment].copy()
    
    # =========================================================================
    # KPIs SECTION
    # =========================================================================
    colors = get_theme_colors()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Total Reviews",
            f"{len(filtered_df):,}",
            delta=f"From {len(df):,} total"
        )
    
    with col2:
        unique_aspects = filtered_df['Aspect'].nunique()
        st.metric(
            "🏷️ Unique Aspects",
            f"{unique_aspects}",
            delta=f"{unique_aspects} complaint types"
        )
    
    with col3:
        if len(filtered_df) > 0:
            top_aspect = filtered_df['Aspect'].value_counts().index[0]
            top_count = filtered_df['Aspect'].value_counts().values[0]
            st.metric(
                "🔴 #1 Aspect",
                f"{top_aspect}",
                delta=f"{top_count} mentions ({top_count/len(filtered_df)*100:.1f}%)"
            )
        else:
            st.metric("#1 Aspect", "N/A", delta="No data")
    
    st.markdown("---")
    
    # =========================================================================
    # TOP ASPECTS CHART
    # =========================================================================
    st.markdown(f"### 📈 Top 15 Most Frequent Aspects ({selected_sentiment})")
    
    if len(filtered_df) > 0:
        # Count aspects
        aspect_counts = filtered_df['Aspect'].value_counts().head(15)
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                y=aspect_counts.index,
                x=aspect_counts.values,
                orientation='h',
                marker=dict(
                    color=aspect_counts.values,
                    colorscale='Reds' if selected_sentiment == 'Negative' else 'Blues',
                    showscale=False,
                    line=dict(color='rgba(0,0,0,0)')
                ),
                text=aspect_counts.values,
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Mentions: %{x}<extra></extra>',
                name=selected_sentiment
            )
        )
        
        fig.update_layout(
            title=f"Top Complained Aspects - {selected_sentiment} Sentiment",
            xaxis_title="Number of Mentions",
            yaxis_title="Aspect",
            height=500,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor=colors['plot_bg'],
            xaxis_gridcolor=colors['grid'],
            xaxis_title_font_color=colors['text'],
            yaxis_title_font_color=colors['text'],
            xaxis_tickfont_color=colors['text'],
            yaxis_tickfont_color=colors['text'],
            font_color=colors['text'],
            margin=dict(l=200)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available for the selected sentiment.")
    
    st.markdown("---")
    
    # =========================================================================
    # DRILL-DOWN SECTION
    # =========================================================================
    st.markdown("### 🔎 Drill-Down: View Reviews by Aspect")
    
    if len(filtered_df) > 0:
        # Dropdown to select aspect
        available_aspects = sorted(filtered_df['Aspect'].unique())
        selected_aspect = st.selectbox(
            "Select Aspect to View Details:",
            available_aspects,
            key="aspect_drilldown"
        )
        
        # Filter for selected aspect
        aspect_reviews = filtered_df[filtered_df['Aspect'] == selected_aspect].copy()
        
        # Display stats for selected aspect
        aspect_col1, aspect_col2, aspect_col3, aspect_col4 = st.columns(4)
        
        with aspect_col1:
            st.metric("Reviews", len(aspect_reviews))
        
        with aspect_col2:
            avg_rating = aspect_reviews['Rating'].mean()
            st.metric("Avg Rating", f"{avg_rating:.1f}★", delta="out of 5")
        
        with aspect_col3:
            if len(aspect_reviews) > 0:
                positive_pct = (aspect_reviews['Rating'] >= 4).sum() / len(aspect_reviews) * 100
                st.metric("Positive", f"{positive_pct:.0f}%", delta="(4-5 stars)")
        
        with aspect_col4:
            if len(aspect_reviews) > 0:
                negative_pct = (aspect_reviews['Rating'] <= 2).sum() / len(aspect_reviews) * 100
                st.metric("Negative", f"{negative_pct:.0f}%", delta="(1-2 stars)")
        
        st.markdown("---")
        
        # Display reviews table
        st.markdown(f"#### Review Texts for Aspect: **{selected_aspect}**")
        
        display_columns = ['Date', 'Rating', 'Review_Text', 'App_Version', 'Sentiment']
        available_columns = [col for col in display_columns if col in aspect_reviews.columns]
        
        # Sort by date descending
        if 'Date' in aspect_reviews.columns:
            aspect_reviews_sorted = aspect_reviews.sort_values('Date', ascending=False)
        else:
            aspect_reviews_sorted = aspect_reviews
        
        # Display as expandable cards
        for idx, (_, row) in enumerate(aspect_reviews_sorted.iterrows()):
            rating = int(row['Rating']) if pd.notna(row['Rating']) else 'N/A'
            sentiment = row.get('Sentiment', 'N/A')
            sentiment_emoji = {'Negative': '🔴', 'Neutral': '🟡', 'Positive': '🟢'}.get(sentiment, '⚪')
            date_str = str(row.get('Date', 'N/A')).split(' ')[0]
            
            with st.expander(f"{sentiment_emoji} ⭐ {rating} | {date_str}", expanded=(idx == 0)):
                st.write(row.get('Review_Text', 'No text'))
                
                exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)
                with exp_col1:
                    st.caption(f"**Date:** {date_str}")
                with exp_col2:
                    st.caption(f"**Rating:** {rating}★")
                with exp_col3:
                    st.caption(f"**Version:** {row.get('App_Version', 'N/A')}")
                with exp_col4:
                    st.caption(f"**Sentiment:** {sentiment}")
        
        # Option to download filtered data
        st.markdown("---")
        csv_buffer = aspect_reviews_sorted[available_columns].to_csv(index=False)
        st.download_button(
            label=f"📥 Download {selected_aspect} Reviews ({len(aspect_reviews)} rows)",
            data=csv_buffer,
            file_name=f"aspect_{selected_aspect.replace(' ', '_')}_reviews.csv",
            mime="text/csv"
        )
    else:
        st.warning("No data available for the selected sentiment.")

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
# COMPETITIVE BENCHMARKING MODULE
# =============================================================================
@st.cache_data
def load_competitive_data():
    """Load competitive benchmarking data from CSV"""
    try:
        df = pd.read_csv('competitive_reviews_raw.csv')
        df['at'] = pd.to_datetime(df['at'], errors='coerce')
        return df
    except FileNotFoundError:
        return None


def page_market_battleground():
    """Tab 2: Market Battleground - High Level Competitive Overview"""
    colors = get_theme_colors()
    
    # Load competitive data
    comp_data = load_competitive_data()
    
    if comp_data is None:
        st.warning("⚠️ Competitive data not found. Run the benchmarking notebook first.")
        return
    
    st.markdown('<h1 class="main-header">⚔️ Market Battleground</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">BPCL vs Competitors: Head-to-Head Analysis</p>', unsafe_allow_html=True)
    
    # Filter to last 12 months
    comp_data['at'] = pd.to_datetime(comp_data['at'], errors='coerce')
    cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=12)
    comp_filtered = comp_data[comp_data['at'] >= cutoff_date].copy()
    
    # =========================================================================
    # ROW 1: KEY METRICS
    # =========================================================================
    st.markdown("### 📊 Key Metrics")
    
    # Calculate NSS for each brand
    def calc_nss_per_brand(df):
        nss_dict = {}
        for brand in df['brand'].unique():
            brand_data = df[df['brand'] == brand]
            promoters = len(brand_data[brand_data['score'] == 5])
            detractors = len(brand_data[brand_data['score'] <= 3])
            total = len(brand_data)
            nss = ((promoters - detractors) / total * 100) if total > 0 else 0
            nss_dict[brand] = nss
        return nss_dict
    
    nss_scores = calc_nss_per_brand(comp_filtered)
    
    # Calculate gaps
    bpcl_nss = nss_scores.get('BPCL', 0)
    indianoil_nss = nss_scores.get('IndianOil', 0)
    hpcl_nss = nss_scores.get('HPCL', 0)
    shell_nss = nss_scores.get('Shell', 0)
    market_avg = np.mean([indianoil_nss, hpcl_nss, shell_nss])
    
    gap_indianoil = bpcl_nss - indianoil_nss
    gap_shell = bpcl_nss - shell_nss
    gap_market = bpcl_nss - market_avg
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🎯 BPCL NSS",
            f"{bpcl_nss:.2f}",
            f"{bpcl_nss:.1f}%",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "🆚 Gap vs IndianOil",
            f"{gap_indianoil:.2f}",
            f"{gap_indianoil:+.1f}",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            "🆚 Gap vs Shell",
            f"{gap_shell:.2f}",
            f"{gap_shell:+.1f}",
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            "📈 vs Market Avg",
            f"{gap_market:.2f}",
            f"{gap_market:+.1f}",
            delta_color="normal"
        )
    
    st.markdown("---")
    
    # =========================================================================
    # ROW 2: PAIN POINT PARITY & SHARE OF VOICE
    # =========================================================================
    st.markdown("### 📉 Competitive Landscape")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 🔥 Pain Point Parity (Complaint Heatmap)")
        st.info("💡 Analyze which brands struggle with specific issues (Login, Payment, UI, Support)")
        
        # Create complaint matrix placeholder
        complaint_topics = ['Login', 'Payment', 'UI', 'Support']
        brands = comp_filtered['brand'].unique()
        
        # Simple complaint count matrix
        complaint_matrix = []
        for brand in brands:
            brand_data = comp_filtered[(comp_filtered['brand'] == brand) & (comp_filtered['score'] <= 2)]
            row = {'Brand': brand}
            for topic in complaint_topics:
                keywords = {
                    'Login': ['login', 'otp', 'verify', 'sms'],
                    'Payment': ['payment', 'fail', 'money', 'deduct'],
                    'UI': ['slow', 'crash', 'hang', 'freeze'],
                    'Support': ['support', 'help', 'ticket', 'contact']
                }
                count = 0
                if len(brand_data) > 0:
                    for keyword in keywords.get(topic, []):
                        count += brand_data['content'].fillna('').str.lower().str.contains(keyword).sum()
                rate = (count / len(comp_filtered[comp_filtered['brand'] == brand]) * 100) if len(comp_filtered[comp_filtered['brand'] == brand]) > 0 else 0
                row[topic] = rate
            complaint_matrix.append(row)
        
        df_complaints = pd.DataFrame(complaint_matrix).set_index('Brand')
        
        fig_heatmap = px.imshow(
            df_complaints,
            labels=dict(x="Issue Category", y="Brand", color="Problem Rate (%)"),
            title="Complaint Heatmap by Brand",
            color_continuous_scale="YlOrRd",
            text_auto='.1f',
            height=400
        )
        fig_heatmap.update_layout(
            plot_bgcolor=colors['plot_bg'],
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=colors['text'])
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with col_right:
        st.markdown("#### 📢 Share of Voice (Review Velocity)")
        st.info("💡 Track engagement: Higher volume = stronger market presence")
        
        # Aggregate reviews by brand and date
        reviews_by_date = comp_filtered.groupby([pd.Grouper(key='at', freq='W'), 'brand']).size().reset_index(name='count')
        
        fig_sov = px.line(
            reviews_by_date,
            x='at',
            y='count',
            color='brand',
            title="Weekly Review Volume (Share of Voice)",
            labels={'at': 'Date', 'count': 'Reviews per Week', 'brand': 'Brand'},
            height=400
        )
        fig_sov.update_layout(
            plot_bgcolor=colors['plot_bg'],
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=colors['text']),
            hovermode='x unified'
        )
        st.plotly_chart(fig_sov, use_container_width=True)
    
    st.markdown("---")
    
    # =========================================================================
    # ROW 3: BLUE OCEAN OPPORTUNITIES
    # =========================================================================
    st.markdown("### 🌊 Blue Ocean: Competitor Strengths")
    st.info("💡 Features competitors are praised for that BPCL can adopt or improve")
    
    # Define sample blue ocean features (would come from analysis function)
    blue_ocean_features = {
        'IndianOil': ['seamless integration', 'fast transactions', 'battery optimization'],
        'HPCL': ['user interface', 'real-time updates', 'quick setup'],
        'Shell': ['premium experience', 'loyalty rewards', 'global standards']
    }
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.success(f"**IndianOil** 🏆\n\n" + "\n".join([f"✓ {f}" for f in blue_ocean_features['IndianOil']]))
    
    with col2:
        st.success(f"**HPCL** 🏆\n\n" + "\n".join([f"✓ {f}" for f in blue_ocean_features['HPCL']]))
    
    with col3:
        st.success(f"**Shell** 🏆\n\n" + "\n".join([f"✓ {f}" for f in blue_ocean_features['Shell']]))


def page_strategic_deep_dive():
    """Tab 3: Strategic Deep Dive - Advanced Competitive Analysis with Live Data"""
    from deep_dive_renderer import render_deep_dive_tab
    
    st.markdown('<h1 class="main-header">🚀 Strategic Deep Dive</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Head-to-Head Competitive Intelligence: BPCL vs IndianOil</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render the full deep dive analysis
    render_deep_dive_tab()


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
    
    # Create main tab structure
    tab1, tab2, tab3 = st.tabs([
        "📊 Internal Pulse",
        "⚔️ Market Battleground",
        "🚀 Strategic Deep Dive"
    ])
    
    # =========================================================================
    # TAB 1: INTERNAL PULSE (Original Dashboard)
    # =========================================================================
    with tab1:
        st.sidebar.markdown("---")
        st.sidebar.markdown("## 📄 Internal Analysis")
        
        page = st.sidebar.radio("Select Page:", 
                               ["📊 Overview", "🏷️ Topics", "😊 Sentiment", "🎯 Aspects", "🔍 Explorer"],
                               label_visibility="collapsed",
                               key="internal_pulse_nav")
        
        # Route to page
        if page == "📊 Overview":
            page_overview(df, topic_keywords)
        elif page == "🏷️ Topics":
            page_topics(df, topic_keywords)
        elif page == "😊 Sentiment":
            page_sentiment(df, topic_keywords)
        elif page == "🎯 Aspects":
            page_aspects(topic_keywords)
        elif page == "🔍 Explorer":
            page_explorer(df, topic_keywords)
    
    # =========================================================================
    # TAB 2: MARKET BATTLEGROUND (Competitive Module)
    # =========================================================================
    with tab2:
        page_market_battleground()
    
    # =========================================================================
    # TAB 3: STRATEGIC DEEP DIVE (Advanced Analytics)
    # =========================================================================
    with tab3:
        page_strategic_deep_dive()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #6b7280; padding: 1rem;'>
            <p>📊 BPCL Reviews Analytics Dashboard | Built with Streamlit & Plotly</p>
            <p>Built by Atharv Patil</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# =============================================================================
# RUN APP
# =============================================================================
if __name__ == "__main__":
    main()
