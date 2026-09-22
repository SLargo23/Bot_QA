import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, expect

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data import data_structure as ds
from pages import kore_page

load_dotenv()

AMBIENTE = 1
ESPERA_MODULO_MS = 4000
TIMEOUT_MS = 8000


async def buscar_enlace_visible(sidebar, modulo):
    enlaces = sidebar.locator("a").filter(has_text=modulo)
    for indice in range(await enlaces.count()):
        enlace = enlaces.nth(indice)
        if await enlace.is_visible():
            return enlace
    return None


async def probar_modulo(page, context, app_url, rol, modulo):
    """Selecciona el rol, abre un modulo y espera para observar la pagina."""
    try:
        # Algunos módulos cambian el estado o la ruta del menú. Volver a la
        # raíz reconstruye el menú del rol antes de probar la siguiente opción.
        await page.goto(app_url, wait_until="domcontentloaded")
        await expect(
            page.locator("span.icon-down-arrow.ml-2.text-xs")
        ).to_be_visible(timeout=TIMEOUT_MS)
        await kore_page.seleccionar_rol_ui(page, rol)
        sidebar = page.locator("aside.ps-sidebar-root")
        enlace = await buscar_enlace_visible(sidebar, modulo)
        if enlace is None:
            return False, "La opción no está visible después de reconstruir el menú"

        target = await enlace.get_attribute("target")
        if target == "_blank":
            async with context.expect_page(timeout=TIMEOUT_MS) as page_info:
                await enlace.click(timeout=TIMEOUT_MS)
            pagina_modulo = await page_info.value
            await pagina_modulo.wait_for_timeout(ESPERA_MODULO_MS)
            await expect(pagina_modulo.locator("body")).to_be_visible(timeout=1000)
            url = pagina_modulo.url
            await pagina_modulo.close()
        else:
            await enlace.click(timeout=TIMEOUT_MS)
            await page.wait_for_timeout(ESPERA_MODULO_MS)
            await expect(page.locator("body")).to_be_visible(timeout=1000)
            url = page.url

        return True, url
    except Exception as ex:
        try:
            await page.wait_for_timeout(ESPERA_MODULO_MS)
        except Exception:
            pass
        return False, f"{type(ex).__name__}: {ex}"


async def explorar_usuario(playwright, usuario):
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print(f"\n--- Usuario: {usuario} (Pre={AMBIENTE}) ---")
        await kore_page.login(
            page,
            set_ambient=AMBIENTE,
            contexto="login_home",
            usuario=usuario,
        )

        roles = await kore_page.listar_roles_ui(page)
        print(f"Roles disponibles ({len(roles)}): {roles}")
        app_url = page.url

        for rol in roles:
            print(f"\nROL: {rol}")
            try:
                await kore_page.seleccionar_rol_ui(page, rol)
                modulos = await kore_page.listar_modulos_menu(
                    page,
                    timeout=TIMEOUT_MS,
                )
                print(f"Módulos visibles ({len(modulos)}): {modulos}")
            except Exception as ex:
                print(f"[ERROR ROL] {type(ex).__name__}: {ex}")
                continue

            for modulo in modulos:
                ok, detalle = await probar_modulo(
                    page,
                    context,
                    app_url,
                    rol,
                    modulo,
                )
                estado = "OK" if ok else "ERROR"
                print(f"  [{estado}] {modulo} -> {detalle}")

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


async def main():
    usuarios = ds.df_usuarios.loc[
        ds.df_usuarios["Pre"] == AMBIENTE, "Usuario"
    ].tolist()
    if not usuarios:
        raise ValueError(
            f"No hay usuarios configurados para Pre={AMBIENTE} en "
            "data/usuarios_kore.csv"
        )

    print("===== INICIO EXPLORACIÓN DINÁMICA KORE =====")
    async with async_playwright() as playwright:
        for usuario in usuarios:
            await explorar_usuario(playwright, usuario)
    print("===== FIN EXPLORACIÓN DINÁMICA KORE =====")


if __name__ == "__main__":
    asyncio.run(main())
