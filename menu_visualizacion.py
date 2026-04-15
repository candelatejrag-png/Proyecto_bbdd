"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

Acceso y visualizacion de los datos.
Incluye:
    1. Histograma de reviews por año
    2. Evolucion de la popularidad de los articulos
    3. Histograma por nota
    4. Evolucion de las reviews a lo largo del tiempo
    5. Histograma de reviews por usuario
    6. Nube de palabras por categoria
    7. Grafica adicional: media de nota por categoria
    8. Salir
"""
import re
import matplotlib.pyplot as plt
import pymysql
from pymongo import MongoClient
from pymongo.database import Database
from wordcloud import WordCloud

from configuracion import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MONGO_CONNECTION_STRING,
    MONGO_DATABASE,
    MONGO_COLLECTION
)

# Conexiones.
def get_mysql_connection():
    """
    Devuelve una conexion a MySQL.
    """
    return pymysql.connect(
                        host = MYSQL_HOST,
                        user = MYSQL_USER,
                        password = MYSQL_PASSWORD,
                        port = MYSQL_PORT,
                        database = MYSQL_DATABASE
                    )


def get_mongo_database(database_name:str) -> Database:
    """
    Devuelve la base de datos de MongoDB.
    """
    client = MongoClient(MONGO_CONNECTION_STRING)
    return client[database_name]


# Utilidades de menu.
def mostrar_menu():
    """
    Muestra el menu principal.
    """
    print(f'\n--- MENU DE VISUALIZACION ---')
    print(f'1. Mostrar la evolucion de reviews por años')
    print(f'2. Evolucion de la popularidad de los articulos')
    print(f'3. Histograma por nota')
    print(f'4. Evolucion de las reviews a lo largo del tiempo')
    print(f'5. Histograma de reviews por usuario')
    print(f'6. Nube de palabras por categoria')
    print(f'7. Grafica adicional: media de nota por categoria')
    print(f'8. Salir')


def pedir_tipo_producto(permitir_todo=True):
    """
    Pide al usuario un tipo de producto.
    Añadimos el argumento permitir_todo porque en la nube de palabras no es una opcion.
    """
    opciones = {
        '1': 'Digital Music',
        '2': 'Musical Instruments',
        '3': 'Toys and Games',
        '4': 'Video Games'
    }

    print(f'\nSelecciona el tipo de producto:')
    for clave, valor in opciones.items():
        print(f'{clave}. {valor}')
    
    if permitir_todo:
        print('5. Todo')

    opcion = input('Opcion: ').strip()

    if opcion in opciones:
        return opciones[opcion]

    if permitir_todo and opcion == '5':
        return 'Todo'
    
    print('Opcion no valida.')
    return None


# Consultas auxiliares.
def construccion_filtro_tipo_producto_sql(product_type_name):
    """
    Devuelve la clausula SQL y los parametros segun el tipo de producto.
    """
    if product_type_name == 'Todo':
        return '', []
    
    clausula = """
            WHERE pt.product_type_name = %s
            """
    return clausula, [product_type_name]


def construccion_join_reviews_products_types():
    """
    Devuelve el bloque JOIN reutilizable para varias consultas.
    """
    return """
        FROM reviews r
        JOIN products p ON r.id_product = p.id_product
        JOIN product_types pt ON p.id_product_type = pt.id_product_type
        """

# Plots.
# 1
def mostrar_reviews_por_anio():
    """
    Muestra un histograma con el numero de reviews por año.
    """
    product_type_name = pedir_tipo_producto(permitir_todo=True)
    if product_type_name is None:
        return
    
    conexion = get_mysql_connection()

    try:
        join_sql = construccion_join_reviews_products_types()
        filtro_sql, params = construccion_filtro_tipo_producto_sql(product_type_name)

        sql = f"""
            SELECT YEAR(r.review_date) AS anio, COUNT(*) AS total_reviews
            {join_sql}
            {filtro_sql}
            GROUP BY YEAR(r.review_date)
            ORDER BY YEAR(r.review_date);
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No hay datos para esa opcion')
            return
        
        anios = [fila[0] for fila in resultados]
        conteos = [fila[1] for fila in resultados]

        plt.figure(figsize=(10, 6))
        plt.bar(anios, conteos)
        plt.title(f'Reviews por año - {product_type_name}')
        plt.xlabel('Año')
        plt.ylabel('Numero de reviews')
        plt.xticks(anios, rotation=45)
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()


