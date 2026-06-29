# FX Risk LatAm

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.35%2B-FF4B4B)
![Pandas](https://img.shields.io/badge/pandas-2.0%2B-150458)
![Status](https://img.shields.io/badge/estado-activo-success)
![License](https://img.shields.io/badge/licencia-PolyForm%20Noncommercial-blue)

> 🇬🇧 Looking for the English version? See **[README.en.md](README.en.md)**.

Panel de análisis cuantitativo de riesgo cambiario para monedas latinoamericanas. Extrae datos diarios de tipo de cambio, calcula retornos, volatilidad, correlación, Valor en Riesgo, escenarios de estrés y anomalías estadísticas — todo expuesto a través de un dashboard interactivo construido en Streamlit.

---

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Por qué este proyecto](#por-qué-este-proyecto)
- [Monedas incluidas](#monedas-incluidas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Inicio rápido](#inicio-rápido)
- [Dashboard](#dashboard)
- [Referencia de módulos](#referencia-de-módulos)
- [Notas metodológicas](#notas-metodológicas)
- [Fuente de datos](#fuente-de-datos)
- [Licencia](#licencia)

---

## Descripción general

**FX Risk LatAm** responde una pregunta concreta para un libro de monedas regional: *¿qué tan riesgosa es esta exposición, y qué tan riesgosa fue durante una crisis?*

El pipeline es:

```
Frankfurter API  →  SQLite (tasas brutas)  →  retornos  →  métricas de riesgo  →  dashboard
```

Cuatro lentes de riesgo estándar más detección de anomalías:

| Lente | Pregunta que responde | Módulo |
|---|---|---|
| **Volatilidad** | ¿Cuánto se mueve esta moneda, en el corto vs. largo plazo? | `volatility.py` |
| **VaR / Expected Shortfall** | ¿Cuál es la peor pérdida diaria esperable a un nivel de confianza dado? | `var.py` |
| **Correlación** | ¿Estas monedas se mueven juntas o independientemente? | `correlation.py` |
| **Stress testing** | ¿Qué pasó realmente durante el COVID, las subidas de la Fed, la devaluación ARS o el carry unwind del JPY? | `stress.py` |
| **Detección de anomalías** | ¿Qué días fueron estadísticamente extremos, sin asumir la causa? | `anomalies.py` |

---

## Por qué este proyecto

La mayoría de tutoriales de FX se detienen en "grafica el tipo de cambio". Este proyecto va un nivel más profundo:

- **VaR histórico, no paramétrico** — los retornos de FX en LatAm tienen colas pesadas (alta curtosis). Un modelo VaR normal subestimaría sistemáticamente el riesgo de cola en monedas como ARS o MXN.
- **Stress testing basado en eventos** — el VaR resume una distribución completa; el stress testing aísla eventos específicos y reales. Un resultado así es más difícil de ignorar frente a un comité de riesgo.
- **EWMA vs. volatilidad rolling** — se implementan ambos modelos para mostrar la diferencia práctica: el modelo rolling tiene "efecto fantasma"; el EWMA de RiskMetrics (λ=0.94) lo suaviza con decay exponencial.
- **Dos perspectivas cambiarias** — tabla base USD y base CLP, cubriendo también la perspectiva del gestor local chileno.

---

## Monedas incluidas

**LatAm core (7):**

| Código | Moneda |
|---|---|
| CLP | Peso chileno |
| BRL | Real brasileño |
| ARS | Peso argentino |
| MXN | Peso mexicano |
| COP | Peso colombiano |
| PEN | Sol peruano |
| VES | Bolívar venezolano soberano |

**Referencias globales (3):**

| Código | Moneda | Razón |
|---|---|---|
| EUR | Euro | Benchmark global |
| CNY | Yuan chino | Principal socio comercial de Chile |
| JPY | Yen japonés | Moneda refugio clásica |

**Más oro (XAU)** como referencia no fiduciaria, expresado en USD y en CLP.

> **Nota sobre rango de fechas:** todas las series comienzan el **2018-05-29**, fecha de introducción del bolívar soberano venezolano (VES). Internamente se extrae desde 2015 para que el forward-fill tenga valores previos disponibles en ese borde.

---

## Estructura del proyecto

```
fx-risk-latam/
├── app.py                    # Dashboard interactivo (Streamlit)
├── requirements.txt
├── README.md                 # Este archivo (español)
├── README.en.md              # Versión en inglés
├── .streamlit/
│   └── config.toml           # Tema: monospace, fondo blanco, sidebar oscuro
├── data/                     # Generado localmente, no committed
│   └── fx_data.db
└── src/
    ├── __init__.py
    ├── config.py             # Monedas, fechas, rutas
    ├── extraction.py         # Frankfurter API → SQLite
    ├── returns.py            # Retornos simples y log, estadísticas
    ├── volatility.py         # Volatilidad rolling y EWMA (RiskMetrics)
    ├── var.py                # VaR histórico + Expected Shortfall
    ├── correlation.py        # Correlación estática y móvil
    ├── stress.py             # Escenarios de estrés histórico
    └── anomalies.py          # Detección de movimientos extremos por z-score
```

---

## Instalación

Requiere **Python 3.10+**.

```bash
git clone https://github.com/bbalbo/fx-risk-latam.git
cd fx-risk-latam
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Dependencias:

| Paquete | Uso |
|---|---|
| `requests` | Llamadas a la Frankfurter API |
| `pandas` | Datos tabulares, retornos, ventanas móviles |
| `numpy` | Retornos log, anualización |
| `streamlit` | Dashboard interactivo |
| `plotly` | Gráficos interactivos |
| `scipy` | KDE, distribuciones teóricas, Q-Q plot |
| `statsmodels` | Línea de tendencia OLS en scatter |

No se requiere API key — [Frankfurter](https://frankfurter.dev/) es gratuita y abierta.

---

## Inicio rápido

**1. Extraer los datos** (una vez, o cuando se quieran datos frescos):

```bash
python -m src.extraction
```

Genera dos tablas en `data/fx_data.db`: `fx_rates_usd` y `fx_rates_clp`.

**2. Lanzar el dashboard:**

```bash
streamlit run app.py
```

**3. O ejecutar módulos directamente:**

```bash
python -m src.returns
python -m src.volatility
python -m src.var
python -m src.correlation
python -m src.stress
python -m src.anomalies
```

**4. O como librería:**

```python
from src.returns import load_rates, log_returns
from src.var import var_summary

rates   = load_rates()
returns = log_returns(rates)
print(var_summary(returns))
```

---

## Dashboard

El dashboard tiene 6 páginas accesibles desde el sidebar:

### Panorama Regional
Tabla resumen de todos los activos (retorno medio, volatilidad anualizada, curtosis), tipo de cambio normalizado (base 100 o valores absolutos), violin plots comparando la distribución de retornos por moneda, mapa de calor de retornos mensuales (años × meses, verde=apreciación / rojo=depreciación), y serie de retornos al cuadrado como evidencia de volatility clustering.

### Volatilidad
Volatilidad rolling (30d / 90d / 252d) o EWMA (λ=0.94). KDE ridge plot comparando la distribución histórica de volatilidad por moneda. Comparación directa Rolling vs. EWMA con panel de diferencia. Señal de estrés (ratio vol 30d / vol 252d). Autocorrelación de r² como test de efectos ARCH.

### Correlaciones
Heatmap de correlación Pearson o Spearman. Joint plot con distribuciones marginales y línea OLS. Scatter matrix (pairplot) para subconjunto seleccionado. Correlación móvil vs. CLP.

### VaR & Riesgo de Cola
VaR histórico y Expected Shortfall al 90/95/99%. Distribución empírica vs. normal teórica con líneas de VaR y ES. Q-Q Plot para visualizar directamente la desviación de la normalidad en las colas.

### Stress Testing
Mapa de calor de retornos acumulados (escenario × moneda). Lollipop chart por escenario (verde=apreciación, rojo=depreciación).

| Escenario | Período |
|---|---|
| COVID-19 crash | 20 Feb – 31 Mar 2020 |
| Fed rate hikes | 1 Jun – 31 Oct 2022 |
| Devaluación ARS (Milei) | 11 – 15 Dic 2023 |
| JPY carry unwind | 1 – 9 Ago 2024 |

### Anomalías
Timeline de eventos extremos (tamaño del punto proporcional al z-score), mapa de calor mensual de frecuencia de anomalías por moneda, conteo observado vs. esperado bajo normalidad, tabla de los 30 eventos más extremos y distribución de z-scores.

---

## Referencia de módulos

### `config.py`
Fuente única de verdad: lista de monedas, fechas de inicio, rutas de SQLite. Agregar una moneda o cambiar el rango de fechas requiere tocar solo este archivo.

### `extraction.py`
Extrae tasas desde Frankfurter API, pivota a formato ancho (fechas × monedas), forward-fill de huecos de fin de semana y feriados. Valida que no quede ningún `NaN` antes de guardar — si queda alguno, lanza en lugar de guardar datos incompletos silenciosamente.

### `returns.py`
Retornos simples y logarítmicos. Los retornos log se usan en todo el análisis posterior por ser aditivos en el tiempo: `Σr_t = ln(p_T/p_0)`. `return_summary()` incluye curtosis, que motiva el uso de VaR histórico en lugar de paramétrico.

### `volatility.py`
Volatilidad rolling anualizada (`×√252`) y EWMA (RiskMetrics). El EWMA implementa `σ²_t = λ·σ²_{t-1} + (1-λ)·r²_{t-1}` con λ=0.94 — sin efecto fantasma, con decay exponencial de shocks pasados.

### `var.py`
Simulación histórica de VaR y Expected Shortfall (ES/CVaR) al 90/95/99%. El ES, adoptado en Basilea III como medida primaria de riesgo de cola, captura la severidad de las pérdidas más allá del umbral del VaR.

### `correlation.py`
Correlación calculada sobre retornos (no niveles de precio). Los niveles comparten tendencias comunes que inflan artificialmente la correlación. Soporta snapshot completo y correlación móvil contra moneda base.

### `stress.py`
Cuatro escenarios de estrés histórico predefinidos. Los retornos log acumulados son la métrica correcta por aditividad temporal.

### `anomalies.py`
Z-score móvil (ventana 30d). Detecta días donde `|z_t| > umbral` respecto a la distribución local de cada moneda. Complementario al stress testing: parte de los datos, no de un evento conocido.

---

## Notas metodológicas

- **Convención de tasas**: tasas expresadas como *unidades de moneda local por 1 USD*. Retorno positivo = la moneda se depreció.
- **252 días/año**: convención estándar de anualización en riesgo de mercado.
- **Signo del VaR**: VaR y ES se reportan como números negativos (pérdidas). ES siempre ≤ VaR en valor absoluto.
- **Curtosis de referencia**: distribución normal = 3. Valores superiores indican fat tails.

---

## Fuente de datos

[Frankfurter API](https://frankfurter.dev/) — gratuita, sin API key, basada en tasas de referencia del BCE, con historia diaria desde 1948.

---

## Licencia

[PolyForm Noncommercial 1.0.0](LICENSE) — libre para uso personal, educativo y no comercial. Uso comercial requiere autorización del autor.

---

<p align="center">Construido para entender cómo se comportan realmente las monedas latinoamericanas bajo estrés.</p>
