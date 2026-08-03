import re
import time
from playwright.async_api import expect
from data import data_structure as ds


async def login(*args, **kwargs):
    # ValidaciÃ³n Visual 1: El dato existe y es correcto
    page = args[0] if len(args) > 0 else kwargs.get('page')
    set_ambient:int = args[1] if len(args) > 1 else kwargs.get('set_ambient')
    contexto:str = args[2] if len(args) > 2 else kwargs.get('contexto')
    #df_data_URL[df_data_URL['Pre']==set_ambient]['URL']
    await page.goto(
        ds.df_data_URL.loc[
            (ds.df_data_URL['Pre']==set_ambient) & (ds.df_data_URL['Contexto']==contexto)
        ]['URL'].values[0],
        wait_until='domcontentloaded'
    )
    await page.wait_for_load_state('networkidle')
    await actions_login(page,set_ambient)
    

      # Espera a que la pÃ¡gina termine de cargar completamente    

#Manejar codigo mediante con try/except para capturar mejor el error, solo poder llegar hasta
#aqui
# Encontrar maneras mas eficientes siguiendo esta estructura
async def actions_login(page,set_ambient):
        await page.get_by_role("textbox", name="Usuario o email").click()
        await page.get_by_role("textbox", name="Usuario o email").fill(
          ds.df_data_kore.loc
          [(ds.df_data_kore['Pre']==set_ambient) &
          (ds.df_data_kore['Codigo']=='user')]['Contexto'].values[0]
           )
        await page.get_by_role("textbox", name="Contraseña").click()
        await page.get_by_role("textbox", name="Contraseña").fill(
          ds.df_data_kore.loc[(ds.df_data_kore['Pre']==set_ambient)&
                          (ds.df_data_kore['Codigo']=='pass')]['Contexto'].values[0]
                          )
        await page.get_by_role("button", name="Iniciar sesión").click()
        await page.wait_for_load_state('networkidle')

        # Confirma que el login navegó a la pantalla post-login (aparece el selector de rol)
        await expect(page.locator("span.icon-down-arrow.ml-2.text-xs")).to_be_visible(timeout=10000)

async def select_rol(page, set_ambient, rol=None):

    nombre_rol = rol if rol is not None else ds.df_data_kore.loc[
        (ds.df_data_kore['Pre']==set_ambient) & (ds.df_data_kore['Codigo']=='rol')
    ]['Contexto'].values[0]

    await page.locator("span.icon-down-arrow.ml-2.text-xs").click()
    await page.locator(".css-1wy0on6").click()

    opcion_rol = page.get_by_role("option", name=nombre_rol, exact=True)
    await expect(opcion_rol).to_be_visible(timeout=10000)
    await opcion_rol.click()

    # Confirma que el dropdown se cerró tras aplicar la selección
    await expect(opcion_rol).not_to_be_visible(timeout=10000)
