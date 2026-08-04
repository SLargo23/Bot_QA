import re
import time
from playwright.async_api import expect
from data import data_structure as ds


async def login(*args, **kwargs):
    # ValidaciÃ³n Visual 1: El dato existe y es correcto
    page = args[0] if len(args) > 0 else kwargs.get('page')
    set_ambient:int = args[1] if len(args) > 1 else kwargs.get('set_ambient')
    contexto:str = args[2] if len(args) > 2 else kwargs.get('contexto')
    usuario:str = args[3] if len(args) > 3 else kwargs.get('usuario')
    #df_data_URL[df_data_URL['Pre']==set_ambient]['URL']
    await page.goto(
        ds.df_data_URL.loc[
            (ds.df_data_URL['Pre']==set_ambient) & (ds.df_data_URL['Contexto']==contexto)
        ]['URL'].values[0],
        wait_until='domcontentloaded'
    )
    await actions_login(page,set_ambient,usuario)


      # Espera a que la pÃ¡gina termine de cargar completamente

#Manejar codigo mediante con try/except para capturar mejor el error, solo poder llegar hasta
#aqui
# Encontrar maneras mas eficientes siguiendo esta estructura
async def actions_login(page,set_ambient,usuario):
        fila_usuario = ds.df_usuarios.loc[
            (ds.df_usuarios['Pre']==set_ambient) & (ds.df_usuarios['Usuario']==usuario)
        ]
        if fila_usuario.empty:
            raise ValueError(
                f"El usuario '{usuario}' no está registrado en data/usuarios_kore.csv para Pre={set_ambient}"
            )
        password = fila_usuario['Password'].values[0]

        await page.get_by_role("textbox", name="Usuario o email").click()
        await page.get_by_role("textbox", name="Usuario o email").fill(usuario)
        await page.get_by_role("textbox", name="Contraseña").click()
        await page.get_by_role("textbox", name="Contraseña").fill(password)
        await page.get_by_role("button", name="Iniciar sesión").click()

        # Confirma que el login navegó a la pantalla post-login (aparece el selector de rol)
        await expect(page.locator("span.icon-down-arrow.ml-2.text-xs")).to_be_visible(timeout=15000)

async def select_rol(page, set_ambient, usuario, rol):

    roles_usuario = ds.df_usuario_roles.loc[
        (ds.df_usuario_roles['Pre']==set_ambient) & (ds.df_usuario_roles['Usuario']==usuario)
    ]['Rol'].values
    if rol not in roles_usuario:
        raise ValueError(
            f"El usuario '{usuario}' no tiene asignado el rol '{rol}' "
            f"(ver data/usuario_roles.csv). Roles asignados: {list(roles_usuario)}"
        )

    await seleccionar_rol_ui(page, rol)


async def seleccionar_rol_ui(page, rol):
    """Selecciona un rol en el dropdown sin validar contra usuario_roles.csv.

    Usado por herramientas de descubrimiento (verificar_roles.py) que ya
    obtuvieron la lista de roles directamente de la UI vía listar_roles_ui.
    """
    await page.locator("span.icon-down-arrow.ml-2.text-xs").click()
    await page.locator(".css-1wy0on6").click()

    opcion_rol = page.get_by_role("option", name=rol, exact=True)
    await expect(opcion_rol).to_be_visible(timeout=10000)
    await opcion_rol.click()

    # Confirma que el dropdown se cerró tras aplicar la selección
    await expect(opcion_rol).not_to_be_visible(timeout=10000)


async def listar_roles_ui(page):
    await page.locator("span.icon-down-arrow.ml-2.text-xs").click()
    await page.locator(".css-1wy0on6").click()

    opciones = page.get_by_role("option")
    await expect(opciones.first).to_be_visible(timeout=10000)
    textos = await opciones.all_text_contents()

    await page.keyboard.press("Escape")
    await expect(opciones.first).not_to_be_visible(timeout=10000)

    return [t.strip() for t in textos if t.strip()]


async def listar_modulos_menu(page, timeout=15000):
    """Lista los módulos visibles en el menú lateral para el rol activo actualmente.

    El menú lateral (react-pro-sidebar) usa el contenedor estable
    'aside.ps-sidebar-root' sin importar el rol seleccionado, así que no
    depende de conocer de antemano ningún texto de menú específico del rol.
    """
    sidebar = page.locator("aside.ps-sidebar-root")
    await expect(sidebar).to_be_visible(timeout=timeout)
    await expect(sidebar.locator("a").first).to_be_attached(timeout=timeout)

    textos = await sidebar.locator("a").all_text_contents()
    return [t.strip() for t in textos if t.strip()]


async def esperar_menu_rol(page, rol, timeout=30000):
    fila_rol = ds.df_roles_kore.loc[ds.df_roles_kore['Rol']==rol]
    if fila_rol.empty:
        raise ValueError(f"El rol '{rol}' no está en el catálogo data/roles_kore.csv")

    item_menu_texto = fila_rol['ItemMenu'].values[0]
    if item_menu_texto == 'REEMPLAZAR_ITEM_MENU':
        raise ValueError(
            f"Falta completar el ítem de menú del rol '{rol}' en data/roles_kore.csv"
        )

    item_menu = page.locator("a").filter(has_text=item_menu_texto)
    await expect(item_menu).to_be_visible(timeout=timeout)
    return item_menu
