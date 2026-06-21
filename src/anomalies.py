# src/anomalies.py
# Detects statistically extreme daily moves using a rolling z-score.
# Detecta movimientos diarios estadisticamente extremos usando un z-score movil.
#
# This is different from stress testing: stress testing isolates known events
# ("what happened during COVID?"), while anomaly detection finds extreme days
# without any prior knowledge of what caused them.
#
# Esto es distinto del stress testing: el stress testing aisla eventos conocidos
# ("que paso durante el COVID?"), mientras que la deteccion de anomalias encuentra
# dias extremos sin conocimiento previo de sus causas.
#
# Method: for each day, compute how many standard deviations the return deviates
# from the rolling mean. Flag anything beyond +/- threshold (default 3.0 sigma).
# Under a normal distribution, a 3-sigma event would occur ~0.3% of the time.
#
# Metodo: para cada dia, calcular cuantas desviaciones estandar se aleja el retorno
# de la media movil. Marcar todo lo que supere +/- umbral (por defecto 3.0 sigma).
# Bajo una distribucion normal, un evento de 3 sigma ocurriria ~0.3% del tiempo.

import logging

import pandas as pd

from src.volatility import WINDOW_30D

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 3.0


def rolling_zscore(returns: pd.DataFrame, window: int = WINDOW_30D) -> pd.DataFrame:
    """
    Rolling z-score: z = (r_t - rolling_mean) / rolling_std.

    A z-score of +3 means the return was 3 standard deviations above the recent average —
    a large depreciation relative to recent history. Negative z-scores indicate appreciation.

    Un z-score de +3 significa que el retorno estuvo 3 desviaciones estandar por encima del
    promedio reciente — una depreciacion grande. Z-scores negativos indican apreciacion.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.005, 100)})
        >>> z = rolling_zscore(r, window=30)
        >>> z.shape == r.shape
        True
    """
    rolling_mean = returns.rolling(window=window).mean()
    rolling_std  = returns.rolling(window=window).std()
    return (returns - rolling_mean) / rolling_std


def detect_anomalies(
    returns: pd.DataFrame,
    window: int = WINDOW_30D,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """
    Boolean mask: True where |z-score| exceeds the threshold.
    Mascara booleana: True donde |z-score| supera el umbral.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.005, 200)})
        >>> flags = detect_anomalies(r, window=30, threshold=3.0)
        >>> flags.dtypes["CLP"].name
        'bool'
    """
    flags = rolling_zscore(returns, window=window).abs() > threshold
    logger.info("Anomaly detection: %d events flagged (threshold=%.1fsigma)", flags.sum().sum(), threshold)
    return flags


def anomaly_report(
    returns: pd.DataFrame,
    window: int = WINDOW_30D,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """
    Tidy table of all flagged events, sorted by absolute z-score (most extreme first).
    Each row is one currency on one date, with the actual return and z-score.

    Tabla ordenada de todos los eventos marcados, ordenados por z-score absoluto.
    Cada fila es una moneda en una fecha, con el retorno real y el z-score.

    Returns / Retorna:
        pd.DataFrame with columns [date, currency, return_pct, zscore].

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(42)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.005, 300)})
        >>> report = anomaly_report(r, window=30, threshold=3.0)
        >>> list(report.columns)
        ['date', 'currency', 'return_pct', 'zscore']
    """
    zscore = rolling_zscore(returns, window=window)
    flags  = zscore.abs() > threshold

    records = []
    for currency in returns.columns:
        for date in returns.index[flags[currency]]:
            records.append({
                "date":       date,
                "currency":   currency,
                "return_pct": round(returns.loc[date, currency] * 100, 4),
                "zscore":     round(zscore.loc[date, currency], 2),
            })

    report = (
        pd.DataFrame(records)
        .sort_values("zscore", key=lambda s: s.abs(), ascending=False)
        .reset_index(drop=True)
    )

    logger.info("Anomaly report: %d events across %d currencies", len(report), returns.shape[1])
    return report


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.anomalies
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
    report  = anomaly_report(returns)

    print(f"\nTop 20 anomalous events / Top 20 eventos anomalos (threshold={DEFAULT_THRESHOLD}σ):\n")
    print(report.head(20).to_string(index=False))

    print("\nAnomaly count by currency / Cantidad de anomalias por moneda:\n")
    print(report["currency"].value_counts().to_string())
