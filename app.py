"""
Sales Performance Dashboard

Interactive dark-themed sales dashboard built with Streamlit, pandas and
Plotly Express. Upload your own Excel/CSV file or explore auto-generated
demo data.

Run:
    streamlit run app.py
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PAGE_TITLE = 'Sales Performance Dashboard'
REQUIRED_COLUMNS = ['Date', 'Category', 'Revenue', 'Units Sold', 'Customer Region']
CATEGORIES = ['Electronics', 'Fashion', 'Home & Living', 'Beauty', 'Sports']
REGIONS = ['Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Bali']
BASE_PRICES = {
    'Electronics': 450.0,
    'Fashion': 60.0,
    'Home & Living': 120.0,
    'Beauty': 35.0,
    'Sports': 80.0,
}
PLOTLY_TEMPLATE = 'plotly_dark'
ACCENT_COLORS = ['#00D4FF', '#7C5CFF', '#FF5C8A', '#FFB020', '#2EE59D']

CUSTOM_CSS = """
<style>
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1A1F2B 0%, #141821 100%);
        border: 1px solid #2A3142;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        min-height: 120px;
        height: 100%;
    }
    div[data-testid="stMetricLabel"] p { color: #9AA4B2; font-size: 0.9rem; }
    div[data-testid="stMetricValue"] { color: #FFFFFF; }
</style>
"""


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
def configure_page() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon='📊', layout='wide')
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def generate_dummy_data(start: str = '2024-01-01', months: int = 24,
                        seed: int = 42) -> pd.DataFrame:
    """Create realistic monthly sales data with trend and seasonality."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start, periods=months, freq='MS')
    rows = []
    for i, month_start in enumerate(dates):
        seasonality = 1 + 0.25 * np.sin(2 * np.pi * month_start.month / 12)
        trend = 1 + 0.02 * i
        for category in CATEGORIES:
            for region in REGIONS:
                units = max(1, int(rng.normal(120, 30) * seasonality * trend))
                price = BASE_PRICES[category] * rng.uniform(0.9, 1.1)
                rows.append({
                    'Date': month_start,
                    'Category': category,
                    'Revenue': round(units * price, 2),
                    'Units Sold': units,
                    'Customer Region': region,
                })
    return pd.DataFrame(rows)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith('.csv'):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Check required columns and coerce types."""
    df.columns = [str(col).strip() for col in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))

    df = df[REQUIRED_COLUMNS].copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    for col in ('Revenue', 'Units Sold'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ('Category', 'Customer Region'):
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=['Date', 'Revenue', 'Units Sold'])
    if df.empty:
        raise ValueError('No valid rows found after cleaning.')
    return df


def load_data() -> tuple[pd.DataFrame, str]:
    """Return (data, source label). Falls back to demo data."""
    st.sidebar.header('📁 Data Source')
    uploaded = st.sidebar.file_uploader(
        'Upload Excel or CSV',
        type=['xlsx', 'xls', 'csv'],
        help='Required columns: ' + ', '.join(REQUIRED_COLUMNS),
    )
    if uploaded is not None:
        try:
            return validate_and_clean(read_uploaded_file(uploaded)), uploaded.name
        except Exception as exc:
            st.sidebar.error(f'Could not load file: {exc}')
            st.sidebar.info('Showing demo data instead.')
    else:
        st.sidebar.caption('No file uploaded - using demo data.')
    return generate_dummy_data(), 'Demo data'


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
def render_sidebar_filters(df: pd.DataFrame) -> tuple[list[str], date, date]:
    st.sidebar.header('🔎 Filters')
    regions = sorted(df['Customer Region'].unique())
    selected_regions = st.sidebar.multiselect('Customer Region', regions, default=regions)

    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    date_range = st.sidebar.date_input(
        'Date Range',
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (tuple, list)):
        start = date_range[0] if len(date_range) > 0 else min_date
        end = date_range[1] if len(date_range) > 1 else max_date
    else:
        start, end = date_range, max_date
    return selected_regions, start, end


def apply_filters(df: pd.DataFrame, regions: list[str], start: date, end: date) -> pd.DataFrame:
    mask = df['Customer Region'].isin(regions) & df['Date'].dt.date.between(start, end)
    return df.loc[mask]


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
def format_currency(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f'${value / 1_000_000:,.2f}M'
    if abs(value) >= 1_000:
        return f'${value / 1_000:,.1f}K'
    return f'${value:,.2f}'


def compute_kpis(df: pd.DataFrame) -> dict:
    total_revenue = float(df['Revenue'].sum())
    total_units = float(df['Units Sold'].sum())
    monthly = df.groupby(df['Date'].dt.to_period('M'))['Revenue'].sum()

    growth = None
    if len(monthly) >= 2 and monthly.iloc[-2] > 0:
        growth = (monthly.iloc[-1] / monthly.iloc[-2] - 1) * 100

    return {
        'total_revenue': total_revenue,
        'total_units': total_units,
        'revenue_per_unit': total_revenue / total_units if total_units else 0.0,
        'top_category': df.groupby('Category')['Revenue'].sum().idxmax(),
        'mom_growth': growth,
    }


def render_kpi_cards(kpis: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    growth = kpis['mom_growth']
    col1.metric('💰 Total Revenue', format_currency(kpis['total_revenue']),
                delta=f'{growth:+.1f}% MoM' if growth is not None else None)
    col2.metric('📦 Units Sold', f"{kpis['total_units']:,.0f}")
    col3.metric('🏷️ Avg. Revenue / Unit', format_currency(kpis['revenue_per_unit']))
    col4.metric('🏆 Top Category', kpis['top_category'])


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def style_figure(fig):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(color='#E6E6E6'),
        title_font=dict(size=18),
        hoverlabel=dict(bgcolor='#1A1F2B'),
    )
    return fig


def monthly_revenue_chart(df: pd.DataFrame):
    monthly = (df.groupby(pd.Grouper(key='Date', freq='MS'))['Revenue']
               .sum().reset_index())
    fig = px.line(monthly, x='Date', y='Revenue', markers=True,
                  title='📈 Monthly Revenue',
                  color_discrete_sequence=[ACCENT_COLORS[0]])
    fig.update_traces(line=dict(width=3),
                      hovertemplate='%{x|%b %Y}<br>Revenue: $%{y:,.0f}<extra></extra>')
    fig.update_yaxes(tickprefix='$', tickformat=',.0f', gridcolor='#2A3142')
    fig.update_xaxes(showgrid=False)
    return style_figure(fig)


def category_breakdown_chart(df: pd.DataFrame):
    by_category = (df.groupby('Category', as_index=False)[['Revenue', 'Units Sold']]
                   .sum().sort_values('Revenue'))
    fig = px.bar(by_category, x='Revenue', y='Category', orientation='h',
                 title='🏷️ Revenue by Category', color='Category',
                 color_discrete_sequence=ACCENT_COLORS, text_auto='.2s',
                 hover_data={'Units Sold': ':,'})
    fig.update_traces(textposition='outside', cliponaxis=False,
                      textfont=dict(color='#E6E6E6', size=13))
    fig.update_layout(showlegend=False)
    max_revenue = by_category['Revenue'].max() if not by_category.empty else 0
    fig.update_xaxes(tickprefix='$', tickformat=',.0f', gridcolor='#2A3142',
                     range=[0, max_revenue * 1.15])
    fig.update_yaxes(title=None)
    return style_figure(fig)


# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------
def render_data_table(df: pd.DataFrame) -> None:
    with st.expander('📄 View & download filtered data'):
        st.dataframe(df.sort_values('Date'), width='stretch', hide_index=True)
        st.download_button(
            '⬇️ Download CSV',
            data=df.to_csv(index=False).encode('utf-8'),
            file_name='filtered_sales.csv',
            mime='text/csv',
        )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main() -> None:
    configure_page()
    df, source = load_data()
    regions, start, end = render_sidebar_filters(df)
    filtered = apply_filters(df, regions, start, end)

    st.title(f'📊 {PAGE_TITLE}')
    st.caption(f'Source: {source}  ·  {start:%d %b %Y} – {end:%d %b %Y}  ·  '
               f'{len(regions)} region(s) selected')

    if filtered.empty:
        st.warning('No data matches the current filters. Try widening the date range or selecting more regions.')
        st.stop()

    render_kpi_cards(compute_kpis(filtered))
    st.divider()

    left, right = st.columns((3, 2))
    with left:
        st.plotly_chart(monthly_revenue_chart(filtered), width='stretch')
    with right:
        st.plotly_chart(category_breakdown_chart(filtered), width='stretch')

    render_data_table(filtered)


if __name__ == '__main__':
    main()