# 2
def mostrar_popularidad_articulos():
    """
    Muestra una curva de articulos ordenados de mayor a menor popularidad.
    """
    product_type_name = pedir_tipo_producto(permitir_todo=True)
    if product_type_name is None:
        return
    
    conexion = get_mysql_connection()

    try:
        join_sql = construccion_join_reviews_products_types()
        filtro_sql, params = construccion_filtro_tipo_producto_sql(product_type_name)

        sql = f"""
            SELECT p.asin, COUNT(*) AS total_reviews
            {join_sql}
            {filtro_sql}
            GROUP BY p.id_product, p.asin
            ORDER BY total_reviews DESC;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No hay datos para esa opcion')
            return
        
        conteos = [fila[1] for fila in resultados]

        if len(conteos) > 1000:     # Tomamos 1000 como limite para los mas relevantes.
            conteos = conteos[:1000]
        
        posiciones = list(range(1, len(conteos) + 1))

        plt.figure(figsize=(10, 6))
        plt.plot(posiciones, conteos)
        plt.title(f'Evolucion de la popularidad de los articulos - {product_type_name}')
        plt.xlabel('Articulos ordenados por popularidad')
        plt.ylabel('Numero de reviews')
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()


# 3
def mostrar_histograma_por_nota():
    """
    Muestra un histograma del numero de reviews por nota.
    Permite filtrar por tipo de producto o por articulo individual.
    """
    print(f'\nSelecciona el modo de consulta:')
    print('1. Por tipo de producto / todo')
    print('2. Por articulo individual (asin)')

    opcion = input('Opcion: ').strip()
    conexion = get_mysql_connection()

    try:
        join_sql = construccion_join_reviews_products_types()

        if opcion == '1':
            product_type_name = pedir_tipo_producto(permitir_todo=True)
            if product_type_name is None:
                return
            
            filtro_sql, params = construccion_filtro_tipo_producto_sql(product_type_name)

            sql = f"""
                SELECT r.overall, COUNT(*) AS total_reviews
                {join_sql}
                {filtro_sql}
                GROUP BY r.overall
                ORDER BY r.overall;
                """
            titulo = f'Histograma por nota - {product_type_name}'
        
        elif opcion == '2':
            asin = input('Introduce el asin del articulo: ').strip()
            if asin == '':
                print('El asin no puede estar vacio')
                return
            
            sql = f"""
                SELECT r.overall, COUNT(*) AS total_reviews
                {join_sql}
                WHERE p.asin = %s
                GROUP BY r.overall
                ORDER BY r.overall;
                """
            params = [asin]
            titulo = f'Histograma por nota del articulo {asin}'

        else:
            print('Opcion no valida')
            return

        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No existen datos para ese criterio de busqueda')
            return
        
        notas = [fila[0] for fila in resultados]
        conteos = [fila[1] for fila in resultados]

        plt.figure(figsize=(8, 6))
        plt.bar(notas, conteos)
        plt.title(titulo)
        plt.xlabel('Nota')
        plt.ylabel('Numero de reviews')
        plt.xticks([1, 2, 3, 4, 5])
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()

# 4
def mostrar_evolucion_reviews_tiempo():
    """
    Muestra la evolucion acumulada de reviews a lo largo del tiempo.
    Se pide para cada tipo de producto o para todos.
    """
    product_type_name = pedir_tipo_producto(permitir_todo=True)
    if product_type_name is None:
        return
    
    conexion = get_mysql_connection()

    try:
        join_sql = construccion_join_reviews_products_types()
        filtro_sql, params = construccion_filtro_tipo_producto_sql(product_type_name)

        sql = f"""
            SELECT r.unix_review_time
            {join_sql}
            {filtro_sql}
            ORDER BY r.unix_review_time;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No hay datos para esa opcion')
            return
        
        tiempos = [fila[0] for fila in resultados]
        acumulado = list(range(1, len(tiempos) + 1))

        plt.figure(figsize=(10, 6))
        plt.plot(tiempos, acumulado)
        plt.title(f'Evolucion de las reviews a lo largo del tiempo - {product_type_name}')
        plt.xlabel('Tiempo')
        plt.ylabel('Numero acumulado de reviews')
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()


