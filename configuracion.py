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
MYSQL_PASSWORD = ''
MYSQL_DATABASE = 'AmazonReviewsProyecto'
MYSQL_PORT = 3306


# MongoDB.
MONGO_CONNECTION_STRING = 'mongodb://localhost:27017'
MONGO_DATABASE = 'AmazonReviewsProyecto'
MONGO_COLLECTION = 'reviews_raw'

# Neo4J
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_PASSWORD = ''


# Rutas de los datasets.
# Rutas de los datasets.
DATASETS = {
    'Toys and Games': 'Toys_and_Games_5.json',
    'Video Games': 'Video_Games_5.json',
    'Digital Music': 'Digital_Music_5.json',
    'Musical Instruments': 'Musical_Instruments_5.json'
}
# DATASETS = {
#     'Toys and Games': 'C:/Users/ctr72/Documents/bases/proyecto/Toys_and_Games_5.json',
#     'Video Games': 'C:/Users/ctr72/Documents/bases/proyecto/Video_Games_5.json',
#     'Digital Music': 'C:/Users/ctr72/Documents/bases/proyecto/Digital_Music_5.json',
#     'Musical Instruments': 'C:/Users/ctr72/Documents/bases/proyecto/Musical_Instruments_5.json'
# }

# Parametros de carga.
BATCH_SIZE = 1000


# Exportacion para visualizaciones externas.
EXPORTS_DIR = 'exports_visualizacion'
TP_N_POPULARIDAD_EXPORT = 1000