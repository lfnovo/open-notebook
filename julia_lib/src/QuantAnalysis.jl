module QuantAnalysis

using Dates
using Statistics
using LinearAlgebra
using Distributions
using SpecialFunctions

export calculate_gex, calculate_vanna, black_scholes_greeks
export GexResult, VannaResult, OptionsContract

"""
Options contract data structure
"""
struct OptionsContract
    strike::Float64
    expiry::Date
    is_call::Bool
    open_interest::Int64
    volume::Int64
    delta::Float64
    gamma::Float64
    vanna::Float64
    iv::Float64
end

"""
GEX calculation result
"""
struct GexResult
    total_gex::Float64
    strikes::Vector{Float64}
    gex_by_strike::Vector{Float64}
    flip_point::Union{Float64, Nothing}
end

"""
Vanna calculation result
"""
struct VannaResult
    total_vanna::Float64
    strikes::Vector{Float64}
    vanna_by_strike::Vector{Float64}
end

"""
Calculate Black-Scholes d1 and d2
"""
function bs_d1d2(S::Float64, K::Float64, r::Float64, σ::Float64, T::Float64)
    d1 = (log(S/K) + (r + 0.5*σ^2)*T) / (σ*sqrt(T))
    d2 = d1 - σ*sqrt(T)
    return d1, d2
end

"""
Calculate Black-Scholes Greeks
"""
function black_scholes_greeks(
    S::Float64,      # Spot price
    K::Float64,      # Strike
    r::Float64,      # Risk-free rate
    σ::Float64,      # Implied volatility
    T::Float64,      # Time to expiry (years)
    is_call::Bool
)
    if T <= 0
        return (delta=0.0, gamma=0.0, vanna=0.0, vega=0.0, theta=0.0)
    end

    d1, d2 = bs_d1d2(S, K, r, σ, T)

    Nd1 = cdf(Normal(), d1)
    nd1 = pdf(Normal(), d1)

    # Delta
    delta = is_call ? Nd1 : Nd1 - 1

    # Gamma (same for calls and puts)
    gamma = nd1 / (S * σ * sqrt(T))

    # Vanna = d(delta)/d(σ) = -d2 * nd1 / σ
    vanna = -nd1 * d2 / σ

    # Vega
    vega = S * nd1 * sqrt(T)

    # Theta (simplified)
    theta = -(S * nd1 * σ) / (2 * sqrt(T))

    return (delta=delta, gamma=gamma, vanna=vanna, vega=vega, theta=theta)
end

"""
Calculate Gamma Exposure (GEX) for an options chain

GEX = Σ (OI × Contract_Size × Spot × Gamma × 100)

Positive GEX = dealers are long gamma (stabilizing)
Negative GEX = dealers are short gamma (amplifying)
"""
function calculate_gex(
    spot::Float64,
    contracts::Vector{OptionsContract};
    contract_size::Int = 100
)
    strikes = unique([c.strike for c in contracts])
    sort!(strikes)

    gex_by_strike = zeros(length(strikes))

    for (i, K) in enumerate(strikes)
        for c in filter(x -> x.strike == K, contracts)
            # Dealer position is opposite of market
            # If call: dealer is short, so negative OI contribution
            # If put: dealer is long, so positive OI contribution
            sign = c.is_call ? -1 : 1
            gex = sign * c.open_interest * contract_size * spot * c.gamma
            gex_by_strike[i] += gex
        end
    end

    total_gex = sum(gex_by_strike)

    # Find GEX flip point (where cumulative GEX crosses zero)
    cumsum_gex = cumsum(gex_by_strike)
    flip_idx = findfirst(x -> x > 0, cumsum_gex)
    flip_point = flip_idx !== nothing && flip_idx > 1 ? strikes[flip_idx] : nothing

    return GexResult(total_gex, strikes, gex_by_strike, flip_point)
end

"""
Calculate Vanna Exposure for an options chain

Vanna measures how delta changes with volatility.
Useful for predicting price moves based on IV changes.
"""
function calculate_vanna(
    spot::Float64,
    contracts::Vector{OptionsContract};
    contract_size::Int = 100
)
    strikes = unique([c.strike for c in contracts])
    sort!(strikes)

    vanna_by_strike = zeros(length(strikes))

    for (i, K) in enumerate(strikes)
        for c in filter(x -> x.strike == K, contracts)
            # Vanna exposure
            vanna_exp = c.open_interest * contract_size * c.vanna
            vanna_by_strike[i] += vanna_exp
        end
    end

    total_vanna = sum(vanna_by_strike)

    return VannaResult(total_vanna, strikes, vanna_by_strike)
end

"""
Calculate charm (delta decay) exposure
"""
function calculate_charm(
    spot::Float64,
    r::Float64,
    contracts::Vector{OptionsContract};
    contract_size::Int = 100
)
    total_charm = 0.0

    for c in contracts
        T = Dates.value(c.expiry - today()) / 365.0
        if T > 0
            d1, d2 = bs_d1d2(spot, c.strike, r, c.iv, T)
            nd1 = pdf(Normal(), d1)

            # Charm = -nd1 * (2*r*T - d2*σ*√T) / (2*T*σ*√T)
            charm = -nd1 * (2*r*T - d2*c.iv*sqrt(T)) / (2*T*c.iv*sqrt(T))

            sign = c.is_call ? -1 : 1
            total_charm += sign * c.open_interest * contract_size * charm
        end
    end

    return total_charm
end

end # module
