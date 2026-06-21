# src/config.py
# Central configuration for the FX Risk LatAm project.
# Configuracion central del proyecto Panel de Riesgo Cambiario LatAm.
#
# Keeping constants here means changing a date range or adding a currency
# never requires touching the extraction logic itself.
# Mantener las constantes aqui significa que cambiar un rango de fechas
# o agregar una moneda no requiere tocar la logica de extraccion.

# -------------------------------------------------------------------
# DATA SOURCE / FUENTE DE DATOS
# -------------------------------------------------------------------
# Frankfurter API — free, no API key required, daily data since 1948.
# Frankfurter API — gratuita, sin API key, datos diarios desde 1948.
API_BASE_URL = "https://api.frankfurter.dev/v2/rates"

# -------------------------------------------------------------------
# CURRENCIES / MONEDAS
# -------------------------------------------------------------------
# LatAm core (7): the regional currencies we're analyzing.
# Nucleo LatAm (7): las monedas regionales que analizamos.
LATAM_CURRENCIES = ["CLP", "BRL", "ARS", "MXN", "COP", "PEN", "VES"]

# Global references added for specific analytical reasons:
# Referencias globales incluidas por razones analiticas especificas:
#   EUR — global benchmark / benchmark global
#   CNY — Chile's largest trading partner / principal socio comercial de Chile
#   JPY — classic safe-haven currency / moneda refugio clasica
REFERENCE_CURRENCIES = ["EUR", "CNY", "JPY"]

# Table A — base USD: USD is the denominator, so it's excluded from quotes.
# Tabla A — base USD: el USD es el denominador, por eso no aparece en las quotes.
TABLE_A_QUOTES = LATAM_CURRENCIES + REFERENCE_CURRENCIES

# Table B — base CLP: Chilean perspective. USD flips to a quote currency here.
# Tabla B — base CLP: perspectiva chilena. El USD pasa a ser una moneda cotizada.
TABLE_B_QUOTES = ["USD"] + [c for c in LATAM_CURRENCIES if c != "CLP"] + REFERENCE_CURRENCIES

# -------------------------------------------------------------------
# DATE RANGE / RANGO DE FECHAS
# -------------------------------------------------------------------
# VES (Venezuelan bolivar soberano) was introduced on 2018-05-29.
# All series are cut to this date to avoid structural NaNs — a deliberate
# design decision to keep the dataset clean rather than mixing real gaps
# with weekend gaps.
#
# El VES (bolivar soberano venezolano) se introdujo el 2018-05-29.
# Todas las series se recortan a esta fecha para evitar NaN estructurales —
# una decision de diseno deliberada para no mezclar huecos reales con huecos
# de fin de semana.
COMMON_START_DATE = "2018-05-29"

# Pull from 2015 so the ffill has prior values to work with at the VES boundary.
# Traemos desde 2015 para que el ffill tenga valores previos en el borde de VES.
EXTRACTION_START_DATE = "2015-01-01"

# -------------------------------------------------------------------
# STORAGE / ALMACENAMIENTO
# -------------------------------------------------------------------
DB_PATH      = "data/fx_data.db"
DB_TABLE_USD = "fx_rates_usd"   # Table A — base USD
DB_TABLE_CLP = "fx_rates_clp"   # Table B — base CLP
