# BPCL Dark Theme - Quick Visual Guide

## 🎨 Color Reference Card

### Background Layers (Navy Gradient System)
```
Layer 1 - Page Background
├─ #0f1419 (Deep charcoal navy)
│
Layer 2 - Sidebar & Elevated Sections  
├─ #1a2332 (Elevated navy)
│
Layer 3 - Cards & Containers
├─ #212d3d (Card background)
│
Layer 4 - Hover & Active States
└─ #263447 (Interactive elevation)
```

### Text Hierarchy
```
KPI Values & Critical Data
├─ #ffffff (Maximum brightness) - 2rem, 700 weight
│
Primary Headlines & Titles
├─ #f0f3f7 (High contrast white) - 2.8rem, 800 weight
│
Body Text & Labels
├─ #f0f3f7 (High contrast white) - 1rem, 400 weight
│
Secondary Labels & Hints
├─ #8a98ab (Muted gray) - 0.9rem, 400 weight
│
Captions & Footnotes
└─ #5e6c7f (Subtle gray) - 0.85rem, 400 weight
```

### BPCL Brand Accents
```
Primary Actions & Highlights
├─ #1e88e5 (Petroleum Blue) + glow: rgba(30, 136, 229, 0.25)

Positive Sentiment & Success
├─ #00c853 (Energy Green)

Warnings & Highlights
├─ #ff6f00 (Petroleum Orange) - Use sparingly

Negative Sentiment & Alerts
└─ #ff3d00 (Alert Red)
```

---

## 📊 Chart Styling Guide

### Standard Plotly Configuration
```python
colors = get_theme_colors()

fig.update_layout(
    # Backgrounds
    paper_bgcolor='rgba(0,0,0,0)',      # Transparent
    plot_bgcolor=colors['plot_bg'],      # #1a2332
    
    # Title
    title=dict(
        text="Chart Title",
        font=dict(
            color=colors['text_bright'],  # #ffffff
            size=16,
            weight=700
        ),
        x=0.05  # Left-aligned
    ),
    
    # X-Axis
    xaxis=dict(
        gridcolor=colors['grid'],         # rgba(138,152,171,0.08)
        tickfont=dict(
            color=colors['secondary_text'], # #8a98ab
            size=11
        ),
        titlefont=dict(
            color=colors['text'],          # #f0f3f7
            size=13,
            weight=600
        )
    ),
    
    # Y-Axis (use grid_major for primary axis)
    yaxis=dict(
        gridcolor=colors['grid_major'],   # rgba(138,152,171,0.12)
        tickfont=dict(
            color=colors['secondary_text'],
            size=11
        ),
        titlefont=dict(
            color=colors['text'],
            size=13,
            weight=600
        )
    ),
    
    # Font
    font=dict(
        family='Inter, system-ui, sans-serif',
        color=colors['text']
    )
)
```

### Altair Configuration
```python
chart = alt.Chart(data).mark_line().encode(
    x=alt.X('date:T',
        axis=alt.Axis(
            labelColor=colors['secondary_text'],
            titleColor=colors['text'],
            gridColor=colors['grid'],
            domainColor=colors['border']
        )
    )
).configure_view(
    strokeWidth=0,
    fill=colors['plot_bg']
).configure_legend(
    titleColor=colors['text'],
    labelColor=colors['text'],
    fillColor=colors['card_bg'],
    strokeColor=colors['border'],
    cornerRadius=8
)
```

---

## 🎯 Component Recipes

### KPI Metric Card
```python
# In CSS (apply_theme_css):
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #212d3d 0%, #1a2332 100%);
    border: 1px solid rgba(30, 136, 229, 0.4);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 
        0 4px 12px rgba(0, 0, 0, 0.3),
        0 0 20px rgba(30, 136, 229, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

# Accent bar (vertical left):
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #1e88e5 0%, #00c853 100%);
}
```

### Section Header
```python
st.markdown("### 📊 Section Title")

# Styled in CSS:
.stMarkdown h3 {
    font-weight: 600;
    font-size: 1.4rem;
    color: #f0f3f7;
    margin-top: 2rem;
    border-bottom: 2px solid rgba(138, 152, 171, 0.1);
    padding-bottom: 0.5rem;
}
```

