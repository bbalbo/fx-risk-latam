# src/correlation.py
# Computes correlation matrices between FX return series.
# Calcula matrices de correlacion entre series de retornos cambiarios.
#
# Correlation measures how similarly two currencies move on a daily basis.
# Values near +1 = move together, near -1 = move in opposite directions, near 0 = independent.
#
# La correlacion mide que tan similarmente se mueven dos monedas dia a dia.
# Valores cerca de +1 = se mueven juntas, cerca de -1 = direcciones opuestas, cerca de 0 = independientes.
#
# Important: always compute correlation on returns, not on price levels.
# Price levels tend to share common trends, which inflates correlations artificially.
#
# Importante: siempre calcular correlacion sobre retornos, no sobre niveles de precio.
# Los niveles de precio tienden a compartir tendencias comunes, lo que infla artificialmente las correlaciones.

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def full_correlation(returns: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """
    Full-period pairwise correlation matrix of daily returns.
    Matriz de correlacion por pares para el periodo completo de retornos diarios.

    This gives a single historical snapshot. Use rolling_correlation() to track
    how relationships between currencies have changed over time.
    Esto da un snapshot historico unico. Usar rolling_correlation() para ver
    como han cambiado las relaciones entre monedas en el tiempo.

    Parameters / Parametros:
        returns: DataFrame of daily log returns
        method : "pearson" (linear) or "spearman" (rank-based, more robust to outliers)
                 "pearson" (lineal) o "spearman" (basado en rangos, mas robusto a valores extremos)

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"A": np.random.normal(0, 1, 100), "B": np.random.normal(0, 1, 100)})
        >>> corr = full_correlation(r)
        >>> corr.shape
        (2, 2)
        >>> corr.loc["A", "A"]
        1.0
    """
    corr = returns.corr(method=method)
    logger.info("Full-period correlation matrix computed (%s): %dx%d", method, *corr.shape)
    return corr


def rolling_correlation(returns: pd.DataFrame, base: str, window: int = 252) -> pd.DataFrame:
    """
    Rolling pairwise correlation between one base currency and all others.
    Correlacion movil por pares entre una moneda base y todas las demas.

    Useful for spotting shifts in currency relationships — for example,
    whether CLP and BRL became more correlated during a commodity cycle,
    or whether a currency decoupled from the region after a local shock.

    Util para detectar cambios en las relaciones entre monedas — por ejemplo,
    si CLP y BRL se volvieron mas correlacionadas durante un ciclo de commodities,
    o si una moneda se desacoplo de la region tras un shock local.

    Parameters / Parametros:
        returns: DataFrame of daily log returns
        base   : reference currency column name (e.g. "CLP")
        window : rolling window in trading days

    Returns / Retorna:
        pd.DataFrame — one column per currency (base excluded), index = dates.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(1)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 1, 300),
        ...                    "BRL": np.random.normal(0, 1, 300)})
        >>> rc = rolling_correlation(r, base="CLP", window=30)
        >>> "BRL" in rc.columns
        True
        >>> "CLP" in rc.columns
        False
    """
    if base not in returns.columns:
        raise ValueError(f"Base currency '{base}' not found in returns columns.")

    other = [col for col in returns.columns if col != base]
    rolling_corr = pd.DataFrame(index=returns.index, columns=other, dtype=float)

    for currency in other:
        rolling_corr[currency] = returns[base].rolling(window=window).corr(returns[currency])

    logger.info("Rolling correlation computed: base=%s, window=%dd, %d pairs", base, window, len(other))
    return rolling_corr


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.correlation
#
if __name__ == "__main__":
    import logging
    from src.returns import load_rates, log_returns

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rates   = load_rates()
    returns = log_returns(rates)

    print("\nFull-period correlation matrix / Matriz de correlacion periodo completo:\n")
    print(full_correlation(returns).round(2).to_string())

    print("\nRolling correlation vs CLP (252d) — last 5 rows / Correlacion movil vs CLP (252d) — ultimas 5 filas:\n")
    print(rolling_correlation(returns, base="CLP", window=252).tail(5).round(2).to_string())
