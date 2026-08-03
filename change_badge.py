import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Ensure the project root is on sys.path so sibling packages can be imported
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pages import kore_page
from playwright.async_api import async_playwright


async def run_automation():

    profile_dir = Path(__file__).resolve().parent / "playwright_profile"
    browser = None
    context = None

    async with async_playwright() as p:

        if profile_dir.exists():
            print(f"Usando perfil persistente de Playwright: {profile_dir}")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

        set_ambient: int = 1  # 0 = PROD | 1 = PRE
        usuario: str = "cmoncayo@ec.krugercorp.com"
        rol: str = "Analista de Talento Humano"

        try:

            print("===== INICIO BOT =====")

            # ==========================================
            # LOGIN KORE
            # ==========================================

            print("Login KORE...")

            await kore_page.login(
                page,
                set_ambient=set_ambient,
                contexto="login_home",
                usuario=usuario
            )

            await kore_page.select_rol(
                page,
                set_ambient=set_ambient,
                usuario=usuario,
                rol=rol
            )

            print("Esperando menú del rol...")

            await kore_page.esperar_menu_rol(
                page,
                rol=rol,
                timeout=30000
            )

            print("Menú del rol visible. Deteniendo el bot.")
            print("===== BOT FINALIZADO OK =====")

        except Exception as ex:

            print(f"\nBOT DETENIDO 💀")
            print(f"ERROR: {type(ex).__name__}")
            print(f"DETALLE: {ex}")

            raise

        finally:

            print("Cerrando navegador...")

            if context:
                try:
                    await context.close()
                except Exception as ex:
                    print(f"Advertencia al cerrar el contexto: {ex}")
            if browser:
                try:
                    await browser.close()
                except Exception as ex:
                    print(f"Advertencia al cerrar el browser: {ex}")


if __name__ == "__main__":
    asyncio.run(run_automation())