# 5
def mostrar_histograma_reviews_usuario():
    """
    Muestra un histograma donde:
    - eje x: numero de reviews
    - eje y: numero de usuarios con esa cantidad de reviews
    """
    conexion = get_mysql_connection()

    try:
        sql = """
            SELECT id_user, COUNT(*) AS total_reviews
            FROM reviews
            GROUP BY id_user;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No hay datos disponibles')
            return
        
        reviews_por_usuario = [fila[1] for fila in resultados]

        plt.figure(figsize=(10, 6))
        plt.hist(reviews_por_usuario, bins=700)
        plt.title('Histograma de reviews por usuario')
        plt.xlabel('Numero de reviews')
        plt.ylabel('Numero de usuarios')
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()

# 6
def limpiar_palabras(texto:str):
    """
    Limpia el texto y devuelve una lista de palabras validas.
    Solo conserva palabras de longitud minima.
    """
    texto = texto.lower()
    palabras = re.findall(r'\b[a-zA-Z]+\b', texto)

    palabras_validas = []
    for palabra in palabras:
        if len(palabra) >= 4:       # No conectores.
            palabras_validas.append(palabra)
    
    return palabras_validas

def mostrar_nube_palabras():
    """
    Genera una nube de palabras a partir del campo summary para
    cada categoria."""
    product_type_name = pedir_tipo_producto(permitir_todo=False)
    if product_type_name is None:
        return
    
    db = get_mongo_database(MONGO_DATABASE)
    collection = db[MONGO_COLLECTION]

    filtro = {'product_type': product_type_name}
    proyeccion = {'review_document.summary': 1, '_id': 0}

    textos = []

    for doc in collection.find(filtro, proyeccion):
        summary = doc.get('review_document', {}).get('summary')
        if summary is not None:
            textos.append(summary)

    if not textos:
        print('No hay summaries para esa categoria')
        return
    
    texto_total = ' '.join(textos)
    palabras = limpiar_palabras(texto_total)

    if not palabras:
        print('No hay suficientes palabras validas para generar la nube')
        return
    
    texto_limpio = ' '.join(palabras)
    
    nube = WordCloud(width=1000, height=500, background_color='white').generate(texto_limpio)
    # Nota de autoria: tutorial de https://www.datacamp.com/es/tutorial/wordcloud-python

    plt.figure(figsize=(12, 6))
    plt.imshow(nube, interpolation='bilinear') # Mismo tutorial.
    plt.axis('off')
    plt.title(f'Nube de palabras - {product_type_name}')
    plt.show()

# Opcional: 7
def mostrar_media_nota_por_categoria():
    """
    Media de la nota por categoria de producto.
    """
    conexion = get_mysql_connection()

    try:
        sql = """
            SELECT pt.product_type_name, AVG(r.overall) AS media_nota
            FROM reviews r
            JOIN products p ON r.id_product = p.id_product
            JOIN product_types pt ON p.id_product_type = pt.id_product_type
            GROUP BY pt.product_type_name
            ORDER BY pt.product_type_name;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            resultados = cursor.fetchall()
        
        if not resultados:
            print('No hay datos disponibles')
            return
        
        categorias = [fila[0] for fila in resultados]
        medias = [float(fila[1]) for fila in resultados]

        plt.figure(figsize=(10, 6))
        plt.bar(categorias, medias)
        plt.title('Media de nota por categoria')
        plt.xlabel('Categoria')
        plt.ylabel('Media de overall')
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.show()

    finally:
        conexion.close()


def main():
    """
    Ejecutamos el menu hasta que el usuario seleccione salir.
    """
    while True:
        mostrar_menu()
        opcion = input('Selecciona una opcion: ').strip()
        
        if opcion == '1':
            mostrar_reviews_por_anio()
        elif opcion == '2':
            mostrar_popularidad_articulos()
        elif opcion == '3':
            mostrar_histograma_por_nota()
        elif opcion == '4':
            mostrar_evolucion_reviews_tiempo()
        elif opcion == '5':
            mostrar_histograma_reviews_usuario()
        elif opcion == '6':
            mostrar_nube_palabras()
        elif opcion == '7':
            mostrar_media_nota_por_categoria()
        elif opcion == '8':
            print('Saliendo del programa...')
            break
        else:
            print('Opcion no valida. Intentalo de nuevo.')

if __name__ == '__main__':
    main()