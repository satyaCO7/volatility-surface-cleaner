import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. CORE FINANCIAL ENGINE
# ==========================================
class Bond:
    def __init__(self, face_value, coupon_rate, maturity, payment_freq=1):
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.maturity = maturity
        self.payment_freq = payment_freq
        
    def _get_cash_flows(self):
        total_payments = int(self.maturity * self.payment_freq)
        times = np.arange(1, total_payments + 1) / self.payment_freq
        coupon_payment = (self.coupon_rate * self.face_value) / self.payment_freq
        cash_flows = np.full(total_payments, coupon_payment)
        cash_flows[-1] += self.face_value
        return times, cash_flows

    def calculate_price(self, ytm):
        times, cash_flows = self._get_cash_flows()
        discount_factors = (1 + ytm / self.payment_freq) ** -(times * self.payment_freq)
        return np.sum(cash_flows * discount_factors)

    def calculate_metrics(self, ytm):
        times, cash_flows = self._get_cash_flows()
        bond_price = self.calculate_price(ytm)
        discount_factors = (1 + ytm / self.payment_freq) ** -(times * self.payment_freq)
        present_values = cash_flows * discount_factors
        
        weights = present_values / bond_price
        macaulay_duration = np.sum(times * weights)
        modified_duration = macaulay_duration / (1 + ytm / self.payment_freq)
        dv01 = bond_price * modified_duration * 0.0001
        
        return {"Price": bond_price, "Mod_Duration": modified_duration, "DV01": dv01}

class Portfolio:
    def __init__(self):
        self.positions = []

    def add_position(self, bond, quantity=1):
        self.positions.append((bond, quantity))

    def calculate_portfolio_metrics(self, yield_curve):
        total_value = 0.0
        total_weighted_duration = 0.0
        total_dv01 = 0.0
        position_details = []

        if not self.positions:
            return {"Total Portfolio Value": 0.0, "Portfolio Mod Duration": 0.0, "Portfolio Total DV01": 0.0, "Positions Breakdown": []}

        for bond, qty in self.positions:
            available_tenors = list(yield_curve.keys())
            closest_tenor = min(available_tenors, key=lambda x: abs(x - bond.maturity))
            ytm = yield_curve[closest_tenor]
            
            metrics = bond.calculate_metrics(ytm)
            pos_value = metrics["Price"] * qty
            pos_dv01 = metrics["DV01"] * qty
            
            total_value += pos_value
            total_dv01 += pos_dv01
            
            position_details.append({
                "Maturity": bond.maturity,
                "Position Value": pos_value,
                "Mod Duration": metrics["Mod_Duration"],
                "DV01": pos_dv01
            })
            
        if total_value > 0:
            for pos in position_details:
                weight = pos["Position Value"] / total_value
                total_weighted_duration += pos["Mod Duration"] * weight

        return {
            "Total Portfolio Value": total_value,
            "Portfolio Mod Duration": total_weighted_duration,
            "Portfolio Total DV01": total_dv01,
            "Positions Breakdown": position_details
        }

def deform_yield_curve(base_curve, parallel=0.0, twist=0.0, butterfly=0.0):
    shift_p = parallel / 10000
    shift_t = twist / 10000
    shift_b = butterfly / 10000
    
    deformed_curve = {}
    for maturity, base_rate in base_curve.items():
        new_rate = base_rate + shift_p
        new_rate += shift_t * (maturity - 5)
        new_rate += shift_b * (maturity * (10 - maturity)) / 25
        deformed_curve[maturity] = max(0.0001, new_rate)
    return deformed_curve

# ==========================================
# 2. STREAMLIT FRONT-END INTERFACE
# ==========================================
st.set_page_config(layout="wide", page_title="Fixed Income Risk Simulator")
st.title("📈 Fixed Income Yield Curve Simulator")
st.markdown("Model complex macroeconomic yield curve shifts and analyze portfolio risk metrics in real-time.")

# --- SIDEBAR: ONLY KEEP SLIDERS HERE TO CLEAN UP SPACE ---
st.sidebar.header("🕹️ Curve Controls")
slider_parallel = st.sidebar.slider("Parallel Shift (Level) in bps", -200, 200, 0, step=5)
slider_twist = st.sidebar.slider("Twist Shift (Slope) in bps", -100, 100, 0, step=5)
slider_butterfly = st.sidebar.slider("Butterfly Shift (Curvature) in bps", -100, 100, 0, step=5)

