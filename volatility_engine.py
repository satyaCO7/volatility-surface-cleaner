import numpy as np
from scipy.stats import norm

def black_scholes_call(S, K, T, r, sigma):
    """
    Calculates the theoretical Black-Scholes price for a European Call Option.
    """
    # Prevent divide-by-zero errors for ultra-short maturities
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def calculate_vega(S, K, T, r, sigma):
    """
    Calculates the option Vega (sensitivity of price relative to volatility).
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return S * np.sqrt(T) * norm.pdf(d1)

def extract_implied_volatility(market_price, S, K, T, r, max_iterations=100, tolerance=1e-6):
    """
    Uses the Newton-Raphson method to iteratively back out Implied Volatility.
    """
    # Enforce Intrinsic Value Bound (Arbitrage Filter)
    intrinsic_value = max(0.0, S - K)
    if market_price <= intrinsic_value:
        return 0.0 # Discard or flag as invalid arbitrage data
        
    # Start with an initial baseline guess of 20% volatility
    sigma_guess = 0.20
    
    for _ in range(max_iterations):
        theoretical_price = black_scholes_call(S, K, T, r, sigma_guess)
        vega = calculate_vega(S, K, T, r, sigma_guess)
        
        # Prevent division by zero if vega becomes too small
        if abs(vega) < 1e-4:
            break
            
        price_error = theoretical_price - market_price
        
        # Update our guess using the Newton-Raphson adjustment
        sigma_new = sigma_guess - (price_error / vega)
        
        # If the adjustment is microscopic, we have converged on the answer!
        if abs(sigma_new - sigma_guess) < tolerance:
            return max(0.0, sigma_new)
            
        sigma_guess = sigma_new
        
    return sigma_guess # Return best estimation if max loops hit