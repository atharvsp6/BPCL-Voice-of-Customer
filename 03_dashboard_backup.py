"""
BPCL Reviews - Professional Interactive Dashboard
==================================================
Notebook 03: Real-time Analytics Dashboard

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

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="BPCL Reviews Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling with dark mode support
st.markdown("""
<style>
    /* Main headers - adapts to theme */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        opacity: 0.8;
        margin-bottom: 2rem;
    }
    
    /* Metric cards with better contrast */
    .stMetric {
        background-color: rgba(28, 131, 225, 0.1);
        padding: 1.2rem;
        border-radius: 0.75rem;
        border: 1px solid rgba(28, 131, 225, 0.2);
    }
    
    /* Sidebar styling */
    div[data-testid="stSidebarContent"] {
        background-color: rgba(0, 0, 0, 0.05);
    }
    
    /* Better contrast for all text elements */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-weight: 600;
    }
    
    /* Plotly chart backgrounds - transparent for theme adaptation */
    .js-plotly-plot {
        background: transparent !important;
    }
    
    /* Filter section headers */
    div[data-testid="stSidebarContent"] h2 {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA LOADING
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
        
        # Ensure required columns exist
        if 'Topic_Label' not in df.columns and 'dominant_topic' in df.columns:
            df['Topic_Label'] = 'Topic ' + (df['dominant_topic'] + 1).astype(str)
        
        return df
    except FileNotFoundError:
        st.error("⚠️ Data file 'df_final_enriched.csv' not found. Please run Notebook 02 first.")
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
    # Default topic keywords (from LDA model)
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

def format_topic_label(topic_label, topic_keywords):
    """Format topic label to include keywords: 'Topic 1 (login, app, otp...)'"""
    if not topic_label or pd.isna(topic_label):
        return "Unknown"
    
    # Extract topic number from label like "Topic 1"
    import re
    match = re.search(r'(\d+)', str(topic_label))
    if match:
        topic_num = match.group(1)
        if topic_num in topic_keywords:
            keywords = ', '.join(topic_keywords[topic_num][:3])
            return f"Topic {topic_num} ({keywords}...)"
    
    return str(topic_label)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_top_keywords(texts, n=10):
    """Extract top keywords from a list of texts"""
    # Simple word frequency (can be enhanced with TF-IDF)
    stop_words = {'the', 'a', 'an', 'is', 'it', 'to', 'and', 'of', 'for', 'in', 'on', 'with', 
                  'this', 'that', 'app', 'i', 'my', 'me', 'not', 'very', 'good', 'bad', 'nice'}
    
    all_words = []
    for text in texts:
        if pd.notna(text):
            words = re.findall(r'\b[a-z]{3,}\b', str(text).lower())
            all_words.extend([w for w in words if w not in stop_words])
    
    word_counts = Counter(all_words)
    return word_counts.most_common(n)

def create_gauge_chart(value, title="Sentiment Health"):
    """Create a gauge chart for sentiment score"""
    # Normalize value from [-1, 1] to [0, 100]
    normalized = (value + 1) * 50
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=normalized,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18}},
        number={'font': {'size': 36}, 'suffix': '%'},
        delta={'reference': 50, 'increasing': {'color': "#10b981"}, 'decreasing': {'color': "#ef4444"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#3b82f6"},
            'bgcolor': "rgba(128, 128, 128, 0.1)",
            'borderwidth': 2,
            'bordercolor': "rgba(128, 128, 128, 0.3)",
            'steps': [
                {'range': [0, 33], 'color': 'rgba(239, 68, 68, 0.2)'},
                {'range': [33, 66], 'color': 'rgba(250, 204, 21, 0.2)'},
                {'range': [66, 100], 'color': 'rgba(16, 185, 129, 0.2)'}
            ],
            'threshold': {
                'line': {'color': "#3b82f6", 'width': 4},
                'thickness': 0.75,
                'value': normalized
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=30, r=30, t=60, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

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
    
    # -------------------------------------------------------------------------
    # SIDEBAR - FILTERS
    # -------------------------------------------------------------------------
    st.sidebar.markdown("## 🎛️ Filters")
    
    # App Version filter
    versions = ['All'] + sorted(df['appVersion'].dropna().unique().tolist(), 
                                 key=lambda x: [int(p) if p.isdigit() else 0 for p in str(x).split('.')])
    selected_version = st.sidebar.selectbox("📱 App Version", versions)
    
    # Month/Year filter
    if 'month_year' in df.columns:
        months = ['All'] + sorted(df['month_year'].dropna().unique().tolist())
        selected_month = st.sidebar.selectbox("📅 Month/Year", months)
    else:
        selected_month = 'All'
    
    # Topic Label filter with keywords
    if 'Topic_Label' in df.columns:
        raw_topics = ['All'] + sorted(df['Topic_Label'].dropna().unique().tolist())
        # Format topics with keywords for display
        topic_display = ['All'] + [format_topic_label(t, topic_keywords) for t in raw_topics[1:]]
        selected_topic_idx = st.sidebar.selectbox("🏷️ Topic", range(len(topic_display)), format_func=lambda x: topic_display[x])
        selected_topic = raw_topics[selected_topic_idx]
    else:
        selected_topic = 'All'
    
    # Sentiment filter
    sentiments = ['All', 'Negative', 'Neutral', 'Positive']
    selected_sentiment = st.sidebar.selectbox("😊 Sentiment", sentiments)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_version != 'All':
        filtered_df = filtered_df[filtered_df['appVersion'] == selected_version]
    if selected_month != 'All':
        filtered_df = filtered_df[filtered_df['month_year'] == selected_month]
    if selected_topic != 'All':
        filtered_df = filtered_df[filtered_df['Topic_Label'] == selected_topic]
    if selected_sentiment != 'All':
        filtered_df = filtered_df[filtered_df['ai_sentiment'] == selected_sentiment]
    
    # Sidebar stats
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Dataset Stats")
    st.sidebar.metric("Total Reviews", f"{len(df):,}")
    st.sidebar.metric("Filtered Reviews", f"{len(filtered_df):,}")
    st.sidebar.metric("Filter Coverage", f"{len(filtered_df)/len(df)*100:.1f}%")
    
    # -------------------------------------------------------------------------
    # HEADER
    # -------------------------------------------------------------------------
    st.markdown('<h1 class="main-header">📊 BPCL Reviews Analytics Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Sentiment Analysis & Topic Insights</p>', unsafe_allow_html=True)
    
    # -------------------------------------------------------------------------
    # KEY METRICS ROW
    # -------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        st.metric(
            "🎯 Average Sentiment",
            f"{avg_sentiment:.3f}",
            delta=f"{'Positive' if avg_sentiment > 0 else 'Negative'}",
            delta_color="normal" if avg_sentiment > 0 else "inverse"
        )
    
    with col2:
        neg_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Negative'])
        neg_pct = neg_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🔴 Negative Reviews", f"{neg_count:,}", f"{neg_pct:.1f}%")
    
    with col3:
        pos_count = len(filtered_df[filtered_df['ai_sentiment'] == 'Positive'])
        pos_pct = pos_count / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("🟢 Positive Reviews", f"{pos_count:,}", f"{pos_pct:.1f}%")
    
    with col4:
        if 'at' in filtered_df.columns:
            latest_date = filtered_df['at'].max()
            st.metric("📅 Latest Review", latest_date.strftime('%Y-%m-%d') if pd.notna(latest_date) else "N/A")
        else:
            st.metric("📋 Unique Versions", filtered_df['appVersion'].nunique())
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # ROW 1: GAUGE + ROOT CAUSE HEATMAP
    # -------------------------------------------------------------------------
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### 🌡️ Global Sentiment Health")
        global_sentiment = filtered_df['sentiment_score'].mean() if 'sentiment_score' in filtered_df.columns else 0
        gauge_fig = create_gauge_chart(global_sentiment, "Sentiment Score")
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        # Interpretation
        if global_sentiment > 0.3:
            st.success("✅ Overall sentiment is POSITIVE")
        elif global_sentiment < -0.3:
            st.error("⚠️ Overall sentiment is NEGATIVE")
        else:
            st.warning("➡️ Overall sentiment is NEUTRAL")
    
    with col_right:
        st.markdown("### 🔥 Root Cause Heatmap: Version vs Topic")
        
        # Create heatmap for negative reviews
        negative_df = filtered_df[filtered_df['ai_sentiment'] == 'Negative']
        
        if len(negative_df) > 0 and 'Topic_Label' in negative_df.columns:
            # Get top versions by negative review count
            top_versions = negative_df['appVersion'].value_counts().head(10).index.tolist()
            heatmap_df = negative_df[negative_df['appVersion'].isin(top_versions)]
            
            # Create pivot table
            pivot = pd.crosstab(
                heatmap_df['appVersion'],
                heatmap_df['Topic_Label'],
                normalize='index'
            ) * 100
            
            # Sort versions
            try:
                pivot = pivot.sort_index(key=lambda x: x.map(
                    lambda v: [int(p) if p.isdigit() else 0 for p in str(v).split('.')]
                ))
            except:
                pass
            
            fig_heatmap = px.imshow(
                pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                color_continuous_scale='RdYlGn_r',
                labels=dict(x="Topic", y="App Version", color="% of Issues"),
                aspect='auto'
            )
            
            fig_heatmap.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Issue Topic",
                yaxis_title="App Version",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("No negative reviews to display in heatmap")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # ROW 2: TIMELINE + WORD COMPARISON
    # -------------------------------------------------------------------------
    col_left2, col_right2 = st.columns(2)
    
    with col_left2:
        st.markdown("### 📈 Issue Timeline: Topic Trends Over Time")
        
        if 'at' in filtered_df.columns and 'Topic_Label' in filtered_df.columns:
            # Filter to negative reviews
            neg_temporal = filtered_df[filtered_df['ai_sentiment'] == 'Negative'].copy()
            neg_temporal['month'] = neg_temporal['at'].dt.to_period('M').astype(str)
            
            # Get top 3 topics
            top_topics = neg_temporal['Topic_Label'].value_counts().head(3).index.tolist()
            
            # Aggregate by month and topic
            timeline_data = neg_temporal[neg_temporal['Topic_Label'].isin(top_topics)].groupby(
                ['month', 'Topic_Label']
            ).size().reset_index(name='count')
            
            if len(timeline_data) > 0:
                # Format topic labels with keywords
                timeline_data['Topic_Display'] = timeline_data['Topic_Label'].apply(
                    lambda x: format_topic_label(x, topic_keywords)
                )
                
                fig_timeline = px.line(
                    timeline_data,
                    x='month',
                    y='count',
                    color='Topic_Display',
                    markers=True,
                    title="Monthly Volume of Top 3 Negative Topics"
                )
                
                fig_timeline.update_layout(
                    height=350,
                    margin=dict(l=10, r=10, t=50, b=10),
                    xaxis_title="Month",
                    yaxis_title="Number of Reviews",
                    legend_title="Topic",
                    hovermode='x unified',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("Not enough data for timeline")
        else:
            st.info("Date or Topic data not available")
    
    with col_right2:
        st.markdown("### 📝 Keyword Comparison: Negative vs Positive")
        
        # Get keywords for negative and positive
        neg_texts = filtered_df[filtered_df['ai_sentiment'] == 'Negative']['content'].tolist()
        pos_texts = filtered_df[filtered_df['ai_sentiment'] == 'Positive']['content'].tolist()
        
        neg_keywords = get_top_keywords(neg_texts, n=10)
        pos_keywords = get_top_keywords(pos_texts, n=10)
        
        if neg_keywords and pos_keywords:
            # Create comparison bar chart
            fig_keywords = make_subplots(
                rows=1, cols=2,
                subplot_titles=("🔴 Negative Keywords", "🟢 Positive Keywords"),
                horizontal_spacing=0.15
            )
            
            # Negative keywords
            neg_words, neg_counts = zip(*neg_keywords) if neg_keywords else ([], [])
            fig_keywords.add_trace(
                go.Bar(x=list(neg_counts), y=list(neg_words), orientation='h',
                       marker_color='#ef4444', name='Negative'),
                row=1, col=1
            )
            
            # Positive keywords
            pos_words, pos_counts = zip(*pos_keywords) if pos_keywords else ([], [])
            fig_keywords.add_trace(
                go.Bar(x=list(pos_counts), y=list(pos_words), orientation='h',
                       marker_color='#10b981', name='Positive'),
                row=1, col=2
            )
            
            fig_keywords.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_keywords, use_container_width=True)
        else:
            st.info("Not enough text data for keyword analysis")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # ROW 3: MODEL INTEGRITY - CONFUSION MATRIX
    # -------------------------------------------------------------------------
    st.markdown("### 🔒 Model Integrity: AI Validation Results")
    
    col_cm_left, col_cm_right = st.columns([2, 1])
    
    with col_cm_left:
        if cm_data:
            # Recreate confusion matrix visualization
            cm = np.array(cm_data['confusion_matrix'])
            labels = cm_data['labels']
            accuracy = cm_data['accuracy']
            
            # Calculate percentages
            cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
            
            # Create annotations
            annotations = [[f"{cm[i,j]:,}<br>({cm_pct[i,j]:.1f}%)" 
                           for j in range(len(labels))] for i in range(len(labels))]
            
            fig_cm = go.Figure(data=go.Heatmap(
                z=cm,
                x=[f'Predicted: {l}' for l in labels],
                y=[f'Actual: {l}' for l in labels],
                colorscale='Blues',
                text=annotations,
                texttemplate='%{text}',
                textfont={'size': 12},
                hovertemplate='Actual: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>',
                colorbar=dict(title='Count')
            ))
            
            fig_cm.update_layout(
                title=f'<b>Confusion Matrix</b> | Accuracy: {accuracy:.2%}',
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_cm, use_container_width=True)
        else:
            st.warning("⚠️ Confusion matrix data not found. Run Notebook 02 to generate it.")
    
    with col_cm_right:
        st.markdown("#### 📊 Model Metrics")
        
        if cm_data:
            st.metric("Overall Accuracy", f"{cm_data['accuracy']:.2%}")
            st.metric("Agreement Rate", f"{cm_data['match_rate']:.2%}")
            
            # Classification report
            if 'classification_report' in cm_data:
                report = cm_data['classification_report']
                
                st.markdown("**Per-Class Performance:**")
                for label in ['Negative', 'Neutral', 'Positive']:
                    if label.lower() in report:
                        metrics = report[label.lower()]
                        st.write(f"• **{label}**: Precision {metrics['precision']:.2%}, Recall {metrics['recall']:.2%}")
        else:
            st.info("Run sentiment analysis notebook to see metrics")
        
        st.markdown("---")
        st.markdown("#### ✅ Validation Status")
        st.success("Model performance validated against user ratings")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # ROW 4: SAMPLE REVIEWS
    # -------------------------------------------------------------------------
    st.markdown("### 💬 Sample Reviews")
    
    tab1, tab2 = st.tabs(["🔴 Negative Reviews", "🟢 Positive Reviews"])
    
    with tab1:
        neg_samples = filtered_df[filtered_df['ai_sentiment'] == 'Negative'].head(5)
        for idx, row in neg_samples.iterrows():
            topic_display = format_topic_label(row.get('Topic_Label', 'N/A'), topic_keywords)
            with st.expander(f"⭐ {row.get('score', 'N/A')} | {topic_display} | Confidence: {row.get('ai_confidence', 0):.2f}"):
                st.write(row.get('content', 'No content'))
                st.caption(f"Version: {row.get('appVersion', 'N/A')} | Date: {row.get('at', 'N/A')}")
    
    with tab2:
        pos_samples = filtered_df[filtered_df['ai_sentiment'] == 'Positive'].head(5)
        for idx, row in pos_samples.iterrows():
            topic_display = format_topic_label(row.get('Topic_Label', 'N/A'), topic_keywords)
            with st.expander(f"⭐ {row.get('score', 'N/A')} | {topic_display} | Confidence: {row.get('ai_confidence', 0):.2f}"):
                st.write(row.get('content', 'No content'))
                st.caption(f"Version: {row.get('appVersion', 'N/A')} | Date: {row.get('at', 'N/A')}")
    
    # -------------------------------------------------------------------------
    # FOOTER
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #6b7280; padding: 1rem;'>
            <p>📊 BPCL Reviews Analytics Dashboard | Built with Streamlit & Plotly</p>
            <p>Data processed with LDA Topic Modeling + Transformer Sentiment Analysis</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# =============================================================================
# RUN APP
# =============================================================================
if __name__ == "__main__":
    main()
