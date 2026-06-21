# src/extraction.py
# Pulls FX and gold price data from Frankfurter API, cleans it,
# and stores the result in a local SQLite database.
#
# Extrae datos de tipo de cambio y precio del oro desde Frankfurter API,
# los limpia y guarda el resultado en una base de datos SQLite local.

import logging
import os
import sqlite3

import pandas as pd
import requests

from src.config import (
    API_BASE_URL,
    COMMON_START_DATE,
    DB_PATH,
    DB_TABLE_CLP,
    DB_TABLE_USD,
    EXTRACTION_START_DATE,
    TABLE_A_QUOTES,
    TABLE_B_QUOTES,
)

logger = logging.getLogger(__name__)


def fetch_fx_rates(base: str, quotes: list[str], start_date: str) -> pd.DataFrame:
    """
    Fetches historical FX rates from Frankfurter API and returns a wide-format
    DataFrame (rows = dates, columns = currencies). Weekend and holiday gaps
    are forward-filled so the index is continuous.

    Extrae tasas de cambio historicas desde Frankfurter API y devuelve un DataFrame
    en formato ancho (filas = fechas, columnas = monedas). Los huecos de fines de
    semana y feriados se rellenan hacia adelante para que el indice sea continuo.

    Parameters / Parametros:
        base      : base currency code (e.g. "USD", "CLP", "XAU")
        quotes    : list of target currency codes (e.g. ["CLP", "BRL", "ARS"])
        start_date: earliest date to include, format "YYYY-MM-DD"
    """
    params = {
        "base": base,
        "quotes": ",".join(quotes),
        "from": start_date,
    }

    logger.info("Requesting %s/%s from %s", base, ",".join(quotes), start_date)
    response = requests.get(API_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    df_long = pd.DataFrame(response.json())
    df_wide = df_long.pivot(index="date", columns="quote", values="rate")

    # Trim to start_date — the API occasionally returns one row before the requested date.
    # Recortar a start_date — la API a veces devuelve una fila antes de la fecha solicitada.
    df_wide = df_wide.loc[start_date:]

    # ffill covers weekend/holiday gaps; bfill(limit=1) handles the very first row
    # in case it falls on a global holiday (e.g. January 1st).
    # ffill cubre fines de semana y feriados; bfill(limit=1) maneja la primera fila
    # si cae en un feriado global (ej. 1 de enero).
    df_wide = df_wide.ffill().bfill(limit=1)

    return df_wide


def build_master_table() -> pd.DataFrame:
    """
    Builds Table A: all currencies vs USD, joined with gold (XAU/USD).
    Series are cut to COMMON_START_DATE so VES has no structural NaNs.

    Construye la Tabla A: todas las monedas vs USD, unida con el oro (XAU/USD).
    Las series se recortan a COMMON_START_DATE para que VES no tenga NaN estructurales.

    Returns / Retorna:
        pd.DataFrame — 11 columns (10 FX + ORO_USD), 0 NaN.

    Raises / Lanza:
        ValueError: if any NaN remains after cleaning.
    """
    logger.info("Building Table A (USD base)")

    df_fx = fetch_fx_rates(base="USD", quotes=TABLE_A_QUOTES, start_date=EXTRACTION_START_DATE)

    # Gold: 1 XAU = N USD (price of one troy ounce in dollars).
    # Oro: 1 XAU = N USD (precio de una onza troy en dolares).
    df_gold = fetch_fx_rates(base="XAU", quotes=["USD"], start_date=EXTRACTION_START_DATE)
    df_gold = df_gold.rename(columns={"USD": "ORO_USD"})

    df_master = df_fx.loc[COMMON_START_DATE:].join(df_gold.loc[COMMON_START_DATE:])

    # Gold has isolated NaNs on certain market holidays that ffill doesn't reach
    # because it happens after the join. One extra pass fixes it.
    # El oro tiene NaN puntuales en ciertos feriados de mercado que ffill no alcanza
    # porque ocurren despues del join. Un pase adicional lo resuelve.
    df_master["ORO_USD"] = df_master["ORO_USD"].ffill()

    remaining = df_master.isna().sum().sum()
    if remaining > 0:
        raise ValueError(f"{remaining} NaN(s) remain in the master table after cleaning.")

    logger.info("Table A ready: %d rows x %d columns", df_master.shape[0], df_master.shape[1])
    return df_master


def build_clp_table() -> pd.DataFrame:
    """
    Builds Table B: all currencies vs CLP (Chilean perspective).
    Gold is expressed in CLP per troy ounce.

    Construye la Tabla B: todas las monedas vs CLP (perspectiva chilena).
    El oro se expresa en CLP por onza troy.

    Returns / Retorna:
        pd.DataFrame — 11 columns (10 FX + ORO_CLP), 0 NaN.

    Raises / Lanza:
        ValueError: if any NaN remains after cleaning.
    """
    logger.info("Building Table B (CLP base)")

    df_fx = fetch_fx_rates(base="CLP", quotes=TABLE_B_QUOTES, start_date=EXTRACTION_START_DATE)

    df_gold = fetch_fx_rates(base="XAU", quotes=["CLP"], start_date=EXTRACTION_START_DATE)
    df_gold = df_gold.rename(columns={"CLP": "ORO_CLP"})

    df_clp = df_fx.loc[COMMON_START_DATE:].join(df_gold.loc[COMMON_START_DATE:])
    df_clp["ORO_CLP"] = df_clp["ORO_CLP"].ffill()

    remaining = df_clp.isna().sum().sum()
    if remaining > 0:
        raise ValueError(f"{remaining} NaN(s) remain in the CLP table after cleaning.")

    logger.info("Table B ready: %d rows x %d columns", df_clp.shape[0], df_clp.shape[1])
    return df_clp


def save_to_sqlite(df: pd.DataFrame, db_path: str = DB_PATH, table: str = DB_TABLE_USD) -> None:
    """
    Saves a DataFrame to a local SQLite database, replacing the table if it exists.

    Guarda un DataFrame en una base de datos SQLite local, reemplazando la tabla si existe.

    reset_index() is necessary so the date index becomes a real column in SQLite —
    otherwise it gets silently dropped.
    reset_index() es necesario para que el indice de fechas quede como columna real en SQLite,
    de lo contrario se pierde silenciosamente.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    df.reset_index().to_sql(table, conn, if_exists="replace", index=False)
    conn.close()
    logger.info("Saved to %s, table '%s'", db_path, table)


# -------------------------------------------------------------------
# Entry point / Punto de entrada
# -------------------------------------------------------------------
# Run this to refresh both tables in the local database:
# Ejecutar esto para actualizar ambas tablas en la base de datos local:
#
#   python -m src.extraction
#
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    df_a = build_master_table()
    save_to_sqlite(df_a, table=DB_TABLE_USD)

    df_b = build_clp_table()
    save_to_sqlite(df_b, table=DB_TABLE_CLP)
