# BPCL Reviews Dashboard - Deployment Guide

## 📊 About
Interactive Streamlit dashboard for analyzing BPCL customer reviews with sentiment analysis and topic modeling.

## 🚀 Quick Start (Local Deployment)

### Prerequisites
- Python 3.8 or higher
- Virtual environment (already set up in `venv/`)

### Step 1: Activate Virtual Environment
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows Command Prompt
.\venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

### Step 2: Install Dependencies (if not already installed)
```bash
pip install -r requirements.txt
```

### Step 3: Run the Dashboard
```bash
streamlit run 03_dashboard.py
```

The dashboard will open automatically in your default browser at `http://localhost:8501`

## 📁 Required Files
Ensure these data files exist before running:
- ✅ `df_final_enriched.csv` - Main dataset with sentiment and topics
- ✅ `confusion_matrix_data.json` - Sentiment analysis metrics
- ✅ `topic_keywords.json` - Topic modeling keywords

If missing, run the analysis notebooks first:
1. `02_sentiment_analysis.ipynb`
2. `topic_modeling.ipynb`

## 🌐 Cloud Deployment Options

### Option 1: Streamlit Community Cloud (Recommended - FREE)

**Requirements:**
- GitHub account
- Public or private repository

**Steps:**

1. **Create a GitHub Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - BPCL Dashboard"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/bpcl-dashboard.git
   git push -u origin main
   ```

2. **Create `.gitignore` file** (Important!)
   ```
   venv/
   __pycache__/
   *.pyc
   .env
   .DS_Store
   .vscode/
   .ipynb_checkpoints/
   *.ipynb
   hello_bpcl_reviews_100k.csv
   ```

3. **Sign in to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"

4. **Configure Deployment**
   - Repository: `YOUR_USERNAME/bpcl-dashboard`
   - Branch: `main`
   - Main file path: `03_dashboard.py`
   - Click "Deploy"

5. **Your app will be live at:**
   `https://YOUR_USERNAME-bpcl-dashboard-03-dashboard-HASH.streamlit.app`

**Advantages:**
- ✅ Completely FREE
- ✅ Automatic HTTPS
- ✅ Auto-deploy on git push
- ✅ Easy sharing with public URL
- ✅ No server management

### Option 2: Heroku

**Steps:**

1. **Install Heroku CLI**
   - Download from [heroku.com](https://devcenter.heroku.com/articles/heroku-cli)

2. **Create `Procfile`**
   ```
   web: sh setup.sh && streamlit run 03_dashboard.py
   ```

3. **Create `setup.sh`**
   ```bash
   mkdir -p ~/.streamlit/
   echo "\
   [server]\n\
   headless = true\n\
   port = $PORT\n\
   enableCORS = false\n\
   \n\
   " > ~/.streamlit/config.toml
   ```

4. **Deploy**
   ```bash
   heroku login
   heroku create bpcl-dashboard
   git push heroku main
   ```

### Option 3: AWS/Azure/GCP

For enterprise deployments, you can use:
- **AWS EC2** with Docker
- **Azure App Service**
- **Google Cloud Run**

Contact your DevOps team for infrastructure setup.

## 🔧 Configuration

### Custom Theme
Edit [.streamlit/config.toml](.streamlit/config.toml) to customize colors:
```toml
[theme]
primaryColor = "#1c83e1"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### Server Settings
Adjust in [.streamlit/config.toml](.streamlit/config.toml):
```toml
[server]
maxUploadSize = 200  # MB
port = 8501
address = "localhost"
```

## 🐛 Troubleshooting

### Issue: ModuleNotFoundError
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Data files not found
**Solution:**
Run the analysis notebooks first:
```bash
jupyter notebook 02_sentiment_analysis.ipynb
```

### Issue: Port already in use
**Solution:**
```bash
# Specify different port
streamlit run 03_dashboard.py --server.port 8502
```

### Issue: Streamlit Cloud deployment fails
**Solutions:**
1. Check `requirements.txt` is in root directory
2. Ensure all data files are committed to git
3. Check file paths are relative, not absolute
4. Review Streamlit Cloud logs for specific errors

## 📊 Dashboard Features

- **Real-time Analytics**: Filter by date, sentiment, rating, and topics
- **Interactive Visualizations**: Plotly charts with zoom, pan, hover
- **Sentiment Analysis**: View overall sentiment health and trends
- **Topic Modeling**: Explore topic distributions and keywords
- **Confusion Matrix**: Evaluate sentiment model performance
- **Export Data**: Download filtered datasets

## 🔐 Security Notes

For production deployments:
1. Never commit sensitive data or API keys
2. Use `.streamlit/secrets.toml` for secrets (not tracked in git)
3. Enable authentication if needed
4. Review data privacy compliance

## 📈 Performance Tips

- Keep CSV files optimized (< 100 MB for best performance)
- Use `@st.cache_data` decorator for expensive operations
- Consider data sampling for very large datasets
- Monitor Streamlit Cloud resource usage

## 📞 Support

For issues or questions:
- Check [Streamlit Documentation](https://docs.streamlit.io)
- Review [Streamlit Community Forum](https://discuss.streamlit.io)

## 📄 License

Proprietary - BPCL Internal Use Only

---

**Quick Commands:**
```bash
# Local development
streamlit run 03_dashboard.py

# With specific port
streamlit run 03_dashboard.py --server.port 8502

# Clear cache and restart
streamlit cache clear
```
