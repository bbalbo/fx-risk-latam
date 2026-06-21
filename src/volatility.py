# src/volatility.py
# Computes rolling volatility from daily return series.
# Calcula volatilidad movil desde series de retornos diarios.
#
# Volatility = rolling standard deviation of log returns, annualized by sqrt(252).
# Volatilidad = desviacion estandar movil de retornos logaritmicos, anualizada por sqrt(252).
#
# The 252 convention (trading days per year) is standard in market risk.
# La convencion de 252 (dias de trading por anio) es estandar en riesgo de mercado.

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Standard window sizes in market risk analysis.
# Ventanas estandar en analisis de riesgo de mercado.
WINDOW_30D  = 30    # short-term stress indicator / indicador de estres de corto plazo
WINDOW_90D  = 90    # medium-term trend / tendencia de mediano plazo
WINDOW_252D = 252   # one trading year / un anio de trading


def rolling_volatility(returns: pd.DataFrame, window: int = WINDOW_30D, annualize: bool = True) -> pd.DataFrame:
    """
    Rolling standard deviation of returns over a moving window.
    Desviacion estandar movil de retornos en una ventana deslizante.

    The first (window - 1) rows will be NaN — expected behavior, not a data error.
    Las primeras (window - 1) filas seran NaN — comportamiento esperado, no un error.

    Parameters / Parametros:
        returns  : DataFrame of daily log returns
        window   : rolling window size in trading days
        annualize: if True, multiply by sqrt(252) to express as annual volatility

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> r = pd.DataFrame({"CLP": [0.01, -0.005, 0.02, -0.01, 0.005] * 10})
        >>> vol = rolling_volatility(r, window=5, annualize=False)
        >>> vol["CLP"].iloc[4:].isna().sum()
        0
        >>> vol["CLP"].iloc[:4].isna().all()
        True
    """
    vol = returns.rolling(window=window).std()
    if annualize:
        vol = vol * np.sqrt(252)

    logger.info("Rolling volatility computed: window=%dd, annualized=%s", window, annualize)
    return vol


def volatility_summary(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Most recent volatility estimate at three standard window sizes.
    Estimacion de volatilidad mas reciente en tres ventanas estandar.

    Comparing vol_30d vs vol_252d reveals the current stress regime:
    vol_30d >> vol_252d means the currency is under elevated stress right now.
    vol_30d << vol_252d means it's unusually calm relative to its own history.

    Comparar vol_30d vs vol_252d revela el regimen de estres actual:
    vol_30d >> vol_252d significa que la moneda esta bajo estres elevado ahora mismo.
    vol_30d << vol_252d significa que esta inusualmente calma respecto a su historia.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.005, 300)})
        >>> summary = volatility_summary(r)
        >>> list(summary.columns)
        ['vol_30d', 'vol_90d', 'vol_252d']
    """
    summary = pd.DataFrame({
        "vol_30d":  rolling_volatility(returns, window=WINDOW_30D).iloc[-1],
        "vol_90d":  rolling_volatility(returns, window=WINDOW_90D).iloc[-1],
        "vol_252d": rolling_volatility(returns, window=WINDOW_252D).iloc[-1],
    })

    logger.info("Volatility snapshot computed as of %s", returns.index[-1].date())
    return summary


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.volatility
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

    print("\nCurrent volatility snapshot (annualized) / Snapshot de volatilidad actual (anualizada):\n")
    print(volatility_summary(returns).to_string())

    print("\n30-day rolling volatility — last 10 rows / Volatilidad movil 30d — ultimas 10 filas:\n")
    print(rolling_volatility(returns, window=WINDOW_30D).tail(10).to_string())
