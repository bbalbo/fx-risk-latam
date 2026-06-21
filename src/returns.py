# src/returns.py
# Computes daily log and simple returns from FX rate data.
# Calcula retornos diarios logaritmicos y simples desde datos de tipo de cambio.
#
# All downstream analyses — volatility, VaR, correlations — operate on returns,
# not on raw price levels. This module is the single source of that transformation.
#
# Todos los analisis posteriores — volatilidad, VaR, correlaciones — operan sobre
# retornos, no sobre niveles de precio. Este modulo es la unica fuente de esa transformacion.
#
# Interpretation note / Nota de interpretacion:
#   Data is expressed as "units of local currency per 1 USD".
#   A positive return in CLP means the peso depreciated (more pesos per dollar).
#   Los datos estan expresados como "unidades de moneda local por 1 USD".
#   Un retorno positivo en CLP significa que el peso se deprecio (mas pesos por dolar).

import logging
import sqlite3

import numpy as np
import pandas as pd

from src.config import DB_PATH, DB_TABLE_USD

logger = logging.getLogger(__name__)


def load_rates(db_path: str = DB_PATH, table: str = DB_TABLE_USD) -> pd.DataFrame:
    """
    Loads the FX rate table from SQLite and returns it with a proper DatetimeIndex.
    Carga la tabla de tipos de cambio desde SQLite y la devuelve con un DatetimeIndex correcto.

    Example / Ejemplo:
        >>> df = load_rates()
        >>> isinstance(df.index, pd.DatetimeIndex)
        True
        >>> df.index.name
        'date'
    """
    logger.info("Loading rates from %s, table '%s'", db_path, table)
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT * FROM {table}", conn, parse_dates=["date"], index_col="date")
    conn.close()
    return df


def simple_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes daily simple (arithmetic) returns: r_t = (P_t / P_{t-1}) - 1.
    Calcula retornos simples (aritmeticos) diarios: r_t = (P_t / P_{t-1}) - 1.

    The first row is dropped because it has no prior day to compare against.
    La primera fila se descarta porque no tiene dia anterior con que comparar.

    Example / Ejemplo:
        >>> import pandas as pd
        >>> prices = pd.DataFrame({"CLP": [600.0, 612.0, 606.0]},
        ...                        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
        >>> r = simple_returns(prices)
        >>> round(r["CLP"].iloc[0], 6)
        0.02
        >>> round(r["CLP"].iloc[1], 6)
        -0.009804
    """
    return df.pct_change().dropna(how="all")


def log_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes daily log returns: r_t = ln(P_t / P_{t-1}).
    Calcula retornos logaritmicos diarios: r_t = ln(P_t / P_{t-1}).

    Log returns are preferred for statistical analysis because they are time-additive
    and better-behaved under aggregation across periods.
    Los retornos logaritmicos se prefieren para analisis estadistico porque son aditivos
    en el tiempo y se comportan mejor al agregar periodos.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> prices = pd.DataFrame({"CLP": [600.0, 612.0, 606.0]},
        ...                        index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]))
        >>> r = log_returns(prices)
        >>> round(r["CLP"].iloc[0], 6)
        0.019803
        >>> round(r["CLP"].iloc[1], 6)
        -0.009852
    """
    return np.log(df / df.shift(1)).dropna(how="all")


def return_summary(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Summary statistics per currency: mean, std, annualized volatility,
    min, max, skew, and kurtosis.

    Estadisticas resumen por moneda: media, desviacion estandar, volatilidad anualizada,
    minimo, maximo, asimetria y curtosis.

    Kurtosis > 3 indicates heavier tails than a normal distribution — relevant
    for choosing between parametric and historical VaR.
    Curtosis > 3 indica colas mas pesadas que una distribucion normal — relevante
    para elegir entre VaR parametrico e historico.

    Example / Ejemplo:
        >>> import pandas as pd
        >>> r = pd.DataFrame({"CLP": [0.01, -0.005, 0.02, -0.01, 0.005]})
        >>> summary = return_summary(r)
        >>> list(summary.columns)
        ['mean', 'std', 'annualized_vol', 'min', 'max', 'skew', 'kurtosis']
    """
    summary = pd.DataFrame({
        "mean":           returns.mean(),
        "std":            returns.std(),
        "annualized_vol": returns.std() * np.sqrt(252),  # 252 trading days / dias de trading
        "min":            returns.min(),
        "max":            returns.max(),
        "skew":           returns.skew(),
        "kurtosis":       returns.kurtosis(),
    })

    logger.info("Return summary computed for %d currencies", len(summary))
    return summary


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.returns
#
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rates   = load_rates()
    r_log   = log_returns(rates)
    summary = return_summary(r_log)

    print("\nLog return summary / Resumen de retornos logaritmicos:\n")
    print(summary.to_string())
