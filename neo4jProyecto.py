"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

Acceso y visualizacion de los datos a través de neo4j.
Incluye:
    1. Grafo mostrando similitudes entre usuarios
    2. Grafo mostrando enlaces entre usuarios y artículos
    3. Grafo mostrando usuarios que han visto más de un determinado tipo de artículo
    4. Grafo mostrando artículos populares y artículos en común entre usuarios
"""
# Importamos las librerías necesarias
import pymysql

from neo4j import GraphDatabase
from neo4j import Driver

# Importamos las variables y los módulos necesarios
from configuracion import (
    MYSQL_HOST,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    NEO4J_URI, 
    NEO4J_PASSWORD
)

def limpiar_neo4j(driver: Driver): 
    """
    Elimina todos los nodos y relaciones actuales del servidor de Neo4j
    """
    consulta = '''MATCH (n)
                DETACH DELETE n'''
    
    with driver.session() as session: 
        session.run(consulta)


def consultas_op1(conexion: pymysql.connect, num_users: int): 
    """
    Busca la información necesaria en la base de datos de SQL devolviendola en forma de diccionario o lista. 

    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información. 
        num_users (int): variable que indica el número de usuarios de los que deseamos obtener la información. 
    Returns: 
        info_users (dict): diccionario que almacena el id_original del usuario junto con su número de reviews para cada usuario encontrado. 
        reviews_result (list): lista que almacenará los productos comunes entre dos usuarios.   
    """
    consulta_users = """
    SELECT u.id_user, u.reviewer_id_original, COUNT(r.id_review) AS num_rev
    FROM users u
    JOIN reviews r ON r.id_user = u.id_user
    GROUP BY u.id_user, u.reviewer_id_original
    ORDER BY num_rev DESC
    LIMIT %s;
    """
    params = ', '.join(['%s']*num_users)    # (%s, %s, ....) para todos los usuarios que vamos a introducir, obtenidos de la consulta anterior
    consulta_rev = f"""
    SELECT
            r.id_user,
            r.id_product,
            r.overall
        FROM reviews r
        WHERE r.id_user IN ({params})
        ORDER BY r.id_user, r.id_product;
    """

    with conexion.cursor() as cursor: 
        # Conseguimos los top usuarios con más reviews almacenando su id, su id_original y el número de reviews 
        cursor.execute(consulta_users, (num_users, ))
        result = cursor.fetchall()

        # Almacenamos la información
        top_users = []
        info_users = {}
        for id_user, reviewer_id_original, num_rev in result:
            top_users.append(id_user)
            info_users[id_user] = {
                'reviewer_id_original': reviewer_id_original,
                'num_reviews': num_rev
            }

        # Conseguimos todas las reviews de estos
        cursor.execute(consulta_rev, top_users)
        reviews_result = cursor.fetchall()
    
    return info_users, reviews_result

def calcular_pearson(rev1: dict, rev2: dict, media1: float, media2: float)-> float: 
    """
    Toma las puntuaciones de productos de dos usuarios junto con la puntuación media que han dado y calcula su similitud de Pearson. 

    Args: 
        rev1, rev2 (dict): diccionarios que almacenan los productos que han puntuado los dos usuarios junto con la puntuación que les han dado. 
        media1, media2 (float): las puntuaciones que han dado ambos usuarios de media entre todos los productos. 
    Returns: 
        pearson (float): la similitud obtenida entre el usuario1 y el usuario2 tras aplicarle a fórmula a los valores recibidos. 
    """
    comunes = set(rev1.keys()) & set(rev2.keys())   # Nos quedamos con las reviews que ambos usuarios han puntuado
    
    if not comunes: 
        return None
    
    num = 0.0
    sum1 = 0.0
    sum2 = 0.0
    
    # Calculamos la fórmula
    for product in comunes: 
        dif1 = rev1[product] - media1
        dif2 = rev2[product] - media2

        num += dif1*dif2
        sum1 += dif1**2
        sum2 += dif2**2

    denom = (sum1**0.5)*(sum2**0.5)

    if denom == 0: 
        return None
    return num/denom

def similitudes_users(conexion: pymysql.connect, num_users=30): 
    """
    Función que, empleando otras funciones auxiliares consigue y limpia los datos de nuestra base para poder cargarlos en el servidor de Neo4j. 

    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información. 
        num_users (int): variable que indica el número de usuarios de los que deseamos obtener la información. 
    Returns: 
        info_usuarios (dict): diccionario que almacena el id_original del usuario junto con su número de reviews para cada usuario encontrado. 
        similitudes (list): lista donde almacenamos la similitud calculada entre todos los posibles pares de usuarios. 
    """

    info_users, reviews_result = consultas_op1(conexion, num_users)
    
    # Creamos un diccionario con las reviews y las valoraciones de los usuarios encontrados. 
    valoraciones_por_user = {}
    for id_user, id_product, overall in reviews_result: 
        if id_user not in valoraciones_por_user:
            valoraciones_por_user[id_user] = {}
        valoraciones_por_user[id_user][id_product] = float(overall)

    # Calculamos la media de valoración de cada usuario
    medias_por_user = {}
    for id_user, valoraciones in valoraciones_por_user.items(): 
        suma = sum(valoraciones.values())
        num_val = len(valoraciones)
        medias_por_user[id_user] = suma / num_val
    
    # Calculamos las similitudes entre usuarios
    similitudes = []
    usuarios = list(valoraciones_por_user.keys())
    
    # Doble bucle para comparar un usuario con el resto, lo hacemos para todos 
    for i in range(len(usuarios)): 
        for j in range(i+1, len(usuarios)): 
            # comparamos dos usuarios
            user1 = usuarios[i]
            user2 = usuarios[j]

            # Recogemos todas las reviews de ambos 
            rev1 = valoraciones_por_user[user1]
            rev2 = valoraciones_por_user[user2]

            # Recogemos la media de overall de ambos
            media1 = medias_por_user[user1]
            media2 = medias_por_user[user2]

            # Calculamos la similitud de Pearson
            pearson = calcular_pearson(rev1, rev2, media1, media2)
            if pearson is not None: 
                similitudes.append((user1, user2, pearson))

    return info_users, similitudes

def cargar_grafo_op1(driver: Driver, info_usuarios: dict, similitudes: list): 
    """
    Cargar el grafo en Neo4j del apartado 4.1. a partir de la información obtenida de la base de datos. 
    """
    crear_users = '''
    MERGE (u:Usuario {id_user: $id_user})
    SET u.reviewer_id_original = $reviewer_id_original,
        u.num_reviews = $num_reviews
    '''
    cargar_relaciones = '''
    MATCH (u1:Usuario {id_user: $id_user1})
    MATCH (u2:Usuario {id_user: $id_user2})
    MERGE (u1)-[r:SIMILAR_A]-(u2)
    SET r.pearson = $pearson   
    '''

    # Cargamos los datos
    with driver.session() as session:
        # Añadimos los usuarios 
        for id_user, datos in info_usuarios.items(): 
            session.run(crear_users, id_user=id_user, reviewer_id_original=datos['reviewer_id_original'], num_reviews=datos['num_reviews'])
        # Añadimos las relaciones entre ellos
        for id_user1, id_user2, pearson in similitudes: 
            session.run(cargar_relaciones, id_user1=id_user1, id_user2=id_user2, pearson=pearson)

def busqueda_op1(driver: Driver)-> str: 
    """
    Devuelve el usuario con más vecinos. 
    """
    consulta = '''
    MATCH (u: Usuario) -[SIMILAR_A]-(Usuario)
    RETURN u.id_user as id_user, u.reviewer_id_original as reviewer_id_original, COUNT(*) as num_vecinos
    ORDER BY num_vecinos DESC
    LIMIT 1    
    '''
    with driver.session() as session: 
        result = session.run(consulta)
        usuario = result.single()
    if usuario is not None:
        return f'El usuario {usuario['id_user']} cuyo id original es {usuario['reviewer_id_original']} es el que tiene más vecinos, tiene {usuario['num_vecinos']} vecinos. '
    else: 
        return 'No se ha encontrado ningún usuario. '

def ejecucion_op1(conexion: pymysql.connect, driver: Driver): 
    """
    Ejecuta todo lo necesario para completar el apartado 4.1 de la práctica. Primero obtiene la información de la base de datos, después crea el grafo en Neo4j 
    y finalmente ejecuta la consulta de búsqueda pedida en Neo4j. 
    
    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información.
        driver (Driver): objeto para establecer la conexión con Neo4j. 
    """
    # Obtenemos la información del grafo
    print('\nRecogiendo la información de la base de datos...')
    info_usuarios, similitudes = similitudes_users(conexion)

    # Eliminamos posible información que pueda hacer en Neo4j
    print('Preparando Neo4j...')
    limpiar_neo4j(driver)
    # Cargamos la información nueva en Neo4j
    print('Creando el grafo resultante...')
    cargar_grafo_op1(driver, info_usuarios, similitudes)

    # Consulta adicional
    print('Buscamos al usuario con más vecinos...')
    print(busqueda_op1(driver),'\n')
    print('Operación ejecutada con éxito. ')


def productos_users(conexion: pymysql.connect, n: int, tipo: str):
    """
    Busca la información necesaria en la base de datos de SQL devolviendola en forma de diccionario o lista. 

    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información. 
        n (int): el número de productos que vamos a buscar. 
        tipo (str): el tipo de producto que van a ser los productos encontrados. 
    Returns: 
        resultado (list): lista de tuplas donde cada tupla guarda la información de un producto en concreto junto con el usuario que lo ha puntuado y los detalles de esta review. 
    """
    
    cargar_articulos = '''
    SELECT p.id_product, p.asin, pt.product_type_name
    FROM products p
    INNER JOIN product_types pt ON p.id_product_type = pt.id_product_type
    WHERE pt.product_type_name = %s
    ORDER BY RAND()
    LIMIT %s;
    '''
    params = ', '.join(['%s']*n)    # (%s, %s, ....) para todos los productos que vamos a introducir, obtenidos de la consulta anterior
    cargar_info = f'''
    SELECT r.id_product, u.id_user, u.reviewer_id_original, r.overall, r.unix_review_time
    FROM reviews r
    INNER JOIN users u ON r.id_user=u.id_user
    WHERE r.id_product IN ({params})
    ORDER BY r.id_product, u.id_user;
    '''
    info_articulos = {}
    resultado = []
    with conexion.cursor() as cursor: 
        # Conseguimos los productos
        cursor.execute(cargar_articulos, (tipo, n))
        articulos = cursor.fetchall()

        # Almacenamos la información
        ids_products = [fila[0] for fila in articulos]
        for id_pro, asin, pro_type_name in articulos: 
            info_articulos[id_pro] = (asin, pro_type_name)

        # Conseguimos la información adicional sobre los productos
        cursor.execute(cargar_info, ids_products)
        reviews = cursor.fetchall()

        # Almacenamos la información
        for id_pro, id_user, reviewer_id_original, overall, time in reviews: 
            asin, pro_type_name = info_articulos[id_pro]
            resultado.append((id_pro, asin, pro_type_name, id_user, reviewer_id_original, overall, time))

    return resultado

def cargar_grafo_op2(driver: Driver, info: list): 
    """
    Cargar el grafo en Neo4j del apartado 4.2. a partir de la información obtenida de la base de datos. 
    """
    consulta = '''
    MERGE (u:Usuario {id_user: $id_user})
    SET u.reviewer_id_original = $reviewer_id_original

    MERGE (a:Articulo {id_product: $id_product})
    SET a.asin = $asin,
        a.product_type_name = $product_type_name

    MERGE (u)-[r:PUNTUO {unix_review_time: $unix_review_time}]->(a)
    SET r.overall = $overall
    '''
    with driver.session() as session: 
        for fila in info: 
            id_pro, asin, pro_type_name, id_user, reviewer_id_orig, overall, time = fila
            session.run(consulta, id_user=id_user, reviewer_id_original=reviewer_id_orig, id_product=id_pro, asin=asin, product_type_name=pro_type_name, overall=float(overall), unix_review_time=int(time))

def ejecucion_op2(conexion: pymysql.connect, driver: Driver): 
    """
    Ejecuta todo lo necesario para completar el apartado 4.2 de la práctica. Primero obtiene la información de la base de datos, después crea el grafo en Neo4j. 
    
    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información.
        driver (Driver): objeto para establecer la conexión con Neo4j. 
    """
    # El usuario introduce los artículos de los que desea formar el grafo
    print('Primero debe escoger el número de artículos y su tipo, si no se escogen valores válidos se creará un grafo para 20 artículos de tipo Digital Music. ')
    n = input('De cuántos artículos desea formar el grafo: ')
    tipo = input('''Que tipo de artículos serán, escoger entre:  
- Digital Music
- Musical Instruments
- Toys and Games
- Video Games: ''')
    tipos = ('Digital Music', 'Musical Instruments', 'Toys and Games', 'Video Games')
    
    # Obtenemos la información del grafo
    print('\nRecogiendo la información de la base de datos...')
    if n.isdecimal() and tipo in tipos: 
        info = productos_users(conexion, int(n), tipo)
    else: 
        print('No se han introducido datos válidos, se usarán los valores predeterminados. ')
        info = productos_users(conexion, 20, 'Digital Music')
    
    # Eliminamos posible información que pueda hacer en Neo4j
    print('Preparando Neo4j...')
    limpiar_neo4j(driver)
    
    # Cargamos la información nueva en Neo4j
    print('Creando el grafo resultante...')
    cargar_grafo_op2(driver, info)
    print('Operación ejecutada con éxito. ')


def obtener_usuarios(conexion: pymysql.connect): 
    """
    Busca la información necesaria en la base de datos de SQL devolviendola en forma de diccionario o lista. 

    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información. 
    Returns: 
        result_bueno (list): lista de tuplas que almacena toda la información recopilada donde cada tupla muestra los datos de un producto.  
    """
    num_users=400
    usuarios = '''
    SELECT u.id_user, u.reviewer_id_original, MIN(un.reviewer_name) AS reviewer_name
    FROM users u
    INNER JOIN user_names un ON u.id_user = un.id_user
    GROUP BY u.id_user, u.reviewer_id_original
    ORDER BY reviewer_name
    LIMIT 400;
    '''
    params = ', '.join(['%s']*num_users)
    tipos_productos = f'''
    SELECT r.id_user, pt.product_type_name, COUNT(DISTINCT r.id_product) AS num_products
    FROM reviews r
    INNER JOIN products p ON r.id_product = p.id_product
    INNER JOIN product_types pt ON p.id_product_type = pt.id_product_type
    WHERE r.id_user IN ({params})
    GROUP BY r.id_user, pt.product_type_name
    ORDER BY r.id_user, pt.product_type_name;
    '''
    info_usuarios = {}
    tipos = {}
    resultado = []
    with conexion.cursor() as cursor: 
        # Conseguimos los usuarios
        cursor.execute(usuarios)
        users = cursor.fetchall()

        # Almacenamos la información
        ids_users = [fila[0] for fila in users]
        for id_user, rev_id_orig, rev_name in users: 
            info_usuarios[id_user] = {'reviewer_id_original': rev_id_orig, 'reviewer_name': rev_name}

        # Conseguimos los productos puntuados y sus tipos por usuario
        cursor.execute(tipos_productos, ids_users)
        info = cursor.fetchall()

        # Almacenamos la información
        # Agrupamos los tipos de producto por usuario
        for id_user, product_type, num_articulos in info: 
            if id_user not in tipos: 
                tipos[id_user] = set()
            tipos[id_user].add(product_type)
            # Guardamos toda la información en la lista resultado
            resultado.append((id_user, info_usuarios[id_user]['reviewer_id_original'], info_usuarios[id_user]['reviewer_name'], product_type, num_articulos))
        
        # Buscamos solo los usuarios que hayan puntuados a productos de dos o más tipos distintos
        result_bueno = []
        for dato in resultado: 
            id_user = dato[0]
            if len(tipos[id_user]) >= 2:
                result_bueno.append(dato)
        
        return result_bueno

def cargar_grafo_op3(driver: Driver, info: list): 
    """
    Cargar el grafo en Neo4j del apartado 4.3. a partir de la información obtenida de la base de datos. 
    """
    consulta = '''
    MERGE (u:Usuario {id_user: $id_user})
    SET u.reviewer_id_original = $reviewer_id_original,
        u.reviewer_name = $reviewer_name

    MERGE (t:TipoProducto {nombre: $product_type_name})

    MERGE (u)-[r:CONSUME_TIPO]->(t)
    SET r.num_articulos = $num_articulos
    '''
    with driver.session() as session: 
        for fila in info: 
            id_user, reviewer_id_original, reviewer_name, product_type_name, num_articulos = fila
            session.run(consulta, id_user=id_user, reviewer_id_original=reviewer_id_original, reviewer_name=reviewer_name, product_type_name=product_type_name, num_articulos=int(num_articulos))

def ejecucion_op3(conexion: pymysql.connect, driver: Driver): 
    """
    Ejecuta todo lo necesario para completar el apartado 4.3 de la práctica. Primero obtiene la información de la base de datos, después crea el grafo en Neo4j. 
    
    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información.
        driver (Driver): objeto para establecer la conexión con Neo4j. 
    """
    # Obtenemos la información del grafo
    print('\nRecogiendo la información de la base de datos...')
    info = obtener_usuarios(conexion)
    
    # Eliminamos posible información que pueda hacer en Neo4j
    print('Preparando Neo4j...')
    limpiar_neo4j(driver)
    
    # Cargamos la información nueva en Neo4j
    print('Creando el grafo resultante...')
    cargar_grafo_op3(driver, info)
    print('Operación ejecutada con éxito. ')


def obtener_articulos(conexion: pymysql.connect): 
    """
    Busca la información necesaria en la base de datos de SQL devolviendola en forma de diccionario o lista. 

    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información. 
    Returns: 
        info_grafo (list): lista que almacena en tuplas los datos asociados a cada producto junto con el usuario que lo ha puntua y los detalles de esto
        enlaces (list): lista que guarda dos usuarios diferentes junto con el número de artículos que ambos han puntuado. 
    """
    num_articulos = 5
    articulos = '''
    SELECT p.id_product, p.asin, pt.product_type_name, COUNT(r.id_review) AS num_reviews
    FROM products p
    INNER JOIN product_types pt ON p.id_product_type=p.id_product_type
    INNER JOIN reviews r ON p.id_product=r.id_product
    GROUP BY p.id_product, p.asin, pt.product_type_name
    HAVING COUNT(r.id_review) < 40
    ORDER BY num_reviews DESC
    LIMIT 5;
    '''
    params=', '.join(['%s']*num_articulos)
    usuarios =f'''
    SELECT r.id_product, u.id_user, u.reviewer_id_original, r.overall, r.unix_review_time
    FROM reviews r
    INNER JOIN users u ON u.id_user=r.id_user
    WHERE r.id_product IN ({params})
    ORDER BY r.id_product, u.id_user;
    '''

    info_productos = {}
    info_grafo = []
    enlaces = []
    usuarios_arts = {}  # Para almacenar los artículos a los que ha puntuado cada usuario
    with conexion.cursor() as cursor: 
        # Conseguimos los top artículos
        cursor.execute(articulos)
        arts = cursor.fetchall()

        # Almacenamos la información
        ids_products = [fila[0] for fila in arts]
        for id_product, asin, tipo, num in arts: 
            info_productos[id_product] = {'asin': asin, 'product_type_name': tipo, 'num_reviews': num}

        # Conseguimos los usuarios que han puntuado los artículos
        cursor.execute(usuarios, ids_products)
        users = cursor.fetchall()

    # Almacenamos la información
    for id_pro, id_user, id_orig, overall, time in users: 
        info_grafo.append((id_pro, info_productos[id_pro]['asin'], info_productos[id_pro]['product_type_name'], info_productos[id_pro]['num_reviews'], id_user, id_orig, overall, time))

        # Guardamos tambien los artículos que puntúa cada usuario
        if id_user not in usuarios_arts: 
            usuarios_arts[id_user] = set()
        usuarios_arts[id_user].add(id_pro)

    lista_users = list(usuarios_arts.keys())    # Creamos una lista con solo los usuarios

    # Buscamos los enlaces, los artículos e común entre dos usuarios
    for i in range(len(lista_users)): 
        for j in range(i+1, len(lista_users)): 
            u1 = lista_users[i]
            u2 = lista_users[j]
            comunes = usuarios_arts[u1] & usuarios_arts[u2]     # Buscamos los elementos en común, si los hay

            if comunes: 
                enlaces.append((u1, u2, len(comunes)))

    return info_grafo, enlaces          

def cargar_grafo_op4(driver: Driver, info: list, enlaces: list): 
    """
    Cargar el grafo en Neo4j del apartado 4.4. a partir de la información obtenida de la base de datos. 
    """
    consulta_user_art = '''
    MERGE (u:Usuario {id_user: $id_user})
    SET u.reviewer_id_original = $reviewer_id_original

    MERGE (a:Articulo {id_product: $id_product})
    SET a.asin = $asin,
        a.product_type_name = $product_type_name,
        a.num_reviews = $num_reviews

    MERGE (u)-[r:PUNTUO {unix_review_time: $unix_review_time}]->(a)
    SET r.overall = $overall
    '''
    consulta_enlaces = '''
    MATCH (u1:Usuario {id_user: $id_user1})
    MATCH (u2:Usuario {id_user: $id_user2})
    MERGE (u1)-[r:EN_COMUN]-(u2)
    SET r.num_comunes = $num_comunes
    '''

    with driver.session() as session: 
        for fila in info: 
            id_pro, asin, tipo, num_rev, user, id_orig, overall, time = fila
            session.run(consulta_user_art, id_user=user, reviewer_id_original=id_orig, id_product=id_pro, asin=asin, product_type_name=tipo, num_reviews=int(num_rev), overall=float(overall), unix_review_time=int(time))

        for u1, u2, comunes in enlaces: 
            session.run(consulta_enlaces, id_user1=u1, id_user2=u2, num_comunes=comunes)

def ejecucion_op4(conexion: pymysql.connect, driver: Driver): 
    """
    Ejecuta todo lo necesario para completar el apartado 4.4 de la práctica. Primero obtiene la información de la base de datos, después crea el grafo en Neo4j. 
    
    Args: 
        Conexion (connect): conexión establecida con MySQL para obtener la información.
        driver (Driver): objeto para establecer la conexión con Neo4j. 
    """
    # Obtenemos la información del grafo
    print('\nRecogiendo la información de la base de datos...')
    info_grafo, enlaces = obtener_articulos(conexion)

    # Eliminamos posible información que pueda hacer en Neo4j
    print('Preparando Neo4j...')
    limpiar_neo4j(driver)

    # Cargamos la información nueva en Neo4j
    print('Creando el grafo resultante...')
    cargar_grafo_op4(driver, info_grafo, enlaces)
    print('Operación ejecutada con éxito. ')


def mostrar_menu(): 
    """
    Muestra el menú principal. 
    """
    print('''
--- MENU DE VISUALIZACION ---
1. Mostrar similitudes entre usuarios
2. Mostrar enlaces entre usuarios y artículos
3. Mostrar usuarios que han visto más de un determinado tipo de artículo
4. Mostrar artículos populares y artículos en común entre usuarios
5. Salir
    ''')

def main(): 
    """
    Primero establecemos las conexiones, luego ejecutamos el menu hasta que el usuario seleccione salir.
    """
    # Establecemos la conexión a PyMySQL
    conexion = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
        )
    # Establecemos la conexión a Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))
    
    while True:
        mostrar_menu()
        opcion = input('Selecciona una opcion: ').strip()
        
        if opcion == '1':
            ejecucion_op1(conexion, driver)
        elif opcion == '2':
            ejecucion_op2(conexion, driver)
        elif opcion == '3':
            ejecucion_op3(conexion, driver)
        elif opcion == '4':
            ejecucion_op4(conexion, driver)
        elif opcion == '5':
            print('Saliendo del programa...')
            break
        else:
            print('Opcion no valida. Intentalo de nuevo.')


if __name__ == '__main__': 
    main()