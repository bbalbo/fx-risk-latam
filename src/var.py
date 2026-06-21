# src/var.py
# Historical simulation Value at Risk (VaR) and Expected Shortfall (ES).
# Valor en Riesgo (VaR) y Perdida Esperada (ES) por simulacion historica.
#
# VaR answers: "What is the worst daily loss I should expect, with X% confidence?"
# A 95% VaR of -2% means: on 95% of days the loss will be less than 2%.
#
# El VaR responde: "Cual es la peor perdida diaria que debo esperar, con X% de confianza?"
# Un VaR 95% de -2% significa: el 95% de los dias la perdida sera menor a 2%.
#
# We use historical simulation — not parametric — because return distributions here
# have fat tails (high kurtosis). Parametric VaR assumes normality and would
# systematically underestimate tail risk for currencies like ARS or MXN.
#
# Usamos simulacion historica — no parametrica — porque las distribuciones de retornos
# tienen colas gordas (curtosis alta). El VaR parametrico asume normalidad y subestimaria
# sistematicamente el riesgo de cola para monedas como ARS o MXN.

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Basel III requires 99% for internal models; 95% is standard for daily monitoring.
# Basilea III exige 99% para modelos internos; 95% es estandar para monitoreo diario.
CONFIDENCE_LEVELS = [0.90, 0.95, 0.99]


def historical_var(returns: pd.DataFrame, confidence: float = 0.95) -> pd.Series:
    """
    Historical simulation VaR: the (1 - confidence) percentile of observed returns.
    VaR por simulacion historica: el percentil (1 - confianza) de los retornos observados.

    No distributional assumption is made — the empirical distribution is used directly.
    No se asume ninguna distribucion — se usa directamente la distribucion empirica.

    Returns negative values (losses). / Devuelve valores negativos (perdidas).

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.01, 1000)})
        >>> var = historical_var(r, confidence=0.95)
        >>> var["CLP"] < 0
        True
    """
    var = returns.quantile(1 - confidence)
    logger.info("Historical VaR computed at %.0f%% confidence", confidence * 100)
    return var


def expected_shortfall(returns: pd.DataFrame, confidence: float = 0.95) -> pd.Series:
    """
    Expected Shortfall (ES), also known as CVaR: average loss on the days
    that breach the VaR threshold.

    Perdida Esperada (ES), tambien conocida como CVaR: perdida promedio en los dias
    que superan el umbral del VaR.

    ES is a more complete risk measure than VaR because it captures the severity
    of tail losses, not just the cutoff point. Basel III adopted ES as its primary
    measure in 2016 for exactly this reason.

    ES es una medida mas completa que el VaR porque captura la severidad de las
    perdidas en la cola, no solo el punto de corte. Basilea III adopto el ES como
    medida primaria en 2016 por exactamente esta razon.

    ES is always <= VaR (a larger loss). / ES siempre es <= VaR (una perdida mayor).

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.01, 1000)})
        >>> es = expected_shortfall(r, confidence=0.95)
        >>> es["CLP"] < historical_var(r, confidence=0.95)["CLP"]
        True
    """
    var = historical_var(returns, confidence=confidence)
    es  = pd.Series(
        {col: returns[col][returns[col] <= var[col]].mean() for col in returns.columns},
        name="ES",
    )
    logger.info("Expected Shortfall computed at %.0f%% confidence", confidence * 100)
    return es


def var_summary(returns: pd.DataFrame) -> pd.DataFrame:
    """
    VaR and ES at all standard confidence levels in a single table.
    VaR y ES en todos los niveles de confianza estandar en una sola tabla.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> np.random.seed(0)
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.01, 1000)})
        >>> summary = var_summary(r)
        >>> "VaR_95" in summary.columns
        True
        >>> "ES_99" in summary.columns
        True
    """
    frames = {}
    for level in CONFIDENCE_LEVELS:
        label = f"{int(level * 100)}"
        frames[f"VaR_{label}"] = historical_var(returns, confidence=level)
        frames[f"ES_{label}"]  = expected_shortfall(returns, confidence=level)

    summary = pd.DataFrame(frames)
    logger.info("VaR summary computed for %d currencies at %d confidence levels",
                len(summary), len(CONFIDENCE_LEVELS))
    return summary


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.var
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
    summary = var_summary(returns)

    print("\nVaR and Expected Shortfall summary / Resumen VaR y Perdida Esperada:\n")
    print((summary * 100).round(2).to_string() + "  (%)")
