"""
Nombres:
    - Gabriela Romero Martin
    - Candela Tejedo Raga

Acceso y visualizacion de los datos por interfaz desarrollada con customtkinter.
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

# Importamos las librerías necesarias
import re
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import matplotlib.pyplot as plt
import pymysql
from pymongo import MongoClient
from pymongo.database import Database
from wordcloud import WordCloud
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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

# Configuramos el aspecto general de la página
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')
# Colores a emplear
BG_DARK = "#0f0f14"
BG_CARD = "#1a1a24"
BG_PANEL = "#13131c"
ACCENT = "#7c6af7"
ACCENT_2 = "#f77c6a"
TEXT_MAIN = "#e8e6f0"
TEXT_MUTED = "#7a7892"
BUTTON_MENU= '#5a4fd4'
BORDER = "#2a2a3d"
BAR1 = '#6af7c2'
BAR2 = '#f7d96a'

# Lista de colores
PRODUCT_TYPES = ['Digital Music', 'Musical Instruments', 'Toys and Games', 'Video Games']

# -------------------------------------
# Establecemos las conexiones
# -------------------------------------

def get_mysql_connection(): 
    """
    Establece la conexión con MySQL. 
    """
    return pymysql.connect(
        host=MYSQL_HOST, 
        user=MYSQL_USER, 
        password=MYSQL_PASSWORD, 
        port=MYSQL_PORT, 
        database=MYSQL_DATABASE,
    )

def get_mongo_database(db_name: str) -> Database:
    """
    Establece la conexión con MongoDB.
    """ 
    client = MongoClient(MONGO_CONNECTION_STRING)
    return client[db_name]

# -------------------------------------
# Consultas comunes
# -------------------------------------

def join_block(): 
    '''
    Consulta que aparece en varias ocasiones, la almecenamos en su propia función para que el código quede más ordenado y limpio.
    '''
    return '''
        FROM REVIEWS r
        JOIN products p ON r.id_product = p.id_product
        JOIN product_types pt ON p.id_product_type = pt.id_product_type
    '''
def where_block(product_type: str): 
    """
    Consulta que aparece en varias ocasiones, la almacenamos en su propia función para que el código quede más ordenado y limpio. 
    Distingue entre dos casos: 
        - Si recibe 'Todo' entonces no filtra nada. 
        - Si recibe una categoría concreta filtra por esta devolviendo además la lista de parámetos.
    """
    if product_type == 'Todo': 
        return '', []
    return 'WHERE pt.product_type_name = %s', [product_type]

# -------------------------------------
# Datos y gráficas
# -------------------------------------

def apply_style(fig: Figure, ax: Axes): 
    """
    Aplica el estilo oscuro (estilo elegido para el fondo) a cualquier figura recibida por argumentos.
    """
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MAIN)
    ax.title.set_color(TEXT_MAIN)
    for spine in ax.spines.values(): 
        spine.set_edgecolor(BORDER)

def plot_reviews_x_anio(product_type: str): 
    """
    Genera una gráfica de barras con el número de reviews por año a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta_join = join_block()
    consulta_where, params = where_block(product_type)
    consulta = f'''
                SELECT YEAR(r.review_date) anio, COUNT(*) total
                {consulta_join}
                {consulta_where}
                GROUP BY anio 
                ORDER BY anio
    '''
    # Establecemos la conexión y obtenemos la información
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor: 
            cursor.execute(consulta, params)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Alamcenamos los resultados
    if not result: 
        return None
    anios = [res[0] for res in result]
    conteos = [res[1] for res in result]
    # Graficamos
    fig, ax = plt.subplots(figsize=(9,5))
    ax.bar(anios, conteos, color=ACCENT, width=0.6)
    ax.set_xlabel('Año')
    ax.set_ylabel('Número de reviews')
    ax.set_xticks(anios)
    ax.tick_params(axis='x', rotation=45)
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_popu_articulos(product_type: str): 
    """
    Representa cuántas reviews tiene cada artículo, ordenandolos por popularidad a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta_join = join_block()
    consulta_where, params = where_block(product_type)
    consulta = f'''
                SELECT p.asin, COUNT(*) total
                {consulta_join}
                {consulta_where}
                GROUP BY p.id_product, p.asin
                ORDER BY total DESC
                '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor:
            cursor.execute(consulta, params)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos los resultados
    if not result: 
        return None
    conteos = [res[1] for res in result]
    # Graficamos
    fig, ax = plt.subplots(figsize=(9,5))
    ax.plot(range(1, len(conteos)+1), conteos, color=ACCENT_2, linewidth=1.5)
    ax.set_title(f'Popularidad de artículos: {product_type}')
    ax.set_xlabel('Artículos')
    ax.set_ylabel('Número de reviews')
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_hist_nota_tipo(product_type): 
    """
    Representa cuántas reviews hay de cada nota (del 1 al 5) para una categoría o para todo a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta_join = join_block()
    consulta_where, params = where_block(product_type)
    consulta = f'''
                SELECT r.overall, COUNT(*)
                {consulta_join}
                {consulta_where}
                GROUP BY r.overall
                ORDER BY r.overall
                '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor:
            cursor.execute(consulta, params)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos los resultados
    if not result: 
        return None
    notas = [res[0] for res in result]
    conteos = [res[1] for res in result]
    # Graficamos
    fig, ax = plt.subplots(figsize=(9,5))
    ax.bar(notas, conteos, color=ACCENT, width=0.5)
    ax.set_title(f'Distribución de notas: {product_type}')
    ax.set_xlabel('Nota')
    ax.set_ylabel('Número de reviews')
    ax.set_xticks([1,2,3,4,5])
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_hist_nota_asin(asin): 
    """
    Representa cuántas reviews hay de cada nota (del 1 al 5) para un artículo específico a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta_join = join_block()
    consulta = f'''
                SELECT r.overall, COUNT(*)
                {consulta_join}
                WHERE p.asin = %s
                GROUP BY r.overall
                ORDER BY r.overall
                '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor:
            cursor.execute(consulta, [asin])
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos los resultados
    if not result: 
        return None
    notas = [res[0] for res in result]
    conteos = [res[1] for res in result]
    # Graficamos
    fig, ax = plt.subplots(figsize=(7,5))
    ax.bar(notas, conteos, color=ACCENT_2, width=0.5)
    ax.set_title(f'Notas de artículo: {asin}')
    ax.set_xlabel('Nota')
    ax.set_ylabel('Número de reviews')
    ax.set_xticks([1,2,3,4,5])
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_evol_tiempo(product_type): 
    """
    Muestra la evolución acumulada de reviews a lo tardo del tiempo a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta_join = join_block()
    consulta_where, params = where_block(product_type)
    consulta = f'''
                SELECT r.unix_review_time
                {consulta_join}
                {consulta_where}
                ORDER BY r.unix_review_time
                '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor:
            cursor.execute(consulta, params)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos los resultados
    if not result: 
        return None
    tiempos = [res[0] for res in result]
    acumulados = list(range(1, len(tiempos)+1))
    # Graficamos
    fig, ax = plt.subplots(figsize=(9,5))
    ax.plot(tiempos, acumulados, color=ACCENT, linewidth=1.5)
    ax.set_title(f'Evolución acumulada de reviews: {product_type}')
    ax.set_xlabel('Tiempo unix')
    ax.set_ylabel('Reviews acumuladas')
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def plot_rev_x_user(): 
    """
    Muestra cómo se distribuye el número de reviews por usuario a partir de la información recopilada por consultas SQL. 
    """
    # Creamos las consultas
    consulta = f'''
                SELECT id_user, COUNT(*)
                FROM reviews
                GROUP BY id_user
                '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor:
            cursor.execute(consulta)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos los resultados
    if not result: 
        return None
    conteos = [res[1] for res in result]
    # Graficamos
    fig, ax = plt.subplots(figsize=(9,5))
    ax.hist(conteos, bins=700, color=ACCENT)
    ax.set_title(f'Histograma de reviews por usuario')
    ax.set_xlabel('Número de reviews')
    ax.set_ylabel('Número de usuarios')
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

def limpiar_palabras(texto: str): 
    """
    Limpia el texto para preparar la nube de palabras.
    """
    palabras = re.findall(r'\b[a-zA-Z]+\b', texto.lower())
    return [p for p in palabras if len(p) >= 4]

def plot_nube(product_type): 
    """
    Crea la nube de palabras con los texto almacenados en summary de los reviews de una categoría a partir de la información recopilada con consultas a MongoDB. 
    """
    # Establecemos la conexion
    db = get_mongo_database(MONGO_DATABASE)
    colec = db[MONGO_COLLECTION]
    # Obtenemos la información
    textos = [
        doc.get('review_document', {}).get('summary', '')
        for doc in colec.find({'product_type': product_type}, {'review_document.summary': 1, '_id': 0})
        if doc.get('review_document', {}).get('summary')
    ]
    # Almacenamos la información limpia
    if not textos: 
        return None
    palabras = limpiar_palabras(' '.join(textos))
    if not palabras: 
        return None
    # Graficamos
    nube = WordCloud(width=1000, height=480, background_color=BG_CARD, colormap='RdPu').generate(' '.join(palabras))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(nube, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(f'Nube de palabras: {product_type}', color=TEXT_MAIN, fontsize=13)
    fig.patch.set_facecolor(BG_CARD)
    fig.tight_layout()
    return fig

def plot_media_nota_cat(): 
    """
    Compara la nota media de cada categoría de producto a partir de la información recopilada con consultas a MongoDB. 
    """
    # Creamos la consulta
    consulta = '''
                SELECT pt.product_type_name, AVG(r.overall)
                FROM reviews r
                JOIN products p ON r.id_product = p.id_product
                JOIN product_types pt ON p.id_product_type = pt.id_product_type
                GROUP BY pt.product_type_name
                ORDER BY pt.product_type_name
            '''
    # Establecemos la conexión
    conexion = get_mysql_connection()
    try: 
        with conexion.cursor() as cursor: 
            cursor.execute(consulta)
            result = cursor.fetchall()
    finally: 
        conexion.close()
    # Almacenamos la información
    if not result: 
        return None
    categ = [res[0] for res in result]
    medias = [float(res[1]) for res in result]
    fig, ax = plt.subplots(figsize=(8,5))
    bars = ax.bar(categ, medias, color=[ACCENT, ACCENT_2, BAR1, BAR2])
    ax.set_title(f'Media de nota por categoría')
    ax.set_xlabel('Categoría')
    ax.set_ylabel('Media (overall)')
    ax.set_ylim(0, 5.5)
    ax.tick_params(axis='x', rotation=15)
    # Nueva funcionalidad: mostramos las medias encima de cada barra formateadas a dos decimales
    for bar, val in zip(bars, medias): 
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.07, f"{val:.2f}", ha="center", va="bottom", color=TEXT_MAIN, fontsize=10)
    apply_style(fig, ax)
    fig.tight_layout()
    return fig

# -------------------------------------
# Componentes de la web reutilizables
# -------------------------------------

class OptionRow(ctk.CTkFrame): 
    """Clase para crear una fila de la interfaz con una etiqueta a la izquierda junto con un menú desplegable a la derecha. """
    def __init__(self, master, label, values, **kwargs): 
        # Primero tenemos que inicializar el contenedor base sobre el que se apoya la clase
        super().__init__(master, fg_color='transparent', **kwargs)
        # Creamos la fila
        # Creamos la etiqueta
        ctk.CTkLabel(self, text=label, text_color=TEXT_MUTED, width=130, anchor='w').pack(side='left')
        self.var = ctk.StringVar(value=values[0])
        # Creamos el Menú
        ctk.CTkOptionMenu(self, values=values, variable=self.var, fg_color=BG_PANEL, button_color=ACCENT, button_hover_color=None, dropdown_fg_color=BG_CARD, text_color=TEXT_MAIN, width=220).pack(side='left', padx=8)

    # Propiedad de la clase, se usa como atributo
    @property
    def value(self): 
        return self.var.get()
    
class EntryRow(ctk.CTkFrame): 
    """Clase para crear un fila de la interfaz con una etiqueta a la izquierda junto con una caja para introducir texto a la derecha.  """
    def __init__(self, master, label, placeholder='', **kwargs): 
        # Primero tenemos que iniciar el contenedor base sobre el que se apoya la clase
        super().__init__(master, fg_color='transparent', **kwargs)
        # Creamos la fila
        # Creamos la etiqueta
        ctk.CTkLabel(self, text=label, text_color=TEXT_MUTED, width=130, anchor='w').pack(side='left')
        # Creamos la caja de texto
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=220, fg_color=BG_PANEL, border_color=BORDER, text_color=TEXT_MAIN)
        self.entry.pack(side='left', padx=8)
    
    # Propiedad de la clase, se usa como atributo
    @property
    def value(self): 
        return self.entry.get().strip()
    
# -------------------------------------
# Panel de las gráficas
# -------------------------------------

class ChartPanel(ctk.CTkFrame): 
    """Clase que muestra las figuras creadas con matplotlib en la interfaz de tkinter"""
    def __init__(self, master, **kwargs): 
        # Primero tenemos que iniciar el contenedor base sobre el que se apoya la clase
        super().__init__(master, fg_color=BG_CARD, corner_radius=12, **kwargs)
        self._graf_canvas = None     # Guardamos internamente el canvas donde se guarda la figura

    def show(self, fig): 
        """Muestra la gráfica recibida por argumentos"""
        # Si ya hay una gráfica la eliminamos
        if self._graf_canvas: 
            self._graf_canvas.get_tk_widget().destroy()
        # Creamos una nueva y la almacenamos
        self._graf_canvas = FigureCanvasTkAgg(fig, master=self)
        self._graf_canvas.draw()
        self._graf_canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def clear(self): 
        """Elimina la gráfica en el canvas si existe y lo reestablece a None."""
        if self._graf_canvas: 
            self._graf_canvas.get_tk_widget().destroy()
            self._graf_canvas = None

# -------------------------------------
# Vistas: general
# -------------------------------------

class BaseView(ctk.CTkFrame): 
    """Clase que crea el frame base con el área de control y navegación y el área de representación de gráficas."""
    TITLE = 'Vista'
    def __init__(self, master, **kwargs): 
        super().__init__(master,fg_color=BG_DARK, **kwargs)
        # Creamos la cabecera
        header = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=56)
        header.pack(fill='x')
        ctk.CTkLabel(header, text=self.TITLE, font=ctk.CTkFont(size=16, weight='bold'), text_color=TEXT_MAIN).pack(side='left', padx=20, pady=12)
        # Panel de controles y navegación
        self.ctrl = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=10, border_width=1, border_color=BORDER)
        self.ctrl.pack(fill='x', padx=18, pady=(14, 0))
        # Área de la gráfica
        self.graf = ChartPanel(self)
        self.graf.pack(fill='both', expand=True, padx=18, pady=14)

    def button(self, parent, text, com): 
        return ctk.CTkButton(parent, text=text, command=com, fg_color=ACCENT, hover_color="#5a4fd4", text_color='white', corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"))
    
    def error(self, mesage): 
        """Controla el prosible error de adquisición de los datos."""
        messagebox.showwarning('Sin datos', mesage, parent=self)
    
    def run(self, fun, *args): 
        """Ejecuta una función recibida por argumentos (la que crea la gráfica) y muestra la gráfica o, en caso de error, un mensaje."""
        try: 
            fig=fun(*args)
        # Controlamos el error
        except Exception as error: 
            self.error(str(error))
            return
        if fig is None: 
            self.error('No hay datos para los filtros seleccionados.')
            return 
        # Mostramos la figura
        self.graf.show(fig)
    
# -------------------------------------
# Vistas de cada opción del menú
# -------------------------------------

# 1. reviews por año
class view1(BaseView):
    TITLE = '1. Histograma de reviews por año'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self._opt = OptionRow(row, "Categoría:", PRODUCT_TYPES + ["Todo"])
        self._opt.pack(side="left")
        self.button(row, "Generar", self._go).pack(side="left", padx=14)
 
    def _go(self):
        self.run(plot_reviews_x_anio, self._opt.value)
    
# 2. Popularidad de artículos
class view2(BaseView): 
    TITLE = '2. Evolución de la popularidad de los artículos'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self._opt = OptionRow(row, "Categoría:", PRODUCT_TYPES + ["Todo"])
        self._opt.pack(side="left")
        self.button(row, "Generar", self._go).pack(side="left", padx=14)
 
    def _go(self):
        self.run(plot_popu_articulos, self._opt.value)

# 3. Histograma por nota
class view3(BaseView): 
    TITLE = '3. Histograma por nota'
    def __init__(self, master, **kwargs): 
        super().__init__(master, **kwargs)
        # El usuario selecciona el tipo de producto
        mode_row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        mode_row.pack(padx=16, pady=(12, 4))
        ctk.CTkLabel(mode_row, text="Modo:", text_color=TEXT_MUTED, width=130, anchor="w").pack(side="left")
        self._mode = ctk.StringVar(value="tipo")
        ctk.CTkRadioButton(mode_row, text="Por categoría", variable=self._mode, value="tipo", text_color=TEXT_MAIN, fg_color=ACCENT).pack(side="left", padx=6)
        ctk.CTkRadioButton(mode_row, text="Por ASIN", variable=self._mode, value="asin", text_color=TEXT_MAIN, fg_color=ACCENT).pack(side="left", padx=6)
 
        filter_row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        filter_row.pack(padx=16, pady=(4, 12))
        self._opt  = OptionRow(filter_row, "Categoría:", PRODUCT_TYPES + ["Todo"])
        self._opt.pack(side="left")
        self._asin = EntryRow(filter_row, "ASIN:", placeholder="p.ej. B001234")
        self._asin.pack(side="left", padx=12)
        self.button(filter_row, "Generar", self._go).pack(side="left", padx=14)
 
    def _go(self):
        if self._mode.get() == "tipo":
            self.run(plot_hist_nota_tipo, self._opt.value)
        else:
            asin = self._asin.value
            if not asin:
                self.error("Introduce un ASIN."); return
            self.run(plot_hist_nota_asin, asin)

# 4. Evolución temporal de las reviews
class view4(BaseView): 
    TITLE = '4. Evolución de reviews a lo largo del tiempo'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self._opt = OptionRow(row, "Categoría:", PRODUCT_TYPES + ["Todo"])
        self._opt.pack(side="left")
        self.button(row, "Generar", self._go).pack(side="left", padx=14)
 
    def _go(self):
        self.run(plot_evol_tiempo, self._opt.value)

# 5. Reviews por usuario
class view5(BaseView): 
    TITLE = '5. Histograma de reviews por usuario'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self.button(row, "Generar histograma", self._go).pack()
 
    def _go(self):
        self.run(plot_rev_x_user)

# 6. Nube de palabras
class view6(BaseView): 
    TITLE = '6. Nube de palabras por categoría'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self._opt = OptionRow(row, "Categoría:", PRODUCT_TYPES)
        self._opt.pack(side="left")
        self.button(row, "Generar", self._go).pack(side="left", padx=14)
 
    def _go(self):
        self.run(plot_nube, self._opt.value)

# 7. Media por categoría
class view7(BaseView): 
    TITLE = '7. Media por categoria'
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        row = ctk.CTkFrame(self.ctrl, fg_color="transparent")
        row.pack(padx=16, pady=12)
        self.button(row, "Generar gráfica", self._go).pack()
 
    def _go(self):
        self.run(plot_media_nota_cat)

# -------------------------------------
# Pantalla inicial
# -------------------------------------

OPS_MENU = [
    ('1. Reviews por año', view1),
    ('2. Popularidad artículos', view2),
    ('3. Histograma por nota', view3),
    ('4. Evolución temporal', view4), 
    ('5. Reviews por usuario', view5),
    ('6. Nube de palabras', view6),
    ('7. Media por categoría', view7)
]

class HomeScreen(ctk.CTkFrame): 
    """Pantalla inicial que se muestra al arrancar"""
    def __init__(self, master, on_select, **kwargs): 
        super().__init__(master, fg_color=BG_DARK, **kwargs)
        # Fondo decorativo
        canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        for i in range(0, 800, 60):
            canvas.create_line(i, 0, i+400, 700, fill="#1c1c2a", width=1)
        # Título
        ctk.CTkLabel(self, text="📊 Panel de Visualización",
                     font=ctk.CTkFont(family="Georgia", size=30, weight="bold"),
                     text_color=TEXT_MAIN).place(relx=0.5, rely=0.12, anchor="center")
        ctk.CTkLabel(self, text="Gabriela Romero Martín · Candela Tejedo Raga",
                     font=ctk.CTkFont(size=12), text_color=TEXT_MUTED
                     ).place(relx=0.5, rely=0.19, anchor="center")
        # Tarjetas de menú
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.place(relx=0.5, rely=0.57, anchor="center")
        for idx, (label, view_cls) in enumerate(OPS_MENU):
            col = idx % 4
            row = idx // 4
            card = ctk.CTkButton(grid, text=label, width=190, height=70,
                fg_color=BG_CARD, hover_color=ACCENT,
                text_color=TEXT_MAIN, border_width=1, border_color=BORDER,
                corner_radius=10, font=ctk.CTkFont(size=12),
                command=lambda vc=view_cls: on_select(vc),
            )
            card.grid(row=row, column=col, padx=10, pady=10)

class SideBar(ctk.CTkFrame): 
    """Barra lateral para navegar por la interfaz."""
    def __init__(self, master, on_select, on_home, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=0, width=210, **kwargs)
        self.pack_propagate(False)
        # Logo
        ctk.CTkLabel(self, text="📊", font=ctk.CTkFont(size=28)).pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Visualizaciones",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT_MAIN).pack()
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=16, pady=12)
        # Botón inicio
        ctk.CTkButton(self, text="⌂  Inicio", command=on_home,
                      fg_color="transparent", hover_color="#2a2a3d",
                      text_color=TEXT_MUTED, anchor="w",
                      font=ctk.CTkFont(size=12)).pack(fill="x", padx=10, pady=2)
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=16, pady=8)
        # Botones de vistas
        for label, view_cls in OPS_MENU:
            btn = ctk.CTkButton(
                self, text=label,
                command=lambda vc=view_cls: on_select(vc),
                fg_color="transparent", hover_color="#2a2a3d",
                text_color=TEXT_MUTED, anchor="w",
                font=ctk.CTkFont(size=11),
            )
            btn.pack(fill="x", padx=10, pady=2)
        # Botón salir
        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(self, text="✕  Salir", command=master.quit,
                      fg_color="#3d1a1a", hover_color="#7a1a1a",
                      text_color="#f77c7c",
                      font=ctk.CTkFont(size=12)).pack(fill="x", padx=10, pady=4)

# -------------------------------------
# Ventana principal de la app
# -------------------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Panel de Visualización")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(fg_color=BG_DARK)
 
        self._current_view = None
 
        # Layout: sidebar | contenido
        self._sidebar = SideBar(self, on_select=self._show_view, on_home=self._show_home)
        self._sidebar.pack(side="left", fill="y")
 
        self._content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)
 
        self._show_home()
 
    def _clear_content(self):
        for widget in self._content.winfo_children():
            widget.destroy()
        self._current_view = None
 
    def _show_home(self):
        self._clear_content()
        HomeScreen(self._content, on_select=self._show_view).pack(fill="both", expand=True)
 
    def _show_view(self, view_cls):
        self._clear_content()
        self._current_view = view_cls(self._content)
        self._current_view.pack(fill="both", expand=True)

# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__': 
    app = App()
    app.mainloop()