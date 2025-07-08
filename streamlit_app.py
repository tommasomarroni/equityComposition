
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Configurazione della pagina
st.set_page_config(
    page_title="Portfolio vs Benchmark Analysis",
    page_icon="📊",
    layout="wide"
)

def clean_percentage(value):
    """Converte una stringa con percentuale europea (con virgola) in float"""
    if pd.isna(value) or value == '':
        return 0.0
    clean_val = str(value).strip().replace(',', '.')
    try:
        return float(clean_val)
    except:
        return 0.0

def load_and_clean_data(uploaded_file):
    """Carica e pulisce i dati da un file CSV"""
    try:
        # Legge il file saltando le prime 2 righe (metadata)
        df = pd.read_csv(uploaded_file, skiprows=2)

        # Pulisce la colonna delle ponderazioni
        df['Ponderazione_Clean'] = df['Ponderazione (%)'].apply(clean_percentage)

        # Filtra solo le holding azionarie e con ponderazione > 0
        df = df[(df['Asset Class'] == 'Azionario') & (df['Ponderazione_Clean'] > 0)]

        return df
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {str(e)}")
        return None

def aggregate_portfolio_data(etf_files, weights):
    """Aggrega i dati del portafoglio basato sui pesi degli ETF"""
    portfolio_holdings = {}
    portfolio_sectors = {}
    portfolio_regions = {}

    for i, (etf_file, weight) in enumerate(zip(etf_files, weights)):
        df = load_and_clean_data(etf_file)
        if df is not None:
            # Aggrega holding
            for _, row in df.iterrows():
                ticker = row["Ticker dell'emittente"]
                name = row['Nome']
                contribution = row['Ponderazione_Clean'] * weight / 100

                if ticker in portfolio_holdings:
                    portfolio_holdings[ticker]['weight'] += contribution
                else:
                    portfolio_holdings[ticker] = {
                        'name': name,
                        'weight': contribution,
                        'sector': row['Settore'],
                        'region': row['Area Geografica']
                    }

            # Aggrega settori
            sector_weights = df.groupby('Settore')['Ponderazione_Clean'].sum()
            for sector, sector_weight in sector_weights.items():
                contribution = sector_weight * weight / 100
                portfolio_sectors[sector] = portfolio_sectors.get(sector, 0) + contribution

            # Aggrega regioni
            region_weights = df.groupby('Area Geografica')['Ponderazione_Clean'].sum()
            for region, region_weight in region_weights.items():
                contribution = region_weight * weight / 100
                portfolio_regions[region] = portfolio_regions.get(region, 0) + contribution

    return portfolio_holdings, portfolio_sectors, portfolio_regions

def create_top_holdings_chart(benchmark_df, portfolio_holdings):
    """Crea il grafico delle top 10 holding"""
    # Top 10 holding del benchmark
    top_10_benchmark = benchmark_df.nlargest(10, 'Ponderazione_Clean')

    # Estrae i pesi del portafoglio per le stesse holding
    portfolio_weights = []
    holding_names = []

    for _, row in top_10_benchmark.iterrows():
        ticker = row["Ticker dell'emittente"]
        name = row['Nome']
        holding_names.append(name)

        if ticker in portfolio_holdings:
            portfolio_weights.append(portfolio_holdings[ticker]['weight'])
        else:
            portfolio_weights.append(0)

    # Crea il grafico
    fig = go.Figure(data=[
        go.Bar(name='Benchmark', x=holding_names, y=top_10_benchmark['Ponderazione_Clean'].tolist()),
        go.Bar(name='Portfolio', x=holding_names, y=portfolio_weights)
    ])

    fig.update_layout(
        title='Top 10 Holdings: Benchmark vs Portfolio',
        xaxis_title='Holdings',
        yaxis_title='Peso (%)',
        barmode='group',
        height=500,
        xaxis={'tickangle': -45}
    )

    return fig

def create_sector_comparison_chart(benchmark_df, portfolio_sectors):
    """Crea il grafico di confronto settoriale"""
    # Aggregazione settoriale del benchmark
    benchmark_sectors = benchmark_df.groupby('Settore')['Ponderazione_Clean'].sum().to_dict()

    # Unisce tutti i settori
    all_sectors = set(benchmark_sectors.keys()) | set(portfolio_sectors.keys())

    sectors = list(all_sectors)
    benchmark_weights = [benchmark_sectors.get(sector, 0) for sector in sectors]
    portfolio_weights = [portfolio_sectors.get(sector, 0) for sector in sectors]

    fig = go.Figure(data=[
        go.Bar(name='Benchmark', x=sectors, y=benchmark_weights),
        go.Bar(name='Portfolio', x=sectors, y=portfolio_weights)
    ])

    fig.update_layout(
        title='Esposizione Settoriale: Benchmark vs Portfolio',
        xaxis_title='Settori',
        yaxis_title='Peso (%)',
        barmode='group',
        height=500,
        xaxis={'tickangle': -45}
    )

    return fig

