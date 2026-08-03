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

- `usuarios_kore.csv` → `df_usuarios` (credenciales por usuario registrado, indexado por `Pre` + `Usuario`)
- `usuario_roles.csv` → `df_usuario_roles` (qué roles tiene asignados cada usuario; una fila por combinación `Pre` + `Usuario` + `Rol`, así un usuario con varios roles ocupa varias filas)
- `roles_kore.csv` → `df_roles_kore` (catálogo completo de roles de KORE, indexado por `Rol`, con el `ItemMenu` — texto del ítem de menú lateral que confirma que se navegó a ese rol; roles sin ese dato confirmado usan el placeholder `REEMPLAZAR_ITEM_MENU`)
- `kore_URL.csv` → `df_data_URL` (URLs de KORE, indexado por `Pre` + `Contexto`)

`kore_page.select_rol(page, set_ambient, usuario, rol)` valida contra `df_usuario_roles` que el `rol` pedido esté realmente asignado a ese `usuario` antes de tocar la UI (levanta `ValueError` si no). `kore_page.esperar_menu_rol(page, rol, timeout)` resuelve el ítem de menú a esperar consultando `df_roles_kore` — el mapeo rol→ítem de menú vive en un solo lugar, no se repite por usuario ni se hardcodea en `change_badge.py`.

La variable dividida `df_data_URL_prod`/`_pre` también existe en este módulo pero es código muerto — nada la lee; todas las consultas reales filtran el DataFrame sin dividir por `Pre==set_ambient` directamente.

### Nota sobre secretos

Las credenciales de preproducción están en texto plano en `data/usuarios_kore.csv` (logins reales de KORE, uno por usuario registrado). Las filas de producción usan strings placeholder literales (`REEMPLAZAR_...`) que deben completarse manualmente antes de cualquier corrida en producción. Tratar estos CSV como sensibles — no agregar credenciales reales de producción al control de versiones; si esto se lleva a producción, sacar las credenciales de los CSV commiteados.

### Detalles pendientes conocidos (no "arreglar" en silencio — confirmar la intención primero)

- `pages/locators.py` es un placeholder vacío y sin usar.
- Varios comentarios del código fuente en `kore_page.py` tienen mojibake (ej. `ValidaciÃ³n`) por un desajuste de encoding al guardar el archivo.
- Los CSV están globalmente en `.gitignore` (`*.csv`). En este checkout, ninguno está realmente trackeado en git (`git ls-files` no los lista — verificado; la afirmación anterior de que "los CSV de configuración están commiteados de todas formas" no es cierta en este repo) — todos, incluyendo `usuarios_kore.csv`, `usuario_roles.csv`, `roles_kore.csv` y `kore_URL.csv`, son necesarios para que el bot corra pero solo existen en disco local; habría que `git add -f` cada uno si se quieren versionar.
- `data/data_structure.py` documenta en su código un flujo BCE (URLs, tasas oficiales) y una tabla de monedas que ya no se generan ni se leen en el flujo actual — son restos del pivote hacia pruebas de login+rol (ver `RESUMEN_IMPLEMENTACION_LOGIN_ROL.md`). La sección "Arquitectura" de este archivo, más abajo, todavía describe ese flujo BCE completo (`pages/bce_page.py`) como si estuviera activo — ese archivo ya no existe en el repo; esa sección está desactualizada y no se tocó como parte de esta implementación.