### Interactive Button (Sidebar)
```python
if st.sidebar.button("🌙 Dark"):
    st.session_state.theme = 'dark'
    st.rerun()

# Styled in CSS:
div[data-testid="stSidebarContent"] button:hover {
    background-color: #263447;
    border-color: #1e88e5;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
}
```

### Sentiment Gauge
```python
def create_gauge_chart(value, title):
    # Dynamic color based on value
    normalized = (value + 1) * 50
    if normalized >= 66:
        bar_color = colors['accent_green']  # #00c853
    elif normalized <= 33:
        bar_color = colors['negative']      # #ff3d00
    else:
        bar_color = colors['primary']       # #1e88e5
    
    # Build gauge with BPCL styling...
```

---

## 🔧 Testing Checklist

### Visual Quality
- [ ] All KPI values clearly visible (#ffffff)
- [ ] All section headers stand out (#f0f3f7, 700 weight)
- [ ] Cards have visible borders and depth
- [ ] Sidebar distinct from main content
- [ ] Chart text readable (no dark-on-dark)
- [ ] Hover states provide visual feedback
- [ ] Focus states show petroleum blue ring

### Functional
- [ ] Theme toggle works (Light ↔ Dark)
- [ ] Theme persists across page navigation
- [ ] All filters apply correctly
- [ ] Charts render without errors
- [ ] Export button functional
- [ ] Search highlights work

### Cross-Page Consistency
- [ ] Overview page: Metrics, timeline, gauge, pie, bar charts
- [ ] Topics page: Topic selector, keyword display, distribution charts
- [ ] Sentiment page: Violin plots, heatmaps, distribution
- [ ] Explorer page: Data table, sort controls, pagination

---

## 🎭 Dark Theme Activation Steps

1. **Launch Dashboard**
   ```bash
   streamlit run 03_dashboard.py
   ```

2. **Open Browser**
   - Navigate to `http://localhost:8502`

3. **Activate Dark Mode**
   - Open sidebar (if collapsed)
   - Scroll to "🎨 Theme" section
   - Click **🌙 Dark** button

4. **Verify Styling**
   - Check KPI cards have glow and borders
   - Verify text is bright white (#ffffff for values)
   - Confirm charts match dark theme
   - Test hover effects on cards/buttons

5. **Navigate Pages**
   - Overview → Topics → Sentiment → Explorer
   - Verify theme persists across all pages
   - Check all charts render correctly

---

## 🐛 Troubleshooting

### Issue: KPI values not visible
**Fix**: Ensure `text_bright` color is `#ffffff` in `get_theme_colors()`

### Issue: Cards blend into background
**Fix**: Check CSS injection happening (inspect browser dev tools)

### Issue: Charts have light background
**Fix**: Verify `plot_bgcolor=colors['plot_bg']` in all chart updates

### Issue: Sidebar same color as main content
**Fix**: Confirm sidebar gradient CSS targeting `section[data-testid="stSidebar"]`

### Issue: Theme doesn't persist
**Fix**: Theme stored in `st.session_state`, resets on browser refresh (Streamlit limitation)

---

## 📱 Responsive Behavior

### Desktop (>1200px)
- Full sidebar visible
- 4-column metric layouts
- Wide charts with legends

### Tablet (768-1200px)
- Collapsible sidebar
- 2-column metric layouts
- Charts stack vertically

### Mobile (<768px)
- Hamburger sidebar
- Single-column metrics
- Full-width charts

**Note**: Streamlit handles responsiveness automatically; CSS uses `use_container_width=True` for charts.

---

## 🚀 Deployment Considerations

### Streamlit Cloud
- CSS injection works identically
- No additional configuration needed
- Theme toggle functional in production

### Performance
- CSS: <10ms injection time
- No external resources loaded
- Charts render at normal speed
- No impact on data processing

### Browser Support
- ✅ Chrome/Edge: Full support
- ✅ Firefox: Full support
- ✅ Safari: Full support (macOS/iOS)
- ⚠️ IE11: Not supported (Streamlit limitation)

---

**Pro Tip**: For best experience, use Chrome/Edge with hardware acceleration enabled for smooth chart interactions and CSS transitions.