def create_region_comparison_chart(benchmark_df, portfolio_regions):
    """Crea il grafico di confronto geografico"""
    # Aggregazione geografica del benchmark
    benchmark_regions = benchmark_df.groupby('Area Geografica')['Ponderazione_Clean'].sum().to_dict()

    # Unisce tutte le regioni
    all_regions = set(benchmark_regions.keys()) | set(portfolio_regions.keys())

    regions = list(all_regions)
    benchmark_weights = [benchmark_regions.get(region, 0) for region in regions]
    portfolio_weights = [portfolio_regions.get(region, 0) for region in regions]

    fig = go.Figure(data=[
        go.Bar(name='Benchmark', x=regions, y=benchmark_weights),
        go.Bar(name='Portfolio', x=regions, y=portfolio_weights)
    ])

    fig.update_layout(
        title='Esposizione Geografica: Benchmark vs Portfolio',
        xaxis_title='Area Geografica',
        yaxis_title='Peso (%)',
        barmode='group',
        height=500,
        xaxis={'tickangle': -45}
    )

    return fig

# Interfaccia principale
st.title("📊 Analisi Portfolio vs Benchmark")
st.markdown("---")

# Sezione upload benchmark
st.header("1. Upload Benchmark")
benchmark_file = st.file_uploader(
    "Carica il file CSV del benchmark",
    type=['csv'],
    help="File CSV con la composizione del benchmark ETF"
)

if benchmark_file is not None:
    benchmark_df = load_and_clean_data(benchmark_file)

    if benchmark_df is not None:
        st.success(f"✅ Benchmark caricato: {len(benchmark_df)} holding")

        # Sezione upload portafoglio
        st.header("2. Composizione Portfolio")

        num_etfs = st.number_input(
            "Numero di ETF nel portfolio",
            min_value=1,
            max_value=10,
            value=1,
            step=1
        )

        etf_files = []
        weights = []

        col1, col2 = st.columns([3, 1])

        for i in range(num_etfs):
            with col1:
                etf_file = st.file_uploader(
                    f"ETF {i+1} - File CSV",
                    type=['csv'],
                    key=f"etf_{i}"
                )
                etf_files.append(etf_file)

            with col2:
                weight = st.number_input(
                    f"ETF {i+1} - Peso (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=100.0/num_etfs,
                    step=0.1,
                    key=f"weight_{i}"
                )
                weights.append(weight)

        # Verifica che i pesi sommino a 100%
        total_weight = sum(weights)
        if abs(total_weight - 100.0) > 0.01:
            st.warning(f"⚠️ I pesi non sommano a 100% (attuale: {total_weight:.1f}%)")
        else:
            st.success(f"✅ Pesi corretti: {total_weight:.1f}%")

        # Analisi e grafici
        if all(etf_file is not None for etf_file in etf_files):
            st.header("3. Analisi Comparativa")

            with st.spinner("Elaborazione dati del portfolio..."):
                portfolio_holdings, portfolio_sectors, portfolio_regions = aggregate_portfolio_data(etf_files, weights)

            if portfolio_holdings:
                # Grafico Top 10 Holdings
                st.subheader("📈 Top 10 Holdings")
                fig_holdings = create_top_holdings_chart(benchmark_df, portfolio_holdings)
                st.plotly_chart(fig_holdings, use_container_width=True)

                # Grafico Settoriale
                st.subheader("🏭 Esposizione Settoriale")
                fig_sectors = create_sector_comparison_chart(benchmark_df, portfolio_sectors)
                st.plotly_chart(fig_sectors, use_container_width=True)

                # Grafico Geografico
                st.subheader("🌍 Esposizione Geografica")
                fig_regions = create_region_comparison_chart(benchmark_df, portfolio_regions)
                st.plotly_chart(fig_regions, use_container_width=True)

                # Statistiche riassuntive
                st.header("4. Statistiche Riassuntive")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Holdings Benchmark",
                        len(benchmark_df)
                    )

                with col2:
                    st.metric(
                        "Holdings Portfolio",
                        len(portfolio_holdings)
                    )

                with col3:
                    overlap = len(set(portfolio_holdings.keys()) & set(benchmark_df["Ticker dell'emittente"]))
                    overlap_pct = (overlap / len(portfolio_holdings)) * 100 if portfolio_holdings else 0
                    st.metric(
                        "Overlap %",
                        f"{overlap_pct:.1f}%"
                    )
else:
    st.info("👆 Carica il file del benchmark per iniziare l'analisi")

# Footer
st.markdown("---")
st.markdown("*Sviluppato per l'analisi comparativa di portfolio ETF*")
