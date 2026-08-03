import pandas as pd

#En este archivo se realizan los dataframes, recopilando datos de entrada, replicar el contexto de automatizacion de pruebas
#Si se hace un despliegue, hacer la prueba de login, verificando que el sistema esta habilitado
#Recopilando credenciales

#Construir el dataframe con pandas
#Recibe la ruta del archivo, manteniendo la estructura, mantener en la misma carpeta data csv y py, para evitar confusion.
#A la variable, darle todo el valor del archivo

# Read CSV file
df_data_kore= pd.read_csv('data/kore_data.csv', sep=',')

df_data_kore_prod = df_data_kore[df_data_kore['Pre'] == 0]

df_data_kore_pre=df_data_kore[df_data_kore['Pre']==1]


df_data_URL= pd.read_csv('data/kore_URL.csv', sep=',')

df_data_URL_prod = df_data_URL[df_data_URL['Pre'] == 0]
df_data_URL_pre=df_data_URL[df_data_URL['Pre']==1]


df_tabla_monedas = pd.read_csv('data/tabla_monedas.csv', sep=',')




