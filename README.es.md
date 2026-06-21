# FX Risk LatAm

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/pandas-2.0%2B-150458)
![NumPy](https://img.shields.io/badge/numpy-1.26%2B-013243)
![Estado](https://img.shields.io/badge/estado-activo-success)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)

> 🇬🇧 Looking for the English version? Read **[README.md](README.md)**.

Un toolkit cuantitativo de riesgo de mercado para monedas latinoamericanas. Extrae datos diarios de tipo de cambio y calcula retornos, volatilidad, correlación, Valor en Riesgo, escenarios de estrés y anomalías estadísticas — los mismos componentes que usan las mesas de riesgo cambiario institucionales, condensados en una base de código Python pequeña y legible.

---

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Por qué este proyecto](#por-qué-este-proyecto)
- [Monedas incluidas](#monedas-incluidas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Inicio rápido](#inicio-rápido)
- [Referencia de módulos](#referencia-de-módulos)
- [Notas de metodología](#notas-de-metodología)
- [Fuente de datos](#fuente-de-datos)
- [Ideas a futuro](#ideas-a-futuro)
- [Licencia](#licencia)

---

## Descripción general

**FX Risk LatAm** responde una pregunta simple para un libro de monedas regional: *¿qué tan riesgosa es esta exposición, y qué tan riesgosa fue durante una crisis?*

El flujo de trabajo es:

```
API Frankfurter  →  SQLite (tasas crudas)  →  retornos  →  métricas de riesgo
```

A partir de ahí, se calculan cuatro lentes de riesgo estándar:

| Lente | Pregunta que responde | Módulo |
|---|---|---|
| **Volatilidad** | ¿Cuánto se mueve esta moneda, recientemente vs. históricamente? | `volatility.py` |
| **Valor en Riesgo (VaR) / Pérdida Esperada** | ¿Cuál es la peor pérdida diaria que debería esperar, con cierto nivel de confianza? | `var.py` |
| **Correlación** | ¿Estas monedas se mueven juntas, o de forma independiente? | `correlation.py` |
| **Stress testing** | ¿Qué pasó realmente con esta moneda durante el COVID, las alzas de tasas de la Fed en 2022, la devaluación del ARS en 2023, o el desarme del carry trade del JPY en 2024? | `stress.py` |
| **Detección de anomalías** | ¿Qué días específicos fueron estadísticamente extremos, sin ningún supuesto previo sobre la causa? | `anomalies.py` |

## Por qué este proyecto

La mayoría de los tutoriales públicos de FX se quedan en "graficar el tipo de cambio". Este proyecto va un nivel más profundo, hacia el tipo de análisis que realmente produce una mesa de riesgo:

- **VaR histórico, no paramétrico** — los retornos de FX en Latam tienen colas pesadas (curtosis alta). Un modelo de VaR paramétrico (distribución normal) subestimaría sistemáticamente el riesgo de cola para monedas como ARS o MXN, por lo que este proyecto usa simulación histórica en su lugar.
- **Stress testing basado en eventos, no solo estadística** — el VaR resume toda una distribución; el stress testing aísla eventos específicos y nombrables (COVID, alzas de la Fed, una devaluación real) y reporta qué pasó en concreto. Eso es mucho más difícil de descartar frente a un comité de riesgo — o en una entrevista.
- **Dos perspectivas de FX, no solo una** — la mayoría de los recursos asumen por defecto una vista solo en USD. Este proyecto construye tanto una tabla base USD como una tabla base CLP, de modo que los mismos datos también responden "¿cómo se ve esto desde Chile?"

## Monedas incluidas

**Núcleo LatAm (7):**

| Código | Moneda |
|---|---|
| CLP | Peso chileno |
| BRL | Real brasileño |
| ARS | Peso argentino |
| MXN | Peso mexicano |
| COP | Peso colombiano |
| PEN | Sol peruano |
| VES | Bolívar soberano venezolano |

**Monedas de referencia (3)** — incluidas por razones analíticas específicas:

| Código | Moneda | Razón |
|---|---|---|
| EUR | Euro | Benchmark global |
| CNY | Yuan chino | Principal socio comercial de Chile |
| JPY | Yen japonés | Moneda refugio clásica |

**Más oro (XAU)** como activo de referencia no fiduciario, expresado tanto en USD como en CLP.

> **Nota sobre el rango de fechas:** todas las series comienzan el **2018-05-29**, fecha en que se introdujo el *bolívar soberano* venezolano (VES). Esta es una decisión de diseño deliberada — recortar todas las series a un inicio común evita mezclar huecos de datos reales con la ausencia estructural de datos de VES antes de esa fecha. Internamente los datos se extraen desde 2015 para que el forward-fill tenga valores previos disponibles justo en ese borde.

## Estructura del proyecto

```
fx-risk-latam/
├── requirements.txt
├── README.md                # versión en inglés
├── README.es.md              # este archivo
├── data/                     # se genera localmente, no se sube (ver .gitignore)
│   └── fx_data.db
└── src/
    ├── __init__.py
    ├── config.py              # monedas, rangos de fechas, rutas — fuente única de verdad
    ├── extraction.py          # extrae datos desde Frankfurter API → SQLite
    ├── returns.py              # retornos simples y logarítmicos, estadísticas resumen
    ├── volatility.py           # volatilidad móvil anualizada (30d / 90d / 252d)
    ├── var.py                  # VaR histórico + Pérdida Esperada
    ├── correlation.py          # matrices de correlación estática y móvil
    ├── stress.py                # pruebas sobre escenarios de crisis históricos
    └── anomalies.py             # detección de movimientos extremos por z-score móvil
```

## Instalación

Requiere **Python 3.10+** (el código usa type hints estilo `dict[str, tuple[str, str]]`).

```bash
git clone https://github.com/bbalbo/fx-risk-latam.git
cd fx-risk-latam
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Las dependencias son intencionalmente mínimas:

| Paquete | Propósito |
|---|---|
| `requests` | llama a la API de Frankfurter |
| `pandas` | datos tabulares, retornos, ventanas móviles |
| `numpy` | retornos logarítmicos, matemática de anualización |

No se requiere API key — [Frankfurter](https://frankfurter.dev/) es una API de tipos de cambio gratuita y abierta, con datos diarios desde 1948.

## Inicio rápido

**1. Extraer y guardar los datos** (ejecutar una vez, o cuando quieras datos actualizados):

```bash
python -m src.extraction
```

Esto construye dos tablas SQLite locales en `data/fx_data.db`:
- `fx_rates_usd` — todas las monedas vs. USD (Tabla A)
- `fx_rates_clp` — todas las monedas vs. CLP, la perspectiva chilena (Tabla B)

**2. Ejecutar cualquier módulo de análisis directamente:**

```bash
python -m src.returns        # resumen de retornos (media, vol, asimetría, curtosis)
python -m src.volatility     # volatilidad anualizada 30d / 90d / 252d
python -m src.var            # VaR y Pérdida Esperada al 90/95/99% de confianza
python -m src.correlation    # correlación periodo completo + móvil vs. CLP
python -m src.stress         # retorno acumulado durante 4 crisis históricas
python -m src.anomalies      # top 20 movimientos diarios más extremos
```

**3. O usarlo como librería:**

```python
from src.returns import load_rates, log_returns
from src.var import var_summary
from src.stress import full_stress_table

rates   = load_rates()
returns = log_returns(rates)

print(var_summary(returns))
print(full_stress_table(returns))
```

Cada función pública incluye un ejemplo ejecutable en su docstring (`>>>`), así que también puedes verificar el comportamiento con `python -m doctest src/var.py -v` (o cualquier otro módulo).

## Referencia de módulos

### `config.py`
Fuente única de verdad para listas de monedas, límites de fechas y la ruta de SQLite. Cambiar el universo de análisis (por ejemplo, agregar una moneda) implica editar un solo archivo, no buscar por toda la lógica de extracción.

### `extraction.py`
Extrae tasas diarias desde Frankfurter, las pivota en una tabla ancha (fechas × monedas), y rellena hacia adelante los huecos de fines de semana/feriados para que la serie sea continua. Valida que no queden `NaN` antes de guardar — si quedan, lanza un error en vez de guardar datos incompletos silenciosamente.

### `returns.py`
Calcula tanto retornos simples (`P_t / P_{t-1} - 1`) como retornos logarítmicos (`ln(P_t / P_{t-1})`). Los retornos logarítmicos se usan en todos los análisis posteriores porque son aditivos en el tiempo y se comportan mejor estadísticamente. También calcula `return_summary()`: media, desviación estándar, volatilidad anualizada, mínimo, máximo, asimetría y curtosis — esta última motiva específicamente la elección posterior de VaR histórico (no paramétrico).

### `volatility.py`
Desviación estándar móvil de retornos logarítmicos, anualizada con la convención estándar de `√252` días de trading. Tres tamaños de ventana son estándar en riesgo de mercado: 30d (estrés de corto plazo), 90d (tendencia de mediano plazo), 252d (un año de trading). Comparar la volatilidad de 30d vs. 252d indica si una moneda está *actualmente* inusualmente calma o inusualmente estresada respecto a su propia historia.

### `var.py`
VaR y Pérdida Esperada (ES/CVaR) por **simulación histórica** al 90%, 95% y 99% de confianza. Se usa simulación histórica deliberadamente en vez de un modelo paramétrico (normal), porque los retornos de FX en Latam exhiben colas pesadas — un supuesto de distribución normal subestimaría el riesgo de cola real. El ES, adoptado por Basilea III como medida primaria de riesgo de cola en 2016, captura la *severidad* de las pérdidas más allá del corte del VaR, no solo el punto de corte.

### `correlation.py`
Calcula correlación **sobre retornos, no sobre niveles de precio** — los niveles de precio comparten tendencias comunes que inflan artificialmente la correlación. Soporta tanto un snapshot de periodo completo como correlación móvil contra una moneda base elegida, útil para detectar cambios de régimen (por ejemplo, ¿CLP y BRL se volvieron más correlacionadas durante un ciclo de commodities?).

### `stress.py`
Corre cuatro escenarios de estrés históricos predefinidos y reporta el retorno logarítmico acumulado por moneda durante cada uno:

| Escenario | Ventana |
|---|---|
| Crash COVID-19 | 20 feb – 31 mar, 2020 |
| Alzas de tasas Fed | 1 jun – 31 oct, 2022 |
| Devaluación ARS (Milei) | 11 – 15 dic, 2023 |
| Desarme carry trade JPY | 1 – 9 ago, 2024 |

A diferencia del VaR, que resume toda una distribución, esto aísla *eventos reales y nombrables* — un resultado mucho más difícil de descartar que un percentil estadístico.

### `anomalies.py`
Marca días individuales donde el retorno de una moneda se desvía más de un umbral (por defecto ±3σ) respecto a su propia media/desviación móvil de 30 días. Esto es complementario al stress testing: el stress testing parte de un evento conocido y pregunta qué pasó; la detección de anomalías parte de los datos y pregunta qué días fueron extremos, sin conocimiento previo de la causa.

## Notas de metodología

- **Convención de retornos**: todas las tasas se expresan como *unidades de moneda local por 1 USD* (Tabla A) o *por 1 CLP* (Tabla B). Un retorno **positivo** significa entonces que la moneda se **depreció** (se necesitan más unidades de moneda local para comprar un USD).
- **252 días de trading al año** es la convención estándar de anualización en riesgo de mercado — usada consistentemente en `volatility.py` y `returns.py`.
- **Convención de signos del VaR**: el VaR y el ES se reportan como números **negativos** (representan pérdidas). El ES siempre es ≤ VaR (una pérdida más negativa, es decir, mayor).
- **¿Por qué recortar la fecha de inicio a 2018-05-29 pero extraer desde 2015?** El VES no existía antes de mayo de 2018. Extraer desde 2015 le da a `ffill()` valores previos reales en los que apoyarse justo en ese borde, en vez de producir artefactos en el límite de la serie.

## Fuente de datos

Todos los datos provienen de la [API de Frankfurter](https://frankfurter.dev/) — un servicio de tipos de cambio gratuito, de código abierto y sin necesidad de API key, construido sobre las tasas de referencia del Banco Central Europeo (y datos de precio spot del oro), con historia diaria desde 1948.

## Ideas a futuro

- [ ] Agregar un archivo `LICENSE`
- [ ] Punto de entrada por CLI (`fx-risk extract`, `fx-risk var --confidence 0.99`)
- [ ] VaR paramétrico (varianza-covarianza) como línea base de comparación
- [ ] Helpers ligeros de visualización (estructura temporal de volatilidad, heatmap de correlación móvil)
- [ ] Workflow de GitHub Actions para actualizar `data/fx_data.db` periódicamente
- [ ] Suite de pruebas unitarias más allá de los doctests (`pytest`)

## Licencia

Este proyecto está licenciado bajo [PolyForm Noncommercial 1.0.0](LICENSE) — de uso libre para fines personales, educativos y no comerciales. El uso comercial requiere permiso del autor.

---

<p align="center">Construido para entender cómo se comportan realmente las monedas latinoamericanas bajo estrés — no solo cuál es su tendencia.</p>
