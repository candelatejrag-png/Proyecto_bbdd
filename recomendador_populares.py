"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

Dado un reviewerID original y un tipo de producto,
devuelve los 10 articulos mas populares que el usuario no ha consumido.
"""

import pymysql

from configuracion import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    EXPORTS_DIR,
    TP_N_POPULARIDAD_EXPORT
)


# Conexion.
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


# Funciones auxiliares.
def pedir_tipo_producto():
    """
    Pide al usuario un tipo de producto.
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

    opcion = input('Opcion: ').strip()

    if opcion in opciones:
        return opciones[opcion]

    print('Opcion no valida.')
    return None !! quiza poner para que siga preguntando hasta funcionar


# Recomendacion.
def recomendar_top_10_no_consumidos(reviewer_id_original:str, product_type_name:str):
    """
    Devuelve los 10 articulos mas populares de una categoria
    que el usuario no ha consumido.
    """
    conexion = get_mysql_connection()

    try: 
        # Primero comprobamos is el usuario existe.
        sql_usuario = """
                    SELECT id_user
                    FROM users
                    WHERE reviewer_id_original = %s;
                    """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql_usuario, [reviewer_id_original])
            fila_usuario = cursor.fetchone()
        
        if fila_usuario is None:
            print('El usuario no existe en la base de datos.')
            return
        
        id_user = fila_usuario[0]

        sql_recomendacion = """
                        SELECT p.asin, COUNT(*) AS total_reviews
                        FROM reviews r
                        JOIN products p ON r.id_product = p.id_product
                        JOIN product_types pt ON p.id_product_type = pt.id_product_type
                        WHERE pt.product_type_name = %s
                            AND p.id_product NOT IN (SELECT DISTINCT r2.id_product
                                                     FROM reviews r2
                                                     WHERE r2.id_user = %s) 
                        GROUP BY p.id_product, p.asin
                        ORDER BY total_reviews DESC
                        LIMIT 10;
                        """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql_recomendacion, [product_type_name, id_user])
            resultados = cursor.fetchall()

        if not resultados:
            print('No hay recomendaciones disponibles para este usuario y categoria')
            return
        
        print(f'\nTop 10 articulos recomendados no consumidos:')
        print(f'Usuario: {reviewer_id_original}')
        print(f'Tipo de producto: {product_type_name}\n')

        for i, fila in enumerate(resultados, start=1):
            asin = fila[0]
            total_reviews = fila[1]
            print(f'{i}. ASIN:{asin} | Popularidad (reviews): {total_reviews}')

    finally:
        conexion.close()


def main():
    """
    Pide los datos al usuario y muestra las recomendaciones.
    """
    reviewer_id_original = input('introduce el reviewerID original: ').strip()
    if reviewer_id_original == '':
        print('El reviewerID no puede estar vacio.')
        return
    
    product_type_name = pedir_tipo_producto()
    if product_type_name is None:
        return
    
    recomendar_top_10_no_consumidos(reviewer_id_original, product_type_name)


if __name__ == '__main__':
    main()