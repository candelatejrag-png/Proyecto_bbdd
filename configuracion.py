"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga
    
Fichero de configuracion del proyecto.
Aqui se centralizan:
    - credenciales de MySQL
    - credenciales de MongoDB
    - Nombres de bbdd y colecciones
    - Rutas de los 4 ficheros JSON
    - Parametros generales de carga

"""

# MySQL.
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'pythonista'
MYSQL_DATABASE = 'AmazonReviewsProyecto'
MYSQL_PORT = 3306


# MongoDB.
MONGO_CONNECTION_STRING = 'mongodb://localhost:27017'
MONGO_DATABASE = 'AmazonReviewsProyecto'
MONGO_COLLECTION = 'reviews_raw'


# Rutas de los datasets.
# Rutas de los datasets.
DATASETS = {
    'Toys and Games': '',
    'Video Games': '',
    'Digital Music': '',
    'Musical Instruments': ''
}
# DATASETS = {
#     'Toys and Games': 'C:/Users/ctr72/Documents/bases/proyecto/Toys_and_Games_5.json',
#     'Video Games': 'C:/Users/ctr72/Documents/bases/proyecto/Video_Games_5.json',
#     'Digital Music': 'C:/Users/ctr72/Documents/bases/proyecto/Digital_Music_5.json',
#     'Musical Instruments': 'C:/Users/ctr72/Documents/bases/proyecto/Musical_Instruments_5.json'
# }

# Parametros de carga.
BATCH_SIZE = 1000