import asyncio
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

# Ensure the project root is on sys.path so sibling packages can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pages import kore_page
from data import data_structure as ds
from playwright.async_api import async_playwright, expect

USUARIO_ROLES_CSV = PROJECT_ROOT / "data" / "usuario_roles.csv"
ROLES_KORE_CSV = PROJECT_ROOT / "data" / "roles_kore.csv"
ROLES_EXCEL_XLSX = PROJECT_ROOT / "data" / "Roles x parametros (1).xlsx"


def cargar_roles_excel():
    """Carga el catálogo de roles esperado desde la hoja de convenciones."""
    df_roles = pd.read_excel(
        ROLES_EXCEL_XLSX,
        sheet_name="Convensión roles",
        usecols=["Cargo / Rol", "Código"]
    ).dropna(subset=["Cargo / Rol"])
    df_roles["Cargo / Rol"] = df_roles["Cargo / Rol"].astype(str).str.strip()
    return set(df_roles["Cargo / Rol"])


async def verificar_usuario(playwright, set_ambient, usuario, roles_excel):
    """Login con `usuario`, descubre sus roles reales en la UI y navega el
    menú de módulos de cada uno. Devuelve {rol: [modulos] | None} (None = error)."""

    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    resultado = {}

    try:
        print(f"\n--- Usuario: {usuario} (Pre={set_ambient}) ---")

        await kore_page.login(
            page,
            set_ambient=set_ambient,
            contexto="login_home",
            usuario=usuario
        )

        roles = await kore_page.listar_roles_ui(page)
        print(f"Roles disponibles ({len(roles)}): {roles}")

        roles_disponibles = set(roles)
        roles_catalogados = sorted(roles_disponibles & roles_excel)
        roles_no_catalogados = sorted(roles_disponibles - roles_excel)
        roles_no_disponibles = sorted(roles_excel - roles_disponibles)
        print(f"Roles disponibles y catalogados en Excel ({len(roles_catalogados)}): "
              f"{roles_catalogados}")
        print(f"Roles disponibles que no están en Excel ({len(roles_no_catalogados)}): "
              f"{roles_no_catalogados}")
        print(f"Roles del Excel no asignados a este usuario ({len(roles_no_disponibles)}): "
              f"{roles_no_disponibles}")

        # Se registran de entrada como roles válidos (ya confirmados por la UI),
        # así un fallo posterior al navegar el menú de alguno no borra los demás.
        resultado.update({rol: None for rol in roles})

        for rol in roles:
            ultimo_error = None
            for intento in range(2):
                try:
                    await kore_page.seleccionar_rol_ui(page, rol)
                    modulos = await kore_page.listar_modulos_menu(page)
                    resultado[rol] = modulos
                    print(f"  ✔ {rol} -> {len(modulos)} módulos: {modulos}")
                    resultados_modulos = await kore_page.probar_modulos_menu(page, rol)
                    for resultado_modulo in resultados_modulos:
                        estado = "OK" if resultado_modulo["ok"] else "ERROR"
                        detalle = resultado_modulo["url"] or resultado_modulo["error"]
                        print(
                            f"    [{estado}] {resultado_modulo['modulo']} -> {detalle}"
                        )
                    break
                except Exception as ex:
                    ultimo_error = ex
                    await page.wait_for_timeout(1500)
            else:
                resultado[rol] = None
                print(f"  ✗ {rol} -> ERROR: {type(ultimo_error).__name__}: {ultimo_error}")

    except Exception as ex:
        print(f"ERROR verificando '{usuario}': {type(ex).__name__}: {ex}")

    finally:
        try:
            if not context.is_closed():
                await context.close()
        except Exception as ex:
            print(f"Advertencia al cerrar el contexto: {type(ex).__name__}: {ex}")
        try:
            if browser.is_connected():
                await browser.close()
        except Exception as ex:
            print(f"Advertencia al cerrar el navegador: {type(ex).__name__}: {ex}")

    return resultado


def actualizar_csvs(set_ambient, resultados_por_usuario):
    """Sobrescribe usuario_roles.csv (para Pre=set_ambient) y roles_kore.csv
    con lo efectivamente observado en la UI durante esta corrida."""

    # --- usuario_roles.csv ---
    df_roles_actual = pd.read_csv(USUARIO_ROLES_CSV, sep=',')
    df_sin_ambiente = df_roles_actual.loc[df_roles_actual['Pre'] != set_ambient]

    filas_nuevas = [
        {'Pre': set_ambient, 'Usuario': usuario, 'Rol': rol}
        for usuario, roles in resultados_por_usuario.items()
        for rol in roles.keys()
    ]
    df_ambiente_nuevo = pd.DataFrame(filas_nuevas, columns=['Pre', 'Usuario', 'Rol'])

    df_final = pd.concat([df_sin_ambiente, df_ambiente_nuevo], ignore_index=True)
    df_final.to_csv(USUARIO_ROLES_CSV, index=False, encoding='utf-8')
    print(f"\nActualizado {USUARIO_ROLES_CSV} ({len(df_ambiente_nuevo)} filas para Pre={set_ambient}).")

    # --- roles_kore.csv ---
    df_catalogo = pd.read_csv(ROLES_KORE_CSV, sep=',')
    catalogo = dict(zip(df_catalogo['Rol'], df_catalogo['ItemMenu']))

    for roles in resultados_por_usuario.values():
        for rol, modulos in roles.items():
            item_actual = catalogo.get(rol)
            necesita_item = item_actual is None or item_actual == 'REEMPLAZAR_ITEM_MENU'
            if necesita_item and modulos:
                catalogo[rol] = modulos[0]
            elif rol not in catalogo:
                catalogo[rol] = 'REEMPLAZAR_ITEM_MENU'

    df_catalogo_final = pd.DataFrame(
        {'Rol': list(catalogo.keys()), 'ItemMenu': list(catalogo.values())}
    )
    df_catalogo_final.to_csv(ROLES_KORE_CSV, index=False, encoding='utf-8')
    print(f"Actualizado {ROLES_KORE_CSV} ({len(df_catalogo_final)} roles en catálogo).")


async def run():
    set_ambient = 1  # Solo preproducción: las credenciales de producción son placeholders
    roles_excel = cargar_roles_excel()

    usuarios_pre = ds.df_usuarios.loc[ds.df_usuarios['Pre'] == set_ambient]['Usuario'].tolist()

    print(f"===== INICIO VERIFICACIÓN DE ROLES Y MENÚS (Pre={set_ambient}) =====")
    print(f"Roles definidos en Excel: {len(roles_excel)}")
    print(f"Usuarios a verificar: {usuarios_pre}")

    resultados_por_usuario = {}

    async with async_playwright() as p:
        for usuario in usuarios_pre:
            resultados_por_usuario[usuario] = await verificar_usuario(
                p,
                set_ambient=set_ambient,
                usuario=usuario,
                roles_excel=roles_excel
            )

    actualizar_csvs(set_ambient, resultados_por_usuario)

    print("\n===== FIN VERIFICACIÓN DE ROLES Y MENÚS =====")


if __name__ == "__main__":
    asyncio.run(run())
