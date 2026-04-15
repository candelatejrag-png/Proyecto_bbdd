"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

Genera ficheros CSV para crear 3 visualizaciones en Tableau:
    1. Reviews por año
    2. Popularidad de articulos
    3. Media de nota por categoria
"""

import csv
import os
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
def asegurar_directorio_exports():
    """
    Crea el directorio de exportacion si no existe.
    """
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR)

def escribir_csv(nombre_fichero: str, cabecera: list[str], filas:list[tuple]):
    """
    Escribe un CSV en el directorio de exportacion.
    """
    ruta = os.path.join(EXPORTS_DIR, nombre_fichero)

    with open(ruta, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(cabecera)
        writer.writerows(filas)

    print(f'CSV generado: {ruta}')


# Export 1.
def exportar_reviews_por_anio():
    """
    Exporta un CSV con numero de reviews por año y categoria.
    """
    conexion = get_mysql_connection()

    try:
        sql = """
            SELECT pt.product_type_name, YEAR(r.review_date) AS anio, COUNT(*) AS total_reviews
            FROM reviews r
            JOIN products p ON r.id_product = p.id_product 
            JOIN product_types pt ON p.id_product_type = pt.id_product_type
            WHERE r.review_date IS NOT NULL
            GROUP BY pt.product_type_name, YEAR(r.review_date)
            ORDER BY pt.product_type_name, YEAR(r.review_date);
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            filas = cursor.fetchall()
        
        escribir_csv('reviews_por_anio.csv', ['product_type_name', 'anio', 'total_reviews'], filas)
    
    finally:
        conexion.close()


# Export 2.
def exportar_popularidad_articulos():
    """
    Exporta un CSV con popularidad de articulos por categoria.
    Hemos limitado el numero de articulo exportados por categoria para que 
    el fichero no sea demasiado grande.
    """
    conexion = get_mysql_connection()

    try:
        sql = """
            SELECT pt.product_type_name, p.asin, COUNT(*) AS total_reviews
            FROM reviews r
            JOIN products p ON r.id_product = p.id_product 
            JOIN product_types pt ON p.id_product_type = pt.id_product_type
            GROUP BY pt.product_type_name, p.id_product, p.asin
            ORDER BY pt.product_type_name, total_reviews DESC;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            resultados = cursor.fetchall()
        
        # Para que el fichero no se haga enorme, cortamos por categoria.
        filas_filtradas = []
        contador_por_categoria = {}

        for fila in resultados:
            categoria = fila[0]

            if categoria not in contador_por_categoria:
                contador_por_categoria[categoria] = 0
            
            if contador_por_categoria[categoria] < TP_N_POPULARIDAD_EXPORT:
                filas_filtradas.append(fila)
                contador_por_categoria[categoria] += 1

        escribir_csv('popularidad_articulos.csv', ['product_type_name', 'asin', 'total_reviews'], filas_filtradas)
    
    finally:
        conexion.close()


# Export 3.
def exportar_histograma_por_nota():
    """
    Exporta un CSV con numero de reviews por nota y categoria
    """
    conexion = get_mysql_connection()

    try:
        sql = """
            SELECT pt.product_type_name, r.overall, COUNT(*) AS total_reviews
            FROM reviews r
            JOIN products p ON r.id_product = p.id_product 
            JOIN product_types pt ON p.id_product_type = pt.id_product_type
            WHERE r.overall IS NOT NULL
            GROUP BY pt.product_type_name, r.overall
            ORDER BY pt.product_type_name, r.overall;
            """
        
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            filas = cursor.fetchall()
        
        escribir_csv('histograma_por_nota.csv', ['product_type_name', 'overall', 'total_reviews'], filas)
    
    finally:
        conexion.close()   


def main():
    """
    Genera todos los CSV necesarios para Tableau.
    """ 
    asegurar_directorio_exports()

    print('Generando CSV para visualizacion externa...')
    exportar_reviews_por_anio()
    exportar_popularidad_articulos()
    exportar_histograma_por_nota()
    print('Proceso completado.')


if __name__ == '__main__':
    main()