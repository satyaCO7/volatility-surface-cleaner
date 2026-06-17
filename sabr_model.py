import numpy as np
from scipy.optimize import least_squares

def sabr_volatility(F, K, T, alpha, beta, rho, nu):
    """
    Calculates the smooth implied volatility for a given strike using the Hagan SABR formula.
    """
    # Handle the boundary condition where strike equals forward price (At-The-Money)
    if abs(F - K) < 1e-6:
        numerator = 1.0 + (((1.0 - beta)**2 / 24.0) * (alpha**2 / (F**(2.0 - 2.0 * beta))) + 
                           (0.25 * rho * beta * alpha * nu / (F**(1.0 - beta))) + 
                           ((2.0 - 3.0 * rho**2) / 24.0) * nu**2) * T
        denominator = F**(1.0 - beta)
        return alpha * numerator / denominator

    # Standard out-of-the-money calculation
    log_FK = np.log(F / K)
    f_k_beta = (F * K) ** ((1.0 - beta) / 2.0)
    
    z = (nu / alpha) * f_k_beta * log_FK
    
    # Avoid numerical instability or square root errors inside log functions
    try:
        x_z = np.log((np.sqrt(1.0 - 2.0 * rho * z + z**2) + z - rho) / (1.0 - rho))
    except:
        return alpha / f_k_beta # Fallback baseline stability parameter

    if abs(x_z) < 1e-6:
        factor = 1.0
    else:
        factor = z / x_z

    num_term = 1.0 + (((1.0 - beta)**2 / 24.0) * (alpha**2 / (F * K)**(1.0 - beta)) + 
                      (0.25 * rho * beta * alpha * nu / f_k_beta) + 
                      ((2.0 - 3.0 * rho**2) / 24.0) * nu**2) * T
                      
    den_term = 1.0 + ((1.0 - beta)**2 / 24.0) * log_FK**2 + ((1.0 - beta)**4 / 1920.0) * log_FK**4
    
    vol = (alpha / (f_k_beta * den_term)) * factor * num_term
    return max(0.0001, vol) # Force volatility to remain strictly positive

def fit_sabr_parameters(market_strikes, market_vols, F, T, beta=0.5):
    """
    Fits alpha, rho, and nu parameters to a raw list of market data points 
    using non-linear least squares regression.
    """
    # Define our objective cost function (minimize the squared errors)
    def residuals(params):
        alpha, rho, nu = params
        # Enforce mathematical boundaries inside the optimization loop
        if alpha <= 0 or rho <= -1.0 or rho >= 1.0 or nu <= 0:
            return np.full_like(market_strikes, 1e6)
            
        return [sabr_volatility(F, k, T, alpha, beta, rho, nu) - m_vol 
                for k, m_vol in zip(market_strikes, market_vols)]

    # Starting guesses for optimizer: alpha=0.2, rho= -0.4 (classic equity skew), nu=0.3
    initial_guess = [0.2, -0.4, 0.3]
    
    # Define strict search boundaries to keep physics/finance properties intact
    # alpha bounded (0, inf), rho bounded (-0.99, 0.99), nu bounded (0, inf)
    bounds = ((1e-4, -0.99, 1e-4), (np.inf, 0.99, np.inf))
    
    res = least_squares(residuals, initial_guess, bounds=bounds)
    return res.x # Returns array containing optimized [alpha, rho, nu]