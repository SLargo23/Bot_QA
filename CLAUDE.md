# CLAUDE.md

Este archivo brinda orientación a Claude Code (claude.ai/code) al trabajar con código en este repositorio.

## Qué es esto

Un bot de RPA (automatización robótica de procesos) hecho en Python + Playwright que automatiza pruebas del ERP KORE interno ("KERP", alojado en krugercorp.com). El proyecto pivotó desde un objetivo original distinto hacia la automatización de pruebas de **login, selección de rol, y navegación del menú de módulos** en KORE — ver `RESUMEN_IMPLEMENTACION_LOGIN_ROL.md` para el detalle de ese pivote.

La función actual del bot: iniciar sesión en KORE con un usuario registrado, seleccionar uno de sus roles asignados, y confirmar que el menú lateral de módulos correspondiente a ese rol carga correctamente — reemplazando una verificación manual repetitiva.

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

Todos los valores específicos de ambiente (URLs, credenciales, nombre de rol) se consultan en tiempo de ejecución desde los CSV en `data/` usando una columna `Pre` (`0`=Producción, `1`=Preproducción) — no existe otro mecanismo de selección de ambiente.

## Arquitectura

Un orquestador async único, un page-object de Playwright, y una capa de configuración en pandas/CSV que hace las veces de base de datos.

```
change_badge.py (punto de entrada; asyncio.run(run_automation()))
   │
   ├── data/data_structure.py  (importado como `ds`) — carga todos los CSV de configuración/datos en DataFrames de pandas a nivel de módulo, al momento de importar
   ├── pages/kore_page.py      — automatización Playwright para el ERP KORE/KERP (login, selección de rol, listado de roles y de módulos del menú)
   └── utils/utils.py          — helper save_variable_to_csv(data, cols, filepath); actualmente sin usar en el flujo activo
```

Flujo de ejecución en `change_badge.py` (`run_automation`):
1. Lanza Chromium (visible, no headless) — reutiliza el contexto persistente `playwright_profile/` si existe, o si no, un contexto nuevo.
2. `kore_page.login(page, set_ambient, contexto="login_home", usuario)` navega a la URL de login y completa el formulario con las credenciales del usuario indicado (leídas de `data/usuarios_kore.csv`).
3. `kore_page.select_rol(page, set_ambient, usuario, rol)` valida que el rol pedido esté asignado a ese usuario en `data/usuario_roles.csv`, abre el dropdown de rol y lo selecciona.
4. `kore_page.esperar_menu_rol(page, rol, timeout)` confirma que el ítem de menú asociado a ese rol (según `data/roles_kore.csv`) quedó visible.
5. Todo el flujo está envuelto en try/except/finally: ante cualquier excepción, imprime `"BOT DETENIDO 💀"` y la vuelve a lanzar; el `finally` siempre cierra el contexto del navegador.

### `verificar_roles.py`

Script adicional (no es el punto de entrada principal) para descubrimiento/QA: recorre todos los usuarios de preproducción en `data/usuarios_kore.csv`, hace login con cada uno, y usa `kore_page.listar_roles_ui` para leer directamente del dropdown los roles realmente disponibles para ese usuario (sin depender de que `usuario_roles.csv` esté actualizado). Útil para detectar CSV desactualizados frente a la UI real de KORE.

### Capa de datos (`data/data_structure.py`)

Lee de forma anticipada estos CSV en DataFrames al momento de importar (no hay validación de esquema ni auto-creación — CSV de configuración faltantes o mal formados romperán el arranque):

- `usuarios_kore.csv` → `df_usuarios` (credenciales por usuario registrado, indexado por `Pre` + `Usuario`)
- `usuario_roles.csv` → `df_usuario_roles` (qué roles tiene asignados cada usuario; una fila por combinación `Pre` + `Usuario` + `Rol`, así un usuario con varios roles ocupa varias filas)
- `roles_kore.csv` → `df_roles_kore` (catálogo completo de roles de KORE, indexado por `Rol`, con el `ItemMenu` — texto de un ítem de menú que confirma que se navegó a ese rol; roles sin ese dato confirmado usan el placeholder `REEMPLAZAR_ITEM_MENU`)
- `kore_URL.csv` → `df_data_URL` (URLs de KORE, indexado por `Pre` + `Contexto`; hoy solo existe el contexto `login_home`)

`kore_page.select_rol(page, set_ambient, usuario, rol)` valida contra `df_usuario_roles` que el `rol` pedido esté realmente asignado a ese `usuario` antes de tocar la UI (levanta `ValueError` si no). `kore_page.esperar_menu_rol(page, rol, timeout)` resuelve el ítem de menú a esperar consultando `df_roles_kore` — el mapeo rol→ítem de menú vive en un solo lugar, no se repite por usuario ni se hardcodea en `change_badge.py`.

La variable dividida `df_data_URL_prod`/`_pre` también existe en este módulo pero es código muerto — nada la lee; todas las consultas reales filtran el DataFrame sin dividir por `Pre==set_ambient` directamente.

### Nota sobre secretos

Las credenciales de preproducción están en texto plano en `data/usuarios_kore.csv` (logins reales de KORE, uno por usuario registrado). Las filas de producción usan strings placeholder literales (`REEMPLAZAR_...`) que deben completarse manualmente antes de cualquier corrida en producción. Tratar estos CSV como sensibles — no agregar credenciales reales de producción al control de versiones; si esto se lleva a producción, sacar las credenciales de los CSV commiteados.

### Detalles pendientes conocidos (no "arreglar" en silencio — confirmar la intención primero)

- `pages/locators.py` es un placeholder vacío y sin usar.
- Varios comentarios del código fuente en `kore_page.py` tienen mojibake (ej. `ValidaciÃ³n`) por un desajuste de encoding al guardar el archivo.
- Los CSV están globalmente en `.gitignore` (`*.csv`). En este checkout, ninguno está realmente trackeado en git (`git ls-files` no los lista) — todos, incluyendo `usuarios_kore.csv`, `usuario_roles.csv`, `roles_kore.csv` y `kore_URL.csv`, son necesarios para que el bot corra pero solo existen en disco local; habría que `git add -f` cada uno si se quieren versionar.
- `utils/utils.py` (`save_variable_to_csv`) no tiene ningún llamador activo en el código actual.