# --- MAIN SCREEN: EDITABLE HOLDINGS EXPOSED AT THE TOP ---
st.subheader("💼 Active Portfolio Settings")
st.markdown("Modify values in the spreadsheet below or click the **'+ Add row'** button at the bottom of the table to add entirely new types of bonds.")

# Setup default starting rows
default_data = [
    {"Maturity (Years)": 1, "Coupon Rate (%)": 3.2, "Quantity Owned": 20000},
    {"Maturity (Years)": 2, "Coupon Rate (%)": 3.5, "Quantity Owned": 30000},
    {"Maturity (Years)": 5, "Coupon Rate (%)": 3.8, "Quantity Owned": 40000},
    {"Maturity (Years)": 10, "Coupon Rate (%)": 4.2, "Quantity Owned": 40000},
    {"Maturity (Years)": 30, "Coupon Rate (%)": 4.8, "Quantity Owned": 20000}
]

# Render the ultimate live editor grid in the main section using modern stretch syntax
edited_data = st.data_editor(
    default_data,
    num_rows="dynamic",
    width="stretch",
    key="main_portfolio_editor"
)

# Rebuild portfolio based on live edits
portfolio = Portfolio()
initial_curve = {1: 0.032, 2: 0.035, 5: 0.038, 7: 0.040, 10: 0.042, 20: 0.045, 30: 0.048}

if edited_data:
    for row in edited_data:
        if row.get("Maturity (Years)") is not None and row.get("Coupon Rate (%)") is not None and row.get("Quantity Owned") is not None:
            mat = int(row["Maturity (Years)"])
            cpn = float(row["Coupon Rate (%)"]) / 100
            qty = int(row["Quantity Owned"])
            
            # Make sure our yield curve baseline dictionary knows about this maturity tenor
            if mat not in initial_curve:
                initial_curve[mat] = 0.040 # Default baseline rate if user inputs a completely unique year
                
            portfolio.add_position(Bond(face_value=100, coupon_rate=cpn, maturity=mat), quantity=qty)

st.markdown("---")

# --- CALCULATE BASELINE & SHOCKED METRICS ---
base_metrics = portfolio.calculate_portfolio_metrics(initial_curve)
shocked_curve = deform_yield_curve(initial_curve, parallel=slider_parallel, twist=slider_twist, butterfly=slider_butterfly)
shocked_metrics = portfolio.calculate_portfolio_metrics(shocked_curve)

pnl = shocked_metrics["Total Portfolio Value"] - base_metrics["Total Portfolio Value"]

# --- MAIN DISPLAY: TOP LEVEL METRICS ---
if shocked_metrics["Total Portfolio Value"] > 0:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Portfolio Value", value=f"${shocked_metrics['Total Portfolio Value']:,.2f}")
    with col2:
        st.metric(label="Net Portfolio PnL", value=f"${pnl:,.2f}", delta=f"{pnl:,.2f}")
    with col3:
        st.metric(label="Portfolio Mod Duration", value=f"{shocked_metrics['Portfolio Mod Duration']:.2f} Yrs")
    with col4:
        st.metric(label="Portfolio Total DV01", value=f"${shocked_metrics['Portfolio Total DV01']:,.2f}")

    st.markdown("---")

    # --- VISUALIZATION: THE CHARTS ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Yield Curve Profiles")
        maturities = sorted(initial_curve.keys())
        base_rates = [initial_curve[m] * 100 for m in maturities]
        new_rates = [shocked_curve[m] * 100 for m in maturities]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=maturities, y=base_rates, name='Baseline Curve', line=dict(color='gray', width=2, dash='dash')))
        fig.add_trace(go.Scatter(x=maturities, y=new_rates, name='Shocked Curve', line=dict(color='rgb(31, 119, 180)', width=4)))
        
        fig.update_layout(
            xaxis_title="Maturity Tenor (Years)",
            yaxis_title="Yield to Maturity (%)",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(yanchor="bottom", y=0.01, xanchor="right", x=0.99)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Position Breakdown")
        breakdown_data = shocked_metrics["Positions Breakdown"]
        
        for item in breakdown_data:
            st.markdown(f"**{item['Maturity']}-Year Bond Asset**")
            st.caption(f"Value: ${item['Position Value']:,.2f} | DV01: ${item['DV01']:,.2f}")
            if shocked_metrics['Portfolio Total DV01'] > 0:
                st.progress(min(max(float(item['DV01'] / shocked_metrics['Portfolio Total DV01']), 0.0), 1.0))
else:
    st.info("💡 Please ensure there is active position data in the matrix above to view risk calculations.")