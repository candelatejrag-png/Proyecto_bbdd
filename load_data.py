"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

En este fichero:
    1. Creamos la bbdd de MySQL si no existe
    2. Creamos las tablas relacionales del proyecto
    3. Creamos/limpiamos la coleccion de MongoDB
    4. Leemos los 4 ficheros json lineal a linea
    5. Insertamos la informacion estructurada en MySQL
    6. Insertamos la review original en MongoDB

"""
# Importamos las librerías necesarias
import json
from datetime import datetime

import pymysql
from pymongo import MongoClient
from pymongo.database import Database
from pymysql.connections import Connection

# Importamos las variables de otros módulos necesarias
from configuracion import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MONGO_CONNECTION_STRING,
    MONGO_DATABASE,
    MONGO_COLLECTION,
    DATASETS,
    BATCH_SIZE
)

# Conexiones.
def get_mysql_connection(database_name:str=None) -> Connection:     # El =None nos permite no pasarle nombre mas tarde en la funcion de crear_bbdd_mysql(), para conectarnos sin pasar ninguna base.
    """
    Crea y devuelve una conexion a MySQL.
    """
    if database_name is not None:
        return pymysql.connect(
                        host = MYSQL_HOST,
                        user = MYSQL_USER,
                        password = MYSQL_PASSWORD,
                        port = MYSQL_PORT,
                        database = database_name
                    )
    # En vez de usar USE Reviews, conecto a la base de datos concreta (arriba).
    return pymysql.connect(
                        host = MYSQL_HOST,
                        user = MYSQL_USER,
                        port = MYSQL_PORT,
                        password = MYSQL_PASSWORD
                    )

def get_mongo_database(database_name:str) -> Database:
    """
    Devuelve la base de datos de MongoDB.
    """
    client = MongoClient(MONGO_CONNECTION_STRING)
    return client[database_name]


# Limpieza y transformacion de los datos.
def limpieza_basica(s:str):
    """
    Limpieza basica de cadenas.
    """
    if s is None:
        return ''
    return str(s).strip()

def formateo_review_time(review_time:str):
    """
    Convierte reviewTime del formato:
    '07 9, 2012'
    a un objeto date de Python.
    Devuelve None si no se puede convertir.
    """
    review_time = limpieza_basica(review_time)
    if not review_time:
        return None
    
    try:
        fecha_dt = datetime.strptime(review_time, '%m %d, %Y')
        return fecha_dt.date()
    except ValueError:
        return None
    
def extraccion_helpful(review:dict):
    """
    Extrae los dos enteros del campo helpful [x, y].
    Devuelve:
    (helpful_yes, helpful_total)
    """
    helpful = review.get('helpful', None)

    if not isinstance(helpful, list):
        return None, None
    
    helpful_yes = helpful[0] if len(helpful) > 0 else None
    helpful_total = helpful[1] if len(helpful) > 1 else None

    return helpful_yes, helpful_total

def construccion_review_uid(product_type_name:str, reviewer_id_original:str, asin:str, unix_review_time):
    """
    Construimos un identificador para cada review.
    Va a ser UNICO.
    Asi podremos enlazar la misma review entre MySQL y MongoDB.
    """
    unix_part = '' if unix_review_time is None else str(unix_review_time)       # Por si devolviera un error la conversion a fecha.
    
    return f'{product_type_name}|{reviewer_id_original}|{asin}|{unix_part}'


# MySQL: creacion de base de datos y tablas.
def crear_bbdd_mysql() -> None:
    """
    Crea la base de datos de MySQL si no existe.
    """
    print('MySQL -> Creando base de datos...')
    conexion = get_mysql_connection()

    try:
        with conexion.cursor() as cursor:
            sql = f'CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE}'
            cursor.execute(sql)
        conexion.commit()
    finally:
        conexion.close()

def borrar_tablas_mysql() -> None:
    """
    Borra las tablas.
    """
    print('MySQL -> Borrando tablas anteriores si existen...')
    conexion = get_mysql_connection(MYSQL_DATABASE)

    drop_tables = [
        'DROP TABLE IF EXISTS reviews;',
        'DROP TABLE IF EXISTS products;',
        'DROP TABLE IF EXISTS user_names;',
        'DROP TABLE IF EXISTS users;',
        'DROP TABLE IF EXISTS product_types;'
    ]

    try:
        with conexion.cursor() as cursor:
            for sentencia in drop_tables:
                cursor.execute(sentencia)
        conexion.commit()
    finally:
        conexion.close()

def crear_tablas_mysql() -> None:
    """
    Creamos las tablas relacionales.
    """
    print('MySQL -> Creando tablas...')
    conexion = get_mysql_connection(MYSQL_DATABASE)

    create_product_types = """
                    CREATE TABLE product_types (
                        id_product_type INT NOT NULL AUTO_INCREMENT,
                        product_type_name VARCHAR(100) NOT NULL,
                        source_file_path VARCHAR(255) NOT NULL,
                        PRIMARY KEY (id_product_type),
                        UNIQUE KEY uq_product_types_name (product_type_name)
                    );
                    """
    # Nota de autoria: para hacer nuestro programa mas robusto, 
    #                  usamos UNIQUE KEY para poder identificar 
    #                  el error facilmente si insertamos un duplicado.
    
    create_users = """
            CREATE TABLE users (
                id_user INT NOT NULL AUTO_INCREMENT,
                reviewer_id_original VARCHAR(40) NOT NULL,
                PRIMARY KEY (id_user),
                UNIQUE KEY uq_users_reviewer_id_original (reviewer_id_original)
            );
            """
    
    create_user_names = """
            CREATE TABLE user_names (
                id_user_name INT NOT NULL AUTO_INCREMENT,
                id_user INT NOT NULL,
                reviewer_name VARCHAR(255) NOT NULL,
                PRIMARY KEY (id_user_name),
                UNIQUE KEY uq_user_name_user_name (id_user, reviewer_name),
                FOREIGN KEY (id_user) REFERENCES users(id_user)
            );
            """
    
    create_products = """
            CREATE TABLE products (
                id_product INT NOT NULL AUTO_INCREMENT,
                asin VARCHAR(30) NOT NULL,
                id_product_type INT NOT NULL,
                PRIMARY KEY (id_product),
                UNIQUE KEY uq_products_asin_type (asin, id_product_type),
                KEY idx_products_type (id_product_type),
                FOREIGN KEY (id_product_type) REFERENCES product_types(id_product_type)
            );
            """
            # KEY es un indice normal. Lo añadimos para que las consultas luego 
            # en visualizacion.py sean mas rapidas.
    
    create_reviews = """
            CREATE TABLE reviews (
                id_review INT NOT NULL AUTO_INCREMENT,
                review_uid VARCHAR(220) NOT NULL,
                id_user INT NOT NULL,
                id_product INT NOT NULL,
                overall FLOAT,
                helpful_yes INT,
                helpful_total INT,
                unix_review_time INT,
                review_date DATE,
                PRIMARY KEY (id_review),
                UNIQUE KEY uq_reviews_review_uid (review_uid),
                KEY idx_reviews_user (id_user),
                KEY idx_reviews_product (id_product),
                KEY idx_reviews_date (review_date),
                KEY idx_reviews_unix_time (unix_review_time),
                FOREIGN KEY (id_user) REFERENCES users(id_user),
                FOREIGN KEY (id_product) REFERENCES products(id_product)
            );
            """
            # Otra vez, añadimos indices (KEY) en columnas que luego usaremos 
            # para hacer JOINs o filtrar reviews, para mejorar el rendimiento.
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute(create_product_types)
            cursor.execute(create_users)
            cursor.execute(create_user_names)
            cursor.execute(create_products)
            cursor.execute(create_reviews)
        conexion.commit()
    finally:
        conexion.close()


# MongoDB.
def preparacion_mongodb() -> None:
    """
    Eliminamos la coleccion si ya existia y creamos indices.
    """
    print('MongoDB -> Preparando coleccion...')
    db = get_mongo_database(MONGO_DATABASE)
    collection = db[MONGO_COLLECTION]

    if MONGO_COLLECTION in db.list_collection_names():
        print('MongoDB -> La coleccion ya existe. Eliminandola...')
        collection.drop()

    collection.create_index('review_uid', unique=True)
    collection.create_index('product_type')
    collection.create_index('mysql_keys.reviewer_id_original')
    collection.create_index('mysql_keys.asin')


# Insercion de tipos de producto.
def insertar_product_types() -> dict:
    """
    Inserta los tipos de producto y devuelve un mapa:
    nombre_tipo -> id_product_type
    """
    print('MySQL -> Insertando tipos de producto...')
    conexion = get_mysql_connection(MYSQL_DATABASE)

    sql_insert = """
        INSERT INTO product_types (product_type_name, source_file_path)
        VALUES (%s, %s);
    """

    sql_select = """
        SELECT id_product_type, product_type_name
        FROM product_types;
    """

    try:
        with conexion.cursor() as cursor:
            for product_type_name, file_path in DATASETS.items():
                cursor.execute(sql_insert, (product_type_name, file_path))
        conexion.commit()

        product_type_map = {}
        with conexion.cursor() as cursor:
            cursor.execute(sql_select)
            resultados = cursor.fetchall()
            for fila in resultados:
                id_product_type = fila[0]
                product_type_name = fila[1]
                product_type_map[product_type_name] = id_product_type

        return product_type_map
    finally:
        conexion.close()


# Inserciones en lote.
def insertar_lotes_mysql(cursor, batch_user_names, batch_reviews):
    """
    Inserta los lotes pendientes de MySQL.
    """
    if batch_user_names:
        sql_user_names = """
            INSERT INTO user_names (id_user, reviewer_name)
            VALUES (%s, %s);
        """
        cursor.executemany(sql_user_names, batch_user_names)
        batch_user_names.clear()

    if batch_reviews:
        sql_reviews = """
            INSERT INTO reviews (
                review_uid,
                id_user,
                id_product,
                overall,
                helpful_yes,
                helpful_total,
                unix_review_time,
                review_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.executemany(sql_reviews, batch_reviews)
        batch_reviews.clear()


def insertar_lote_mongo(collection, batch_reviews_mongo):
    """
    Inserta el lote pendiente de MongoDB.
    """
    if batch_reviews_mongo:
        collection.insert_many(batch_reviews_mongo)
        batch_reviews_mongo.clear()


# Carga principal.
def cargar_datasets(product_type_map:dict) -> None:
    """
    Cargamos los 4 datasers linea a linea.
    Insertamos en MySQL la parte estructurada y en MongoDB la review documental.
    """
    print('Carga -> Iniciando proceso completo de carga...')

    conexion_mysql = get_mysql_connection(MYSQL_DATABASE)
    db_mongo = get_mongo_database(MONGO_DATABASE)
    collection_mongo = db_mongo[MONGO_COLLECTION]

    # Mapas de ids internos.
    user_map = {}
    product_map = {}

    # Para no repetir nombres ya insertados del mismo usuario.
    user_name_seen = set()

    # Para no insertar cada vez.
    batch_user_names = []
    batch_reviews = []
    batch_reviews_mongo = []

    total_reviews = 0

    sql_insert_user = """
                INSERT INTO users (reviewer_id_original)
                VALUES (%s);
                """
    
    sql_insert_product = """
                INSERT INTO products (asin, id_product_type)
                VALUES (%s, %s);
                """
    try:
        with conexion_mysql.cursor() as cursor:
            for product_type_name, file_path in DATASETS.items():
                print(f'Carga -> Procesando tipo de producto: {product_type_name}')
                id_product_type = product_type_map[product_type_name]

                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    # Usamos errors=replace de adquisicion por si hubiera caracteres raros
                    # ya que no lo podemos asegurar con files tan grandes.
                    for line in file:
                        line = line.strip()
                        if not line:
                            continue

                        review = json.loads(line)

                        reviewer_id_original = limpieza_basica(review.get('reviewerID'))
                        reviewer_name = limpieza_basica(review.get('reviewerName'))
                        asin = limpieza_basica(review.get('asin'))

                        # Si falta el id de usuario o de producto, no guardamos la linea.
                        if reviewer_id_original == '' or asin == '':
                            continue

                        overall = review.get('overall')
                        unix_review_time = review.get('unixReviewTime')
                        review_time_original = review.get('reviewTime')
                        review_date = formateo_review_time(review_time_original)
                        helpful_yes, helpful_total = extraccion_helpful(review)

                        review_uid = construccion_review_uid(product_type_name, reviewer_id_original, asin, unix_review_time)

                        # Usuario.
                        if reviewer_id_original not in user_map:
                            cursor.execute(sql_insert_user, (reviewer_id_original,))
                            id_user = cursor.lastrowid          # Nota de autoria: para poder añadirlo a nuestro diccionario correctamente, usamos .lastrowid
                                                                #                  para obtener el ultimo identificador (generado en la linea anterior en la insercion)
                                                                #                  y asi podemos usar tambien ese mismo id en otras tablas. (se podria hacer con una  
                                                                #                  consulta pero asi es mas rapido).
                            user_map[reviewer_id_original] = id_user
                        else:
                            id_user = user_map[reviewer_id_original]

                        # Nombre observado del usuario.
                        if reviewer_name != '':
                            key_user_name = (id_user, reviewer_name)
                            if key_user_name not in user_name_seen:
                                user_name_seen.add(key_user_name)
                                batch_user_names.append((id_user, reviewer_name))

                        # Producto.
                        product_key = (asin, id_product_type)
                        if product_key not in product_map:
                            cursor.execute(sql_insert_product, (asin, id_product_type))
                            id_product = cursor.lastrowid
                            product_map[product_key] = id_product
                        else:
                            id_product = product_map[product_key]

                        # Review para MySQL.
                        batch_reviews.append((review_uid, id_user, id_product, overall, helpful_yes, helpful_total, unix_review_time, review_date))

                        # Review para MongoDB.
                        mongo_doc = {'review_uid': review_uid,
                                     'product_type': product_type_name,
                                     'mysql_keys': {'reviewer_id_original': reviewer_id_original,
                                                    'asin': asin
                                                    },
                                     'review_document': {'reviewerID': review.get('reviewerID'),
                                                         'asin': review.get('asin'),
                                                         'reviewerName': review.get('reviewerName'),
                                                         'helpful': review.get('helpful'),
                                                         'reviewText': review.get('reviewText'),
                                                         'overall': review.get('overall'),
                                                         'summary': review.get('summary'),
                                                         'unixReviewTime': review.get('unixReviewTime'),
                                                         'reviewTime': review.get('reviewTime'),
                                                         }
                                    }
                        
                        batch_reviews_mongo.append(mongo_doc)

                        total_reviews += 1

                        # Insercion por lotes.
                        if len(batch_user_names) >= BATCH_SIZE or len(batch_reviews) >= BATCH_SIZE:
                            insertar_lotes_mysql(cursor, batch_user_names, batch_reviews)
                        
                        if len(batch_reviews_mongo) >= BATCH_SIZE:
                            insertar_lote_mongo(collection_mongo, batch_reviews_mongo)

                insertar_lotes_mysql(cursor, batch_user_names, batch_reviews)
                insertar_lote_mongo(collection_mongo, batch_reviews_mongo)
                conexion_mysql.commit()
                print(f'Carga -> Tipo completado: {product_type_name}')

        conexion_mysql.commit()
        print(f'Carga -> Proceso completado. Reviews insertadas: {total_reviews}')

    except Exception as e:
        conexion_mysql.rollback()
        print(f'Error durante la carga: {e}')
        raise

    finally:
        conexion_mysql.close()


def main() -> None:
    """
    Ejecutamos todo el proceso de creacion y carga.
    """
    print ('--- INICIO DEL PROCESO DE CARGA ---')

    crear_bbdd_mysql()
    borrar_tablas_mysql()
    crear_tablas_mysql()
    preparacion_mongodb()

    product_type_map = insertar_product_types()
    cargar_datasets(product_type_map)

    print('--- FIN DEL PROCESO DE CARGA ---')


if __name__ == '__main__':
    main()