"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

En este fichero:
    1. Se inserta el dataset de Amazon_Instant_Video_5.json 
    2. Reutiliza usuariso y productos ya existentes
    3. Evita duplicados si el script se ejecuta más de una vez
    4. No recrea las bases de datos ni de SQl ni de MongoDB

"""
# Importamos las librerías necesarias
import json
from datetime import datetime

import pymysql
from pymysql.cursors import Cursor
from pymongo import MongoClient
from pymongo.database import Database
from pymysql.connections import Connection

# Importamos los módulos necesarios
from load_data import get_mysql_connection, get_mongo_database, limpieza_basica, formateo_review_time, extraccion_helpful, construccion_review_uid, insertar_lote_mongo, insertar_lotes_mysql

# Importamos las variables de otros módulos necesarias
from configuracion import (
    MYSQL_DATABASE,
    MONGO_DATABASE,
    MONGO_COLLECTION,
    BATCH_SIZE
)

def obten_insert_tipo(cursor: Cursor, nombre: str, ruta: str) -> int: 
    """
    Regula la existencia del tipo de producto nuevo que vamos a introducir en la base de datos. Si existe devuelve su identificador asociado. De lo contrario, 
    lo añade a la tabla creando a su vez su identificador y lo devuelve. 

    Args: 
        cursor (Cursor): Objeto con el que accedemos a la base de datos de MySQL y buscamos o cargamos información
        nombre (str): el tipo de producto. 
        ruta (str): la ruta a través la cuál accedemos a la base de datos. 
    """
    existe = '''
    SELECT id_product_type
    FROM product_types
    WHERE product_type_name = %s;
    '''
    no_existe = '''
    INSERT INTO product_types (product_type_name, source_file_path)
    VALUES (%s, %s);
    '''
    # Vemos si existe
    cursor.execute(existe, (nombre,))
    result = cursor.fetchone()
    if result is not None:
        print('El tipo de producto Amazon Instant Video ya existe, devolvemos el identificador. ')
        return result[0]
    
    # Si no existe lo creamos
    print('El tipo de producto Amazon Instant Video no existe, lo creamos y devolvemos el identificador. ')
    cursor.execute(no_existe, (nombre, ruta))
    return cursor.lastrowid

def existe_review(cursor: Cursor, review_uid: str) -> bool: 
    """
    Comprueba si una review ya existe en la base de datos de MySQL a partir de su identificador y devuelve True en caso de que exista y 
    False de lo contrario 
    """
    consulta = '''
    SELECT 1
    FROM reviews
    WHERE review_uid = %s
    LIMIT 1;
    '''
    cursor.execute(consulta, (review_uid, ))
    result = cursor.fetchone()
    return result is not None

def existe_user(cursor: Cursor) -> set: 
    """
    Carga en memoria los nombres de usuario ya existentes en la base de datos para asegurarnos de que no cargamos el mismo nombre más de 
    una vez. 

    Returns: 
        user_names (set): set de tuplas conteniendo todos los uer_names del datasat ya cargado junto con su identificador asociado. 
    """
    consulta = '''
    SELECT id_user, reviewer_name
    FROM user_names
    '''

    cursor.execute(consulta)
    users = cursor.fetchall()
    user_names = set()

    for id, rev_name in users: 
        user_names.add((id, rev_name))
    
    return user_names

def cargar_usermap(cursor: Cursor) -> dict:
    """
    Carga en memoria los usuarios ya existentes en la base de datos

    Args: 
        cursor (Cursor): Objeto con el que accedemos a la base de datos de MySQL y buscamos o cargamos información. 
    Returns: 
        usermap (dict): diccionario que almacena todos los identificadores originales de los usuarios y su identificardor de SQL asociado. 
    """
    consulta = '''
    SELECT id_user, reviewer_id_original
    FROM users;
    '''
    print('Almacenamos los usuarios ya existentes...')
    cursor.execute(consulta)
    resultados = cursor.fetchall()
    usermap = {}
    for id_user, id_orig in resultados: 
        usermap[id_orig] = id_user
    return usermap

def cargar_productmap(cursor: Cursor) -> dict: 
    """
    Carga en memoria los productos ya existentes en la base de datos para evitar duplicados. 

    Args: 
        cursor (Cursor): Objeto con el que accedemos a la base de datos de MySQL y buscamos o cargamos información. 
    Returns: 
        product_map (dict): diccionario donde almacenamos los datos de los productos junto con su identificador asociado. 
    """
    consulta = '''
    SELECT id_product, asin, id_product_type
    FROM products;
    '''
    cursor.execute(consulta)
    resultado = cursor.fetchall()
    product_map = {}

    for id_pro, asin, tipo in resultado: 
        product_map[(asin, tipo)] = id_pro
    
    return product_map

def cargar_dataset(tipo: str, ruta: str): 
    """
    Inserta de forma incremental el dataset asociado en la ruta recibida por augumentos enn la base de datos ya creada. 

    Args: 
        tipo (str): tipo que cladifica los nuevos productos que vamos a almacenar. 
        ruta (str): ruta asociada al fichero json donde se almacena la información que queremos cargar en la base de datos.   
    """
    print('Estableciendo la conexión con MySQL...')
    conexion_mysql = get_mysql_connection(MYSQL_DATABASE)
    print('Estableciendo la coneción con MongoDB...')
    db_mongo = get_mongo_database(MONGO_DATABASE)
    collection_mongo = db_mongo[MONGO_COLLECTION]

    batch_users = []
    batch_rev = []
    batch_rev_mongo = []

    total_leidas = 0
    insertadas = 0
    duplicadas = 0

    # Consultas sql
    insert_user = '''
    INSERT INTO users (reviewer_id_original)
    VALUES (%s);
    '''
    insert_product = '''
    INSERT INTO products (asin, id_product_type)
    VALUES (%s, %s);
    '''

    try: 
        print('Cargando los datos nuevos en la base de datos...')
        with conexion_mysql.cursor() as cursor: 
            # Obtenemos el identificador asociado al tipo de producto a insertar
            id_product_type = obten_insert_tipo(cursor, tipo, ruta)

            # Cargamos los datos ya existentes
            user_map = cargar_usermap(cursor)
            product_map = cargar_productmap(cursor)
            user_names_in = existe_user(cursor)

            with open(ruta, 'r', encoding='utf-8') as f: 
                for linea in f: 
                    linea = linea.strip()
                    if not linea:                           # Si la linea está vacía no hay nada que insertar
                        continue
                    
                    total_leidas += 1
                    # Cargamos la review
                    rev = json.loads(linea)

                    # limpiamos los datos
                    rev_id_orig = limpieza_basica(rev.get('reviewerID'))
                    rev_name = limpieza_basica(rev.get('reviewerName'))
                    asin = limpieza_basica(rev.get('asin'))

                    if rev_id_orig == '' or asin == '':     # Si estos campos están vacíos no hay nada que insertar
                        continue

                    # Recogemos el resto de variables
                    overall = rev.get('overall')
                    time = rev.get('unixReviewTime')
                    time_orig = rev.get('reviewTime')
                    review_date = formateo_review_time(time_orig)
                    helpful_yes, helpful_tot = extraccion_helpful(rev)

                    rev_uid = construccion_review_uid(tipo, rev_id_orig, asin, time)

                    if existe_review(cursor, rev_uid):      # Controlamos que la review no esté ya en la base de datos
                        duplicadas += 1
                        continue

                    # Carga usuario comprobando si ya existe
                    if rev_id_orig not in user_map: 
                        cursor.execute(insert_user, (rev_id_orig, ))
                        id_user = cursor.lastrowid
                        user_map[rev_id_orig] = id_user
                    else: 
                        id_user = user_map[rev_id_orig]

                    # Carga nombre de usuario comprobando si ya existe
                    if rev_name != '': 
                        key_name = (id_user, rev_name)
                        if key_name not in user_names_in: 
                            user_names_in.add(key_name)
                            batch_users.append((id_user, rev_name))

                    # Carga de producto comprobando si ya existe
                    product_key = (asin, id_product_type)
                    if product_key not in product_map:          # Controlamos que el producto no esté ya en la base de datos
                        cursor.execute(insert_product, (asin, id_product_type))
                        id_product = cursor.lastrowid
                        product_map[product_key] = id_product
                    else: 
                        id_product = product_map[product_key]
                    
                    # Almacenamos review para cargarla en SQL
                    batch_rev.append((rev_uid, id_user, id_product, overall, helpful_yes, helpful_tot, time, review_date))

                    # Almacenamos review para cargarla en MongoDB
                    doc = {
                        'review_uid': rev_uid,
                        'product_type': tipo, 
                        'mysql_keys': {'reviewer_id_original': rev_id_orig, 'asin': asin}, 
                        'review_document': {
                            'reviewerID': rev.get('reviewerID'),
                            'asin': rev.get('asin'),
                            'reviewerName': rev.get('reviewerName'),
                            'helpful': rev.get('helpful'),
                            'reviewText': rev.get('reviewText'),
                            'overall': rev.get('overall'),
                            'summary': rev.get('summary'),
                            'unixReviewTime': rev.get('unixReviewTime'),
                            'reviewTime': rev.get('reviewTime')
                        }}
                    batch_rev_mongo.append(doc)
                    insertadas += 1

                    # Insertamos por lotes 
                    if len(batch_rev) >= BATCH_SIZE or len(batch_rev_mongo) >= BATCH_SIZE: 
                        insertar_lotes_mysql(cursor, batch_users, batch_rev)
                    if len(batch_rev_mongo) >= BATCH_SIZE: 
                        insertar_lote_mongo(collection_mongo, batch_rev_mongo)
            
            # Insertamos los datos restantes
            insertar_lotes_mysql(cursor, batch_users, batch_rev)
            insertar_lote_mongo(collection_mongo, batch_rev_mongo)
            conexion_mysql.commit()
            print('Fin de la carga de datos')

            print(f'Reviews leidas: {total_leidas}.')
            print(f'Reviews insertadas: {insertadas}.')
            print(f'Reviews duplicadas: {duplicadas}.')
            print('Proceso finalizado con éxito. ')
    except Exception as e: 
        conexion_mysql.rollback()
        print(f'Error durante la carga de datos: {e}')
        raise
    finally: 
        conexion_mysql.close()

def main(NEW_PRODUCT_TYPE: str, NEW_DATASET_PATH: str): 
    """
    Ejecuta la inserción del nuevo dataset en la base de datos existente. 

    Args: 
        NEW_PRODUCT_TYPE (str): nuevo tipo de producto a insertar.
        NEW_DATASET_PATH (str): ruta asociada al fichero que almacena la información a insertar.
    """
    print('---INICIO DEL PROCESO DE CARGA---')
    cargar_dataset(NEW_PRODUCT_TYPE, NEW_DATASET_PATH)
    print('---FIN DEL PROCESO DE INSERCIÓN---')

if __name__ == '__main__': 
    # Inicialización
    # Creamos las variables 
    NEW_PRODUCT_TYPE = 'Amazon Instant Video'
    NEW_DATASET_PATH = 'Amazon_Instant_Video_5.json'

    # Proceso
    main(NEW_PRODUCT_TYPE, NEW_DATASET_PATH)