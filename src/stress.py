# src/stress.py
# Stress testing: measures how historical crisis periods impacted each currency.
# Stress testing: mide como los periodos de crisis historicos impactaron cada moneda.
#
# Unlike VaR, which summarizes the full distribution, stress testing isolates
# specific episodes and asks: "what actually happened during that event?"
# This makes the results more interpretable and harder to dismiss in an interview.
#
# A diferencia del VaR, que resume la distribucion completa, el stress testing
# aisla episodios especificos y pregunta: "que ocurrio realmente durante ese evento?"
# Esto hace los resultados mas interpretables y dificiles de refutar en una entrevista.

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# HISTORICAL STRESS SCENARIOS / ESCENARIOS DE ESTRES HISTORICOS
# -------------------------------------------------------------------
# Each scenario is defined by a label and a date range that captures the
# peak-to-trough period of a known market stress event.
#
# Cada escenario se define por una etiqueta y un rango de fechas que captura
# el periodo pico-a-valle de un evento de estres de mercado conocido.
#
# Sources / Fuentes:
#   COVID-19 crash   : Feb-Mar 2020, global markets sold off sharply.
#   2022 rate hikes  : Fed tightening cycle, strong USD pressure on EM currencies.
#   ARS devaluation  : Dec 2023, Milei unified official/parallel exchange rate.
#   2024 JPY carry   : Aug 2024, unwinding of JPY carry trades caused EM volatility.

SCENARIOS: dict[str, tuple[str, str]] = {
    "COVID-19 crash (Feb-Mar 2020)":        ("2020-02-20", "2020-03-31"),
    "Fed rate hikes (Jun-Oct 2022)":        ("2022-06-01", "2022-10-31"),
    "ARS devaluation — Milei (Dec 2023)":   ("2023-12-11", "2023-12-15"),
    "JPY carry unwind (Aug 2024)":          ("2024-08-01", "2024-08-09"),
}


def scenario_returns(returns: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """
    Filters the return series to a specific date window.

    Filtra la serie de retornos a una ventana de fechas especifica.

    Parameters / Parametros:
        returns: DataFrame of daily log returns / DataFrame de retornos logaritmicos diarios
        start  : start date, format "YYYY-MM-DD" / fecha de inicio
        end    : end date, format "YYYY-MM-DD" / fecha de fin

    Returns / Retorna:
        pd.DataFrame — subset of returns within [start, end].
    """
    return returns.loc[start:end]


def scenario_cumulative(returns: pd.DataFrame, start: str, end: str) -> pd.Series:
    """
    Computes the cumulative log return over a stress window per currency.
    Represents the total FX move during the event, not just a single day.

    Calcula el retorno logaritmico acumulado durante una ventana de estres por moneda.
    Representa el movimiento total de tipo de cambio durante el evento, no solo un dia.

    For log returns, cumulative return = sum of daily log returns over the period.
    Para retornos logaritmicos, retorno acumulado = suma de retornos diarios del periodo.

    Parameters / Parametros:
        returns: DataFrame of daily log returns / DataFrame de retornos logaritmicos diarios
        start  : start date / fecha de inicio
        end    : end date / fecha de fin

    Returns / Retorna:
        pd.Series — one cumulative return per currency for the period.

    Example / Ejemplo:
        >>> import pandas as pd
        >>> r = pd.DataFrame({"CLP": [0.01, -0.02, 0.005]},
        ...                   index=pd.to_datetime(["2020-03-01", "2020-03-02", "2020-03-03"]))
        >>> cum = scenario_cumulative(r, "2020-03-01", "2020-03-02")
        >>> round(cum["CLP"], 4)
        -0.01
    """
    window = scenario_returns(returns, start, end)
    return window.sum()


def full_stress_table(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Runs all predefined scenarios and returns a summary table of cumulative returns.

    Corre todos los escenarios predefinidos y devuelve una tabla resumen de retornos acumulados.

    Each row is a scenario; each column is a currency.
    Values are cumulative log returns expressed as percentages.
    Positive = currency depreciated against USD / the base currency.
    Negative = currency appreciated.

    Cada fila es un escenario; cada columna es una moneda.
    Los valores son retornos logaritmicos acumulados expresados como porcentajes.
    Positivo = la moneda se deprecio contra USD / la moneda base.
    Negativo = la moneda se aprecio.

    Parameters / Parametros:
        returns: DataFrame of daily log returns / DataFrame de retornos logaritmicos diarios

    Returns / Retorna:
        pd.DataFrame — shape (n_scenarios x n_currencies), values in percent.

    Example / Ejemplo:
        >>> import pandas as pd, numpy as np
        >>> idx = pd.date_range("2020-02-20", "2020-03-31")
        >>> r = pd.DataFrame({"CLP": np.random.normal(0, 0.005, len(idx))}, index=idx)
        >>> table = full_stress_table(r)
        >>> "COVID-19 crash (Feb-Mar 2020)" in table.index
        True
    """
    rows = {}

    for scenario, (start, end) in SCENARIOS.items():
        # Skip scenarios outside the available data range.
        # Omitir escenarios fuera del rango de datos disponibles.
        if start < returns.index[0].strftime("%Y-%m-%d"):
            logger.warning(
                "Scenario '%s' starts before available data (%s). Skipping. / "
                "Escenario '%s' comienza antes de los datos disponibles (%s). Omitiendo.",
                scenario, returns.index[0].date(), scenario, returns.index[0].date(),
            )
            continue

        cum = scenario_cumulative(returns, start, end)
        rows[scenario] = cum * 100  # express as percentage / expresar como porcentaje

        logger.info(
            "Scenario computed: '%s' [%s → %s] / Escenario calculado: '%s' [%s → %s]",
            scenario, start, end, scenario, start, end,
        )

    table = pd.DataFrame(rows).T
    table.index.name = "scenario"

    return table


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
#   python -m src.stress
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
    table   = full_stress_table(returns)

    print("\nStress test results (cumulative log return %) / Resultados stress test (retorno log acumulado %):\n")
    print(table.round(2).to_string())
