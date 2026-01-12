# 📊 BPCL Reviews Analytics Dashboard

A comprehensive analytics platform for analyzing BPCL customer reviews with sentiment analysis, topic modeling, and interactive visualizations.

## 🎯 Features

- **Real-time Sentiment Analysis** - Analyze customer sentiment trends over time
- **Topic Modeling** - Discover key themes and issues in customer feedback
- **Interactive Visualizations** - Explore data with Plotly charts
- **Advanced Filtering** - Filter by date, sentiment, rating, and topics
- **Performance Metrics** - View confusion matrix and model accuracy
- **Data Export** - Download filtered datasets for further analysis

## 🚀 Quick Start

### Method 1: Using Launch Scripts (Easiest)

**Windows:**
```bash
# Double-click or run:
start_dashboard.bat
```

**PowerShell:**
```powershell
.\start_dashboard.ps1
```

### Method 2: Manual Launch

```bash
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
.\venv\Scripts\activate.bat  # Windows CMD

# 2. Run dashboard
streamlit run 03_dashboard.py
```

The dashboard will automatically open at: **http://localhost:8501**

## 📋 Prerequisites

- Python 3.8 or higher
- Virtual environment (included in `venv/`)
- Required data files:
  - ✅ `df_final_enriched.csv`
  - ✅ `confusion_matrix_data.json`
  - ✅ `topic_keywords.json`

## 📦 Installation

If starting fresh or need to reinstall packages:

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

## 📁 Project Structure

```
Voc_Bpcl2/
├── 03_dashboard.py              # Main dashboard application
├── 02_sentiment_analysis.ipynb  # Sentiment analysis notebook
├── topic_modeling.ipynb         # Topic modeling notebook
├── analysis.ipynb               # Additional analysis
├── requirements.txt             # Python dependencies
├── DEPLOYMENT.md                # Detailed deployment guide
├── .streamlit/
│   ├── config.toml             # Streamlit configuration
│   └── secrets.toml            # Secrets (not in git)
├── df_final_enriched.csv       # Main dataset
├── confusion_matrix_data.json  # Model metrics
├── topic_keywords.json         # Topic mappings
└── start_dashboard.*           # Launch scripts
```

## 🌐 Deployment

### Local Deployment ✅ (Already Done!)
Your dashboard is ready to run locally. Just use the launch scripts.

### Cloud Deployment 🌍

For detailed cloud deployment instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**

**Quick Cloud Deploy Options:**

1. **Streamlit Community Cloud** (FREE & Recommended)
   - Push code to GitHub
   - Connect to [share.streamlit.io](https://share.streamlit.io)
   - Auto-deploys on git push
   - Get a public URL to share

2. **Heroku** (Easy deployment)
   - Uses included `Procfile`
   - One-command deploy

3. **AWS/Azure/GCP** (Enterprise)
   - Full control and scalability

## 🎨 Dashboard Features

### 1. Overview Metrics
- Total reviews analyzed
- Average sentiment score
- Sentiment distribution
- Rating breakdown

### 2. Sentiment Analysis
- Sentiment health gauge
- Trends over time
- Confusion matrix
- Model performance metrics

### 3. Topic Modeling
- Topic distribution charts
- Keyword extraction
- Topic-sentiment correlation
- Interactive topic explorer

### 4. Advanced Filters
- Date range selection
- Sentiment filtering (Positive/Neutral/Negative)
- Rating filters (1-5 stars)
- Topic-based filtering

### 5. Data Explorer
- View raw reviews
- Search functionality
- Export filtered data
- Sample reviews by category

## 🛠️ Configuration

### Theme Customization
Edit [.streamlit/config.toml](.streamlit/config.toml):
```toml
[theme]
primaryColor = "#1c83e1"     # Main accent color
backgroundColor = "#FFFFFF"   # Page background
secondaryBackgroundColor = "#F0F2F6"  # Sidebar/cards
textColor = "#262730"        # Text color
```

### Server Settings
```toml
[server]
port = 8501              # Default port
maxUploadSize = 200      # Max file size in MB
```

## 🔧 Troubleshooting

### Dashboard won't start
```bash
# Check if virtual environment is activated
# You should see (venv) in your terminal

# Reinstall dependencies
pip install -r requirements.txt
```

### Missing data files
```bash
# Run the analysis notebooks first
jupyter notebook 02_sentiment_analysis.ipynb
```

### Port already in use
```bash
# Use a different port
streamlit run 03_dashboard.py --server.port 8502
```

### Module not found errors
```bash
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Install missing packages
pip install -r requirements.txt
```

## 📊 Data Pipeline

```
Raw Reviews (CSV)
    ↓
Sentiment Analysis (BERT/RoBERTa)
    ↓
Topic Modeling (LDA/BERTopic)
    ↓
Enriched Dataset
    ↓
Interactive Dashboard
```

## 🔐 Security

- Secrets stored in `.streamlit/secrets.toml` (not tracked in git)
- Data files excluded from public repositories
- XSRF protection enabled
- CORS configured for security

## 📈 Performance

- **Caching**: Uses Streamlit's `@st.cache_data` for optimal performance
- **Data Loading**: Lazy loading with progress indicators
- **Visualizations**: Interactive Plotly charts with zoom/pan
- **Responsive**: Works on desktop, tablet, and mobile

## 🤝 Contributing

For internal BPCL use only. For changes or improvements:
1. Test changes locally
2. Update documentation
3. Follow code style guidelines
4. Create detailed commit messages

## 📞 Support

**Issues or Questions?**
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment help
- Review Streamlit docs: [docs.streamlit.io](https://docs.streamlit.io)
- Contact the analytics team

## 📝 Version History

- **v1.0.0** - Initial dashboard release
  - Sentiment analysis integration
  - Topic modeling visualization
  - Interactive filters
  - Export functionality

## 📄 License

Proprietary - BPCL Internal Use Only

---

## 🎯 Quick Reference

**Start Dashboard:**
```bash
.\start_dashboard.bat          # Windows (double-click)
.\start_dashboard.ps1         # PowerShell
streamlit run 03_dashboard.py # Manual
```

**Access URLs:**
- Local: http://localhost:8501
- Network: Check terminal for network URL

**Stop Dashboard:**
- Press `Ctrl+C` in terminal

**Clear Cache:**
```bash
streamlit cache clear
```

---

Made with ❤️ for BPCL Analytics Team
