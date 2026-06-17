# Multi-Dimensional Options Volatility Surface Cleaner

An institutional-grade derivatives analytics pipeline that ingests raw, noisy options exchange data, executes dynamic arbitrage filtering, and calibrates a continuous 3D parametric SABR Volatility Surface.

This system bridges raw exchange market microstructure friction with continuous-time asset pricing models, providing risk managers with both automated data cleaning and structural macroeconomic scenario stress-testing capabilities.

## 🧠 Core Quantitative Features

* **Newton-Raphson IV Extraction:** Implemented an optimized numerical root-finding algorithm to invert the non-linear Black-Scholes pricing model and isolate exact Implied Volatilities ($\sigma$).
* **Microstructure Arbitrage Filtering:** Programmed continuous logical guardrails to scan, flag, and strip out stale data feeds, illiquid gapping contracts, and intrinsic value boundary violations ($C < \max(S - K, 0)$).
* **SABR Stochastic Volatility Fitting:** Integrated the industry-standard Hagan parametric approximation. The model utilizes non-linear least squares optimization via Levenberg-Marquardt tracking algorithms to calibrate underlying parameters:
    * **Alpha ($\alpha$):** Baseline vertical displacement asset volatility anchor.
    * **Rho ($\rho$):** Asymmetrical smile skew/tilt modeling directional equity market panic.
    * **Nu ($\nu$):** Parabolic volatility-of-volatility (Vol-of-Vol) dictating wing convexity curvature.

---

## 📈 Underlying Mathematical Specifications

The continuous 3D topographic surface is rendered via the Hagan SABR formulation, modeling the localized implied volatility pathing across strike and maturity dimensions:

$$\sigma_{\text{SABR}}(K) = \frac{\alpha \cdot \left\{1 + \left[\frac{(1-\beta)^2}{24}\frac{\alpha^2}{(F \cdot K)^{1-\beta}} + \frac{1}{4}\frac{\rho \cdot \beta \cdot \alpha \cdot \nu}{(F \cdot K)^{\frac{1-\beta}{2}}} + \frac{2-3\rho^2}{24}\nu^2\right] \cdot T\right\}}{(F \cdot K)^{\frac{1-\beta}{2}} \cdot \left[1 + \frac{(1-\beta)^2}{24}\ln^2(F/K) + \frac{(1-\beta)^4}{1920}\ln^4(F/K)\right]} \cdot \left(\frac{z}{x(z)}\right)$$

Root convergence for individual market data nodes is achieved iteratively through local derivative optimization steps:

$$\sigma_{n+1} = \sigma_n - \frac{C_{\text{Black-Scholes}}(\sigma_n) - C_{\text{Market}}}{\nu(\sigma_n)}$$

Where Vega ($\nu$) tracks localized sensitivity transformations across the distribution curve.

---

## 🚀 Local Installation & Execution

### 1. Clone the Project Workspace
```bash
git clone [https://github.com/YOUR_GITHUB_USERNAME/volatility-surface-cleaner.git](https://github.com/YOUR_GITHUB_USERNAME/volatility-surface-cleaner.git)
cd volatility-surface-cleaner