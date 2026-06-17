import numpy as np
import plotly.graph_objects as go
import streamlit as st

# Import our custom domain calculators
from volatility_engine import extract_implied_volatility, black_scholes_call
from sabr_model import sabr_volatility, fit_sabr_parameters

# ==========================================
# 1. STREAMLIT INITIAL INTERFACE CONFIG
# ==========================================
st.set_page_config(layout="wide", page_title="SABR Volatility Surface Cleaner")
st.title("🎛️ Volatility Surface Data Cleaner & Fitter")
st.markdown("Ingest raw market options chains, filter out arbitrage violations, and fit a smooth 3D parametric SABR surface.")

# --- SIDEBAR: SYSTEM CONTROLS ---
st.sidebar.header("🚨 System Dashboard Configurations")

spot_price = st.sidebar.number_input("Underlying Asset Spot Price ($)", value=100.0, step=5.0)
risk_free_rate = st.sidebar.slider("Risk-Free Rate (r) %", 0.0, 10.0, 4.5, step=0.1) / 100

# Operational Mode Switch
st.sidebar.markdown("---")
mode = st.sidebar.radio("Dashboard Operational Mode", ["Manual Stress Test", "Auto-Fit to Market Data"])

# Fallback/Manual Sliders
st.sidebar.subheader("SABR Parameters (Manual Controls)")
slider_alpha = st.sidebar.slider("Alpha (α) - Baseline Vol Level", 0.05, 0.60, 0.25, step=0.01)
slider_rho = st.sidebar.slider("Rho (ρ) - Smile Skew/Tilt", -0.95, 0.95, -0.40, step=0.05)
slider_nu = st.sidebar.slider("Nu (ν) - Vol-of-Vol (Wing Curvature)", 0.05, 1.00, 0.40, step=0.01)

# ==========================================
# 2. GENERATE RAW NOISY MARKET OPTIONS CHAINS
# ==========================================
@st.cache_data
def generate_synthetic_market_data(S, r, alpha, rho, nu):
    np.random.seed(42) 
    maturities = np.array([0.08, 0.25, 0.50, 1.00]) 
    strikes = np.arange(70, 135, 5) 
    
    raw_data = []
    for T in maturities:
        for K in strikes:
            true_vol = sabr_volatility(S, K, T, alpha, 0.5, rho, nu)
            true_price = black_scholes_call(S, K, T, r, true_vol)
            
            # Inject structural exchange noise & bid-ask friction
            noise = np.random.normal(0, 0.15)
            market_price = true_price + noise
            
            # Inject arbitrage bounds violations (5% probability)
            if np.random.rand() < 0.05:
                market_price = max(0.1, (S - K) - 2.50) 
                
            raw_data.append({
                "Maturity": T,
                "Strike": K,
                "Market Price": max(0.05, market_price)
            })
    return raw_data

raw_market_book = generate_synthetic_market_data(spot_price, risk_free_rate, 0.25, -0.40, 0.40)

# ==========================================
# 3. PROCESS DATA: CALCULATE & FILTER DATA
# ==========================================
clean_strikes = []
clean_maturities = []
clean_raw_vols = []

for contract in raw_market_book:
    T = contract["Maturity"]
    K = contract["Strike"]
    price = contract["Market Price"]
    
    iv = extract_implied_volatility(price, spot_price, K, T, risk_free_rate)
    
    if iv > 1e-4 and iv < 1.50: 
        clean_strikes.append(K)
        clean_maturities.append(T)
        clean_raw_vols.append(iv)

# ==========================================
# 4. THE AUTOMATED PIPELINE OVERRIDE INTERFACE
# ==========================================
if mode == "Auto-Fit to Market Data":
    if len(clean_raw_vols) > 0:
        try:
            # Calibrate parameter variables instantly via Least-Squares optimization
            fitted_alpha, fitted_rho, fitted_nu = fit_sabr_parameters(
                market_strikes=clean_strikes,
                market_vols=clean_raw_vols,
                F=spot_price,
                T=0.5
            )
            slider_alpha = fitted_alpha
            slider_rho = fitted_rho
            slider_nu = fitted_nu
            st.sidebar.success("🎉 SABR Surface Calibrated Successfully!")
        except Exception as e:
            st.sidebar.error(f"Optimization convergence failed, using manual fallbacks. Error: {e}")
    else:
        st.sidebar.warning("Insufficient clean data points to calibrate.")

# ==========================================
# 5. QUANT MATRICES GENERATION FOR GRAPH SURFACE
# ==========================================
grid_strikes = np.linspace(70, 130, 30)
grid_maturities = np.linspace(0.08, 1.00, 20)
X_grid, Y_grid = np.meshgrid(grid_strikes, grid_maturities)

Z_surface = np.zeros_like(X_grid)
for i in range(len(grid_maturities)):
    for j in range(len(grid_strikes)):
        Z_surface[i, j] = sabr_volatility(
            F=spot_price, 
            K=X_grid[i, j], 
            T=Y_grid[i, j], 
            alpha=slider_alpha, 
            beta=0.5, 
            rho=slider_rho, 
            nu=slider_nu
        )

# ==========================================
# 6. RENDER THE VISUAL PLATFORM DASHBOARD
# ==========================================
col_metrics, col_chart = st.columns([1, 3])

with col_metrics:
    st.subheader("📊 Processing Statistics")
    st.metric(label="Total Raw Contracts Scanned", value=len(raw_market_book))
    st.metric(label="Cleaned Contracts Retained", value=len(clean_raw_vols))
    st.metric(label="Arbitrage Anomaly Dropped", value=len(raw_market_book) - len(clean_raw_vols))
    
    st.markdown("---")
    st.markdown("### Calibrated Operational Parameters")
    st.text(f"Alpha (α): {slider_alpha:.4f}")
    st.text(f"Rho (ρ): {slider_rho:.4f}")
    st.text(f"Nu (ν): {slider_nu:.4f}")

with col_chart:
    st.subheader("3D Implied Volatility Surface Mesh")
    
    fig = go.Figure()
    
    # 1. Continuous calibrated SABR model sheet mesh
    fig.add_trace(go.Surface(
        x=X_grid, 
        y=Y_grid * 365, 
        z=Z_surface * 100, 
        colorscale='Viridis',
        name='SABR Clean Surface',
        colorbar_title="IV (%)"
    ))
    
    # 2. Raw noisy market anchor coordinates
    fig.add_trace(go.Scatter3d(
        x=clean_strikes,
        y=np.array(clean_maturities) * 365,
        z=np.array(clean_raw_vols) * 100,
        mode='markers',
        marker=dict(size=4, color='red', opacity=0.7),
        name='Filtered Market Data'
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis_title='Strike Price ($)',
            yaxis_title='Time to Expiry (Days)',
            zaxis_title='Implied Volatility (%)'
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=630,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    st.plotly_chart(fig, use_container_width=True)