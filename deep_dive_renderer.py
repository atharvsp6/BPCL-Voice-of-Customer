"""
Deep Dive Competitive Analysis Renderer for Streamlit Dashboard

This module provides the render_deep_dive_tab() function to display
competitive analysis findings from the master report JSON.

Usage:
    from deep_dive_renderer import render_deep_dive_tab
    
    with tab3:
        render_deep_dive_tab()
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional


def render_deep_dive_tab() -> None:
    """
    Render the Deep Dive Competitive Analysis tab in Streamlit.
    
    This function loads findings from data/competitive_master_report.json and displays:
    1. Feature War (Tug-of-War) analysis with diverging bar chart
    2. Persona Analysis with styled dataframe
    3. Empathy Gap (Support Metrics) with metric cards and verdict
    
    The function handles all data loading, error checking, and visualization
    rendering with proper styling and interactivity.
    
    Returns:
        None (renders directly to Streamlit)
    
    Raises:
        FileNotFoundError: If competitive_master_report.json is not found
        json.JSONDecodeError: If JSON file is malformed
        
    Example:
        >>> import streamlit as st
        >>> from deep_dive_renderer import render_deep_dive_tab
        >>> 
        >>> st.set_page_config(page_title="Dashboard", layout="wide")
        >>> tab1, tab2, tab3 = st.tabs(["Overview", "Analysis", "Deep Dive"])
        >>> 
        >>> with tab3:
        ...     render_deep_dive_tab()
    """
    
    # ============================================================================
    # STEP 1: LOAD DATA FROM JSON
    # ============================================================================
    
    json_path = 'data/competitive_master_report.json'
    
    try:
        if not os.path.exists(json_path):
            st.error(f"❌ Report file not found: {json_path}")
            st.info("💡 Run the Deep Dive Analysis notebook to generate this file.")
            return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            master_report = json.load(f)
        
        # Extract data sections
        feature_war_data = master_report.get('feature_war', {}).get('data', [])
        personas_data = master_report.get('personas', {}).get('data', [])
        empathy_gap_data = master_report.get('empathy_gap', {}).get('data', [])
        last_updated = master_report.get('metadata', {}).get('last_updated', 'Unknown')
        
    except json.JSONDecodeError as e:
        st.error(f"❌ Error reading JSON file: {str(e)}")
        return
    except Exception as e:
        st.error(f"❌ Unexpected error loading data: {str(e)}")
        return
    
    # Display last updated timestamp
    st.caption(f"📅 Last Updated: {last_updated}")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 1: THE TUG-OF-WAR (FEATURE WAR ANALYSIS)
    # ============================================================================
    
    st.subheader("⚔️ The Tug-of-War: Feature War Analysis")
    
    if not feature_war_data:
        st.warning("⚠️ No Feature War data available")
    else:
        try:
            # Convert to DataFrame for easier handling
            fw_df = pd.DataFrame(feature_war_data)
            
            # Prepare data for Plotly
            aspects = fw_df['Aspect'].tolist()
            deltas = fw_df['Delta'].tolist()
            
            # Determine colors: Green for BPCL wins (Delta > 0), Red for IOCL wins (Delta < 0)
            colors = [
                '#2ecc71' if delta > 0 else '#e74c3c' if delta < 0 else '#95a5a6'
                for delta in deltas
            ]
            
            # Create diverging bar chart
            fig_fw = go.Figure(data=[
                go.Bar(
                    y=aspects,
                    x=deltas,
                    orientation='h',
                    marker=dict(
                        color=colors,
                        line=dict(width=2, color='darkgray')
                    ),
                    text=[f'{delta:+.2f}' for delta in deltas],
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Delta: %{x:.2f}<extra></extra>'
                )
            ])
            
            # Add center line at x=0
            fig_fw.add_vline(
                x=0,
                line_dash='dash',
                line_color='black',
                line_width=2,
                annotation_text='Neutral',
                annotation_position='top'
            )
            
            # Update layout
            fig_fw.update_layout(
                title={
                    'text': '<b>BPCL vs IOCL: Competitive Feature Gap</b><br><sub>Green = BPCL Advantage | Red = IOCL Advantage</sub>',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16}
                },
                xaxis=dict(
                    title='<b>Delta (BPCL - IOCL)</b>',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray',
                    zeroline=True,
                    zerolinewidth=2,
                    zerolinecolor='black'
                ),
                yaxis=dict(
                    title='<b>Feature Aspect</b>',
                    tickfont=dict(size=11)
                ),
                plot_bgcolor='rgba(240, 240, 240, 0.3)',
                height=400,
                margin=dict(l=150, r=100, t=100, b=60),
                hovermode='y unified',
                font=dict(family='Arial, sans-serif', size=11),
                showlegend=False
            )
            
            st.plotly_chart(fig_fw, use_container_width=True)
            
            # Summary insights
            bpcl_wins = sum(1 for d in deltas if d > 0)
            iocl_wins = sum(1 for d in deltas if d < 0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("BPCL Wins", bpcl_wins)
            with col2:
                st.metric("IOCL Wins", iocl_wins)
            with col3:
                st.metric("Total Aspects", len(aspects))
            
        except Exception as e:
            st.error(f"❌ Error rendering Feature War chart: {str(e)}")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 2: PERSONA ANALYSIS
    # ============================================================================
    
    st.subheader("👥 Persona Analysis: User Segmentation")
    
    if not personas_data:
        st.warning("⚠️ No Persona data available")
    else:
        try:
            # Convert to DataFrame
            personas_df = pd.DataFrame(personas_data)
            
            # Display dataframe with styling
            st.write("**User Personas Across Brands:**")
            
            # Style the dataframe with gradient background
            def highlight_rating(val):
                """Apply gradient background to ratings"""
                if pd.isna(val):
                    return ''
                # Normalize rating from 1-5 scale to color intensity
                if val >= 4.5:
                    return 'background-color: #d4edda'  # Dark green
                elif val >= 4.0:
                    return 'background-color: #c3e6cb'  # Light green
                elif val >= 3.5:
                    return 'background-color: #fff3cd'  # Yellow
                else:
                    return 'background-color: #f8d7da'  # Red
            
            styled_df = personas_df.style.applymap(
                highlight_rating,
                subset=['Avg_Rating']
            )
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Persona breakdown by brand
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**BPCL Personas:**")
                bpcl_personas = personas_df[personas_df['Brand'] == 'BPCL']
                for _, row in bpcl_personas.iterrows():
                    st.caption(
                        f"  • {row['Persona']}: {row['Avg_Rating']:.2f}⭐ "
                        f"({row['Share_of_Voice_%']:.1f}% of base)"
                    )
            
            with col2:
                st.write("**IOCL Personas:**")
                iocl_personas = personas_df[personas_df['Brand'] == 'IOCL']
                for _, row in iocl_personas.iterrows():
                    st.caption(
                        f"  • {row['Persona']}: {row['Avg_Rating']:.2f}⭐ "
                        f"({row['Share_of_Voice_%']:.1f}% of base)"
                    )
            
        except Exception as e:
            st.error(f"❌ Error rendering Persona Analysis: {str(e)}")
    
    st.markdown("---")
    
    # ============================================================================
    # SECTION 3: EMPATHY GAP (SUPPORT METRICS)
    # ============================================================================
    
    st.subheader("💝 Empathy Gap: Customer Support Performance")
    
    if not empathy_gap_data:
        st.warning("⚠️ No Empathy Gap data available")
    else:
        try:
            # Convert to DataFrame
            empathy_df = pd.DataFrame(empathy_gap_data)
            
            # Extract BPCL and IOCL metrics
            bpcl_metrics = empathy_df[empathy_df['Brand'] == 'BPCL'].iloc[0] if len(empathy_df[empathy_df['Brand'] == 'BPCL']) > 0 else None
            iocl_metrics = empathy_df[empathy_df['Brand'] == 'IOCL'].iloc[0] if len(empathy_df[empathy_df['Brand'] == 'IOCL']) > 0 else None
            
            if bpcl_metrics is not None and iocl_metrics is not None:
                
                # Create 3-column layout for metrics
                col1, col2, col3 = st.columns(3)
                
                # COLUMN 1: BPCL Response Rate with Delta
                with col1:
                    bpcl_rr = float(bpcl_metrics['Response_Rate_%'])
                    iocl_rr = float(iocl_metrics['Response_Rate_%'])
                    delta_rr = bpcl_rr - iocl_rr
                    
                    st.metric(
                        label="📊 BPCL Response Rate",
                        value=f"{bpcl_rr:.1f}%",
                        delta=f"{delta_rr:+.1f}% vs IOCL",
                        delta_color="off"
                    )
                
                # COLUMN 2: BPCL Response Time with Bot/Human Label
                with col2:
                    bpcl_time = float(bpcl_metrics['Median_Time_Mins'])
                    bpcl_type = bpcl_metrics['Support_Type']
                    
                    # Extract emoji and type
                    is_bot = '🤖' in bpcl_type
                    type_label = "Bot" if is_bot else "Human"
                    
                    st.metric(
                        label="⚡ BPCL Response Speed",
                        value=f"{bpcl_time:.1f} min",
                        delta=f"({type_label})",
                        delta_color="off"
                    )
                
                # COLUMN 3: Competitive Verdict
                with col3:
                    # Determine verdict based on comparative metrics
                    rr_advantage = bpcl_rr > iocl_rr
                    time_advantage = bpcl_time < float(iocl_metrics['Median_Time_Mins'])
                    
                    if rr_advantage and time_advantage:
                        st.success(
                            "✅ **BPCL Superior**\n\n"
                            "Faster response rate\n"
                            "and speed"
                        )
                    elif rr_advantage or time_advantage:
                        st.info(
                            "⚖️ **Mixed Results**\n\n"
                            "Competitive advantage\n"
                            "in some metrics"
                        )
                    else:
                        st.warning(
                            "⚠️ **IOCL Superior**\n\n"
                            "IOCL leads on support\n"
                            "performance"
                        )
                
                # Display detailed comparison table
                st.write("**Detailed Support Metrics Comparison:**")
                
                comparison_data = {
                    'Metric': ['Response Rate', 'Median Time (min)', 'Support Type', 'Total Reviews'],
                    'BPCL': [
                        f"{bpcl_rr:.1f}%",
                        f"{bpcl_time:.1f}",
                        bpcl_type,
                        f"{int(bpcl_metrics['Total_Reviews']):,}"
                    ],
                    'IOCL': [
                        f"{iocl_rr:.1f}%",
                        f"{float(iocl_metrics['Median_Time_Mins']):.1f}",
                        iocl_metrics['Support_Type'],
                        f"{int(iocl_metrics['Total_Reviews']):,}"
                    ]
                }
                
                comparison_df_display = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df_display, use_container_width=True, hide_index=True)
                
                # Insights
                st.write("**Key Insights:**")
                insights = []
                
                if is_bot:
                    insights.append("🤖 BPCL uses automated responses (< 10 min)")
                else:
                    insights.append(f"👤 BPCL has human agents ({bpcl_time:.1f} min avg)")
                
                if rr_advantage:
                    insights.append(f"📈 BPCL replies to {delta_rr:+.1f}% more reviews")
                else:
                    insights.append(f"📉 IOCL replies to {abs(delta_rr):.1f}% more reviews")
                
                iocl_type = iocl_metrics['Support_Type']
                if '🤖' in iocl_type and '🤖' not in bpcl_type:
                    insights.append("✨ BPCL employs human touch vs IOCL automation")
                elif '🤖' not in iocl_type and '🤖' in bpcl_type:
                    insights.append("⚡ IOCL employs human touch vs BPCL automation")
                
                for i, insight in enumerate(insights, 1):
                    st.caption(f"{i}. {insight}")
            
            else:
                st.warning("⚠️ Incomplete Empathy Gap data")
        
        except Exception as e:
            st.error(f"❌ Error rendering Empathy Gap analysis: {str(e)}")
    
    st.markdown("---")
    
    # Footer
    st.caption(
        "📊 **Data Source:** Deep Dive Competitive Analysis | "
        "🔄 **Fresh 10k Balanced Dataset** | "
        "📈 **Zero Volume Bias**"
    )


if __name__ == "__main__":
    # Test function when run directly
    st.set_page_config(page_title="Deep Dive Test", layout="wide")
    st.title("🎯 Competitive Deep Dive Analysis")
    render_deep_dive_tab()
