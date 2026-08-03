# CLAUDE.md

Este archivo brinda orientación a Claude Code (claude.ai/code) al trabajar con código en este repositorio.

## Qué es esto

Un bot de RPA (automatización robótica de procesos) hecho en Python + Playwright, no un bot de trading. "BCE" = Banco Central del Ecuador; "K"/"KORE" = un sistema ERP interno ("KERP", alojado en krugercorp.com). La función del bot, ejecutada a diario: leer la lista de códigos de moneda desde el módulo de cambio de divisas del ERP KORE, consultar la tasa oficial de cada moneda en el portal web público del BCE, y escribir esas tasas de vuelta en la pantalla de cambio de divisas del ERP KORE — reemplazando una tarea manual de digitación.

Este repositorio es una plantilla base (según memoria del proyecto), no el entregable final — probar cambios solo en preproducción.

## Configuración y ejecución

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python change_badge.py
```

No existen comandos de test, lint, build ni CI en este proyecto — ninguno está configurado (no hay pytest, ni configuración de linter/formatter, ni `.github/workflows`).

### Ambiente (Producción vs. Preproducción)

A pesar de lo que indica el README, la selección de ambiente **no** es una variable de entorno. Es la variable local hardcodeada `set_ambient` al inicio de `run_automation()` en `change_badge.py`:

- `set_ambient = 0` → Producción
- `set_ambient = 1` → Preproducción

**Bug conocido a tener en cuenta**: `bce_page.login(page, set_ambient=0)` se llama con un `0` hardcodeado en `change_badge.py`, independiente del valor de `set_ambient` usado para los logins de KORE. Si cambiás el `set_ambient` de nivel superior para correr contra preproducción, la parte de BCE igual apunta a producción a menos que también se actualice ese llamado.

Todos los valores específicos de ambiente (URLs, credenciales, nombre de rol) se consultan en tiempo de ejecución desde los CSV en `data/` usando una columna `Pre` (`0`=Producción, `1`=Preproducción) — no existe otro mecanismo de selección de ambiente.

## Arquitectura

Un orquestador async único, dos page-objects de Playwright, y una capa de configuración en pandas/CSV que hace las veces de base de datos.

```
change_badge.py (punto de entrada; asyncio.run(run_automation()))
   │
   ├── data/data_structure.py  (importado como `ds`) — carga todos los CSV de configuración/datos en DataFrames de pandas a nivel de módulo, al momento de importar
   ├── pages/bce_page.py       — automatización Playwright para el sitio de consulta de tasas del BCE
   ├── pages/kore_page.py      — automatización Playwright para el ERP KORE/KERP
   └── utils/utils.py          — helper save_variable_to_csv(data, cols, filepath) usado por ambos page modules
```

Flujo de ejecución en `change_badge.py`:
1. Lanza Chromium (visible, no headless) — reutiliza el contexto persistente `playwright_profile/` si existe, o si no, un contexto nuevo.
2. `kore_page.login` → `select_rol` → `select_module` (Financiero → Cambio de divisas).
3. `kore_page.select_divisa` extrae la tabla de monedas de KORE → escribe `data/tabla_monedas.csv`.
4. `bce_page.login` → `bce_page.select_badge` itera los códigos de moneda, consulta cada uno en el sitio del BCE (dentro de un iframe, usando un selector de rango de fechas fijado en "hoy" según hora de `America/Guayaquil`) → escribe `data/tasas_fecha {YYYY-MM-DD}.csv`.
5. `importlib.reload(ds)` — necesario porque `data_structure.py` solo lee los CSV al momento de importar el módulo (no hay función de recarga bajo demanda), así que el archivo de tasas recién escrito se recoge re-ejecutando el módulo.
6. `kore_page.login(..., contexto="login_divisa")` navega de vuelta a la pantalla de actualización de KORE.
7. `kore_page.select_divisa_post` hace clic en "Actualizar", cruza el código de moneda de cada fila de KORE contra el `ds.df_tasas_oficiales` recién extraído, completa el campo de tasa, y envía el formulario.
8. Todo el flujo está envuelto en try/except/finally: ante cualquier excepción, imprime `"BOT DETENIDO 💀"` y la vuelve a lanzar; el `finally` siempre cierra el contexto del navegador.

### Capa de datos (`data/data_structure.py`)

Lee de forma anticipada estos CSV en DataFrames al momento de importar (no hay validación de esquema ni auto-creación — CSV de configuración faltantes o mal formados romperán el arranque):

- `kore_data.csv` → `df_data_kore` (credenciales + rol, indexado por `Pre` + `Codigo` en `{'user','pass','rol'}`)
- `kore_URL.csv` → `df_data_URL` (URLs de KORE, indexado por `Pre` + `Contexto`)
- `BCE_data.csv` → `df_data_BCE` (URLs del portal BCE, indexado por `Pre`)
- `tabla_monedas.csv` → `df_tabla_monedas` (generado por el bot; códigos de moneda extraídos de KORE)
- `tasas_fecha {hoy}.csv` → `df_tasas_oficiales` (generado por el bot; envuelto en try/except FileNotFoundError ya que no existirá antes de la primera consulta al BCE en la corrida)

Las variables divididas `df_data_kore_prod`/`_pre` y `df_data_URL_prod`/`_pre` también existen en este módulo pero son código muerto — nada las lee; todas las consultas reales filtran el DataFrame sin dividir por `Pre==set_ambient` directamente.

### Nota sobre secretos

Las credenciales de preproducción están commiteadas en texto plano en `data/kore_data.csv` (login real de KORE). Las filas de producción usan strings placeholder literales (`REEMPLAZAR_...`) que deben completarse manualmente antes de cualquier corrida en producción. Tratar estos CSV como sensibles — no agregar credenciales reales de producción al control de versiones; si esto se lleva a producción, sacar las credenciales de los CSV commiteados.

### Detalles pendientes conocidos (no "arreglar" en silencio — confirmar la intención primero)

- `pages/locators.py` es un placeholder vacío y sin usar.
- Tanto `pages/bce_page.py` como `pages/kore_page.py` importan de `playwright.sync_api` al inicio a pesar de ser completamente async y estar manejados por `async_playwright` — import muerto/sin usar.
- Varios comentarios del código fuente en `kore_page.py` tienen mojibake (ej. `ValidaciÃ³n`) por un desajuste de encoding al guardar el archivo.
- Los CSV están globalmente en `.gitignore` (`*.csv`) pero los CSV de configuración (`kore_data.csv`, `kore_URL.csv`, `BCE_data.csv`) y algunos generados están commiteados de todas formas en este checkout — los CSV de configuración son necesarios para que el bot corra (no existe lógica de bootstrap/creación para ellos).
