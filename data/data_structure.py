import pandas as pd

#En este archivo se realizan los dataframes, recopilando datos de entrada, replicar el contexto de automatizacion de pruebas
#Si se hace un despliegue, hacer la prueba de login, verificando que el sistema esta habilitado
#Recopilando credenciales

#Construir el dataframe con pandas
#Recibe la ruta del archivo, manteniendo la estructura, mantener en la misma carpeta data csv y py, para evitar confusion.
#A la variable, darle todo el valor del archivo

# Read CSV file
df_usuarios = pd.read_csv('data/usuarios_kore.csv', sep=',')

df_usuario_roles = pd.read_csv('data/usuario_roles.csv', sep=',')

df_roles_kore = pd.read_csv('data/roles_kore.csv', sep=',')


df_data_URL= pd.read_csv('data/kore_URL.csv', sep=',')

df_data_URL_prod = df_data_URL[df_data_URL['Pre'] == 0]
df_data_URL_pre=df_data_URL[df_data_URL['Pre']==1]







