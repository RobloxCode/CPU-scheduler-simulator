"""
Simulador de Planificación de CPU (CPU Scheduler Simulator)
===========================================================
Este script implementa un entorno gráfico interactivo mediante Pygame para simular
y visualizar algoritmos de planificación de procesos en un sistema operativo.

Algoritmos Soportados:
  - SJF (Shortest Job First) - No expulsivo.
  - SRTF (Shortest Remaining Time First) - Expulsivo.
  - Prioridades - No expulsivo.
  - Round Robin - Basado en ráfagas de tiempo (Quantum) configurables.

Estética de la UI: Terminal de control industrial moderno (Tema Catppuccin Mocha).
"""

import pygame
import sys

# Inicializa todos los módulos internos de Pygame (fuentes, video, audio, etc.)
pygame.init()

# ═══════════════════════════════════════════════════════════════════════════════
#  MODELO DE DATOS — CLASE PROCESO
# ═══════════════════════════════════════════════════════════════════════════════

class Proceso:
    """
    Representa un proceso del sistema operativo con sus atributos de planificación.
    Reemplaza las tuplas (id, llegada, rafaga, prioridad) eliminando índices mágicos.
    """
    def __init__(self, id: str, llegada: int, rafaga: int, prioridad: int):
        self.id        = id        # Identificador único del proceso (e.g. "P1")
        self.llegada   = llegada   # Instante en que el proceso ingresa al sistema
        self.rafaga    = rafaga    # Unidades de CPU que requiere para completarse
        self.prioridad = prioridad # Nivel de prioridad (menor número = mayor prioridad)

    def __iter__(self):
        """Permite desempaquetar el proceso como si fuera una tupla (retrocompatibilidad)."""
        return iter((self.id, self.llegada, self.rafaga, self.prioridad))

    def __repr__(self):
        return f"Proceso(id={self.id!r}, llegada={self.llegada}, rafaga={self.rafaga}, prioridad={self.prioridad})"


class SegmentoGantt:
    """
    Representa un bloque de ejecución continua en el diagrama de Gantt.
    Reemplaza las tuplas (proceso_id, inicio, fin, indice_color) por atributos nombrados.
    """
    def __init__(self, proceso_id: str, inicio: int, fin: int, indice_color: int):
        self.proceso_id   = proceso_id   # Identificador del proceso que ejecutó
        self.inicio       = inicio       # Marca de tiempo en que comenzó el bloque
        self.fin          = fin          # Marca de tiempo en que terminó el bloque
        self.indice_color = indice_color # Índice en COLORES_PROCESOS para pintar la barra


class MetricasProceso:
    """
    Almacena los resultados de rendimiento calculados para un proceso individual.
    Reemplaza las tuplas (espera, respuesta, retorno) por atributos nombrados.
    """
    def __init__(self, espera: int, respuesta: int, retorno: int):
        self.espera    = espera    # Tiempo total que el proceso esperó en la cola de listos
        self.respuesta = respuesta # Tiempo desde llegada hasta primera ejecución en CPU
        self.retorno   = retorno   # Tiempo total desde llegada hasta finalización (turnaround)


# ═══════════════════════════════════════════════════════════════════════════════
#  PALETA DE COLORES (Catppuccin Mocha)
# ═══════════════════════════════════════════════════════════════════════════════
PALETA_COLORES = {
    "fondo_principal":              ( 30,  30,  46),
    "fondo_paneles":                ( 36,  36,  54),
    "fondo_componentes":            ( 49,  50,  68),
    "fondo_componentes_enfocados":  ( 58,  60,  78),
    "borde_estandar":               ( 69,  71,  90),
    "borde_destacado":              (137, 180, 250),
    "color_acento_alerta":          (250, 179, 135),
    "color_acento_atenuado":        (180, 120,  80),
    "color_informativo":            (137, 220, 235),
    "color_informativo_oscuro":     ( 60, 110, 120),
    "color_exito":                  (166, 227, 161),
    "color_error":                  (243, 139, 168),
    "color_metrica_retorno":        (203, 166, 247),
    "texto_principal":              (205, 214, 244),
    "texto_secundario":             (108, 112, 134),
    "texto_alto_contraste":         (245, 224, 220),
    "fondo_celda_espera":           ( 49,  50,  68),
    "fila_tabla_par":               ( 36,  36,  54),
    "fila_tabla_impar":             ( 42,  42,  60),
}

COLORES_PROCESOS = [
    (243, 139, 168),
    (137, 180, 250),
    (166, 227, 161),
    (250, 179, 135),
    (203, 166, 247),
    (137, 220, 235),
    (245, 194, 231),
    (249, 226, 175),
]

# ═══════════════════════════════════════════════════════════════════════════════
#  FUENTES TIPOGRÁFICAS
# ═══════════════════════════════════════════════════════════════════════════════
FUENTE_GIGANTE     = pygame.font.SysFont("consolas", 32, bold=True)
FUENTE_TITULO      = pygame.font.SysFont("consolas", 20, bold=True)
FUENTE_ENCABEZADO  = pygame.font.SysFont("consolas", 14, bold=True)
FUENTE_CUERPO      = pygame.font.SysFont("consolas", 13)
FUENTE_MONOESPACIO = pygame.font.SysFont("consolas", 12)
FUENTE_PEQUENA     = pygame.font.SysFont("consolas", 11)
FUENTE_DIMINUTA    = pygame.font.SysFont("consolas", 10)


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES HELPER PARA LOS ALGORITMOS DE PLANIFICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def inicializar_tiempos_restantes(procesos: list[Proceso]) -> dict[str, int]:
    """Construye el diccionario inicial de tiempo restante para cada proceso."""
    tiempos = {}
    for p in procesos:
        tiempos[p.id] = p.rafaga
    return tiempos


def calcular_techo_seguridad(procesos: list[Proceso], margen: int) -> int:
    """Calcula el límite máximo de reloj para evitar bucles infinitos."""
    suma_rafagas = 0
    llegada_maxima = 0
    for p in procesos:
        suma_rafagas += p.rafaga
        if p.llegada > llegada_maxima:
            llegada_maxima = p.llegada
    return suma_rafagas + llegada_maxima + margen


def ordenar_por_llegada(procesos: list[Proceso]) -> list[Proceso]:
    """Devuelve una copia de la lista ordenada de menor a mayor tiempo de llegada."""
    resultado = list(procesos)
    resultado.sort(key=obtener_llegada)
    return resultado


def ordenar_por_llegada_y_prioridad(procesos: list[Proceso]) -> list[Proceso]:
    """Devuelve una copia ordenada primero por llegada y luego por prioridad."""
    resultado = list(procesos)
    resultado.sort(key=obtener_llegada_y_prioridad)
    return resultado


def obtener_llegada(proceso: Proceso) -> int:
    """Criterio de ordenación: tiempo de llegada del proceso."""
    return proceso.llegada


def obtener_llegada_y_prioridad(proceso: Proceso) -> tuple[int, int]:
    """Criterio de ordenación compuesto: llegada primero, luego prioridad."""
    return (proceso.llegada, proceso.prioridad)


def filtrar_disponibles(procesos: list[Proceso], reloj: int, terminados: set[str]) -> list[Proceso]:
    """Devuelve los procesos que ya llegaron y aún no han terminado."""
    disponibles = []
    for p in procesos:
        ya_llego = p.llegada <= reloj
        no_termino = p.id not in terminados
        if ya_llego and no_termino:
            disponibles.append(p)
    return disponibles


def filtrar_recien_llegados(procesos: list[Proceso], reloj: int, terminados: set[str], en_cola: set[str]) -> list[Proceso]:
    """Devuelve los procesos que llegaron pero todavía no están en la cola de listos."""
    recien_llegados = []
    for p in procesos:
        ya_llego = p.llegada <= reloj
        no_termino = p.id not in terminados
        no_esta_en_cola = p.id not in en_cola
        if ya_llego and no_termino and no_esta_en_cola:
            recien_llegados.append(p)
    return recien_llegados


def elegir_menor_rafaga(disponibles: list[Proceso], tiempo_restante: dict[str, int]) -> Proceso:
    """
    Selecciona el proceso con menor tiempo de ráfaga restante.
    Desempata eligiendo al de menor prioridad (número más bajo = más urgente).
    """
    elegido = disponibles[0]
    for candidato in disponibles[1:]:
        rafaga_candidato = tiempo_restante[candidato.id]
        rafaga_elegido   = tiempo_restante[elegido.id]
        if rafaga_candidato < rafaga_elegido:
            elegido = candidato
        elif rafaga_candidato == rafaga_elegido and candidato.prioridad < elegido.prioridad:
            elegido = candidato
    return elegido


def elegir_mayor_prioridad(disponibles: list[Proceso], tiempo_restante: dict[str, int]) -> Proceso:
    """
    Selecciona el proceso con mayor prioridad (número más bajo).
    Desempata eligiendo al de menor ráfaga restante.
    """
    elegido = disponibles[0]
    for candidato in disponibles[1:]:
        if candidato.prioridad < elegido.prioridad:
            elegido = candidato
        elif candidato.prioridad == elegido.prioridad:
            if tiempo_restante[candidato.id] < tiempo_restante[elegido.id]:
                elegido = candidato
    return elegido


def buscar_indice_proceso(procesos: list[Proceso], proceso_id: str) -> int:
    """Devuelve la posición original de un proceso en la lista por su ID."""
    for indice, p in enumerate(procesos):
        if p.id == proceso_id:
            return indice
    return 0


def calcular_metricas(procesos: list[Proceso], fin: dict[str, int], primer_acceso: dict[str, int]) -> dict[str, MetricasProceso]:
    """Calcula tiempos de espera, respuesta y retorno para cada proceso."""
    metricas = {}
    for p in procesos:
        espera    = max(0, fin[p.id] - p.llegada - p.rafaga)
        respuesta = max(0, primer_acceso[p.id] - p.llegada)
        retorno   = espera + p.rafaga
        metricas[p.id] = MetricasProceso(espera, respuesta, retorno)
    return metricas


# ═══════════════════════════════════════════════════════════════════════════════
#  ALGORITMOS DE PLANIFICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def sjf(procesos: list[Proceso]) -> tuple[list[SegmentoGantt], dict[str, MetricasProceso]]:
    """
    Algoritmo Shortest Job First (SJF) — No Expulsivo.
    Selecciona el proceso listo con el menor tiempo de ráfaga sin interrumpir ejecuciones.
    """
    tiempo_restante = inicializar_tiempos_restantes(procesos)
    terminados: set[str] = set()
    primer_acceso: dict[str, int] = {}
    fin: dict[str, int] = {}
    gantt: list[SegmentoGantt] = []
    reloj = 0

    procesos_por_llegada = ordenar_por_llegada(procesos)

    while len(terminados) < len(procesos):
        disponibles = filtrar_disponibles(procesos_por_llegada, reloj, terminados)

        if not disponibles:
            reloj += 1
            continue

        elegido = elegir_menor_rafaga(disponibles, tiempo_restante)

        if elegido.id not in primer_acceso:
            primer_acceso[elegido.id] = reloj

        indice_color  = buscar_indice_proceso(procesos, elegido.id)
        inicio_bloque = reloj
        reloj        += tiempo_restante[elegido.id]
        tiempo_restante[elegido.id] = 0
        terminados.add(elegido.id)
        fin[elegido.id] = reloj
        gantt.append(SegmentoGantt(elegido.id, inicio_bloque, reloj, indice_color))

    return gantt, calcular_metricas(procesos, fin, primer_acceso)


def srtf(procesos: list[Proceso]) -> tuple[list[SegmentoGantt], dict[str, MetricasProceso]]:
    """
    Algoritmo Shortest Remaining Time First (SRTF) — Expulsivo.
    En cada tick evalúa si hay un proceso con menos tiempo restante que el activo.
    """
    tiempo_restante = inicializar_tiempos_restantes(procesos)
    terminados: set[str] = set()
    primer_acceso: dict[str, int] = {}
    fin: dict[str, int] = {}
    gantt: list[SegmentoGantt] = []
    reloj = 0
    proceso_actual: str | None = None
    inicio_segmento = 0

    techo_seguridad = calcular_techo_seguridad(procesos, margen=5)

    while len(terminados) < len(procesos) and reloj < techo_seguridad:
        disponibles = filtrar_disponibles(procesos, reloj, terminados)

        if not disponibles:
            if proceso_actual is not None:
                indice_color = buscar_indice_proceso(procesos, proceso_actual)
                gantt.append(SegmentoGantt(proceso_actual, inicio_segmento, reloj, indice_color))
                proceso_actual = None
            reloj += 1
            inicio_segmento = reloj
            continue

        elegido = elegir_menor_rafaga(disponibles, tiempo_restante)

        if elegido.id not in primer_acceso:
            primer_acceso[elegido.id] = reloj

        # Si cambió el proceso activo, cierra el segmento anterior en el diagrama
        if proceso_actual != elegido.id:
            if proceso_actual is not None:
                indice_color = buscar_indice_proceso(procesos, proceso_actual)
                gantt.append(SegmentoGantt(proceso_actual, inicio_segmento, reloj, indice_color))
            inicio_segmento = reloj
            proceso_actual  = elegido.id

        tiempo_restante[elegido.id] -= 1
        reloj += 1

        if tiempo_restante[elegido.id] == 0:
            terminados.add(elegido.id)
            fin[elegido.id] = reloj
            indice_color = buscar_indice_proceso(procesos, elegido.id)
            gantt.append(SegmentoGantt(elegido.id, inicio_segmento, reloj, indice_color))
            proceso_actual  = None
            inicio_segmento = reloj

    return gantt, calcular_metricas(procesos, fin, primer_acceso)


def planificar_prioridades(procesos: list[Proceso]) -> tuple[list[SegmentoGantt], dict[str, MetricasProceso]]:
    """
    Algoritmo de Planificación por Prioridades — No Expulsivo.
    Menor número de prioridad = mayor urgencia en el sistema.
    """
    tiempo_restante = inicializar_tiempos_restantes(procesos)
    terminados: set[str] = set()
    primer_acceso: dict[str, int] = {}
    fin: dict[str, int] = {}
    gantt: list[SegmentoGantt] = []
    reloj = 0

    procesos_por_llegada = ordenar_por_llegada(procesos)

    while len(terminados) < len(procesos):
        disponibles = filtrar_disponibles(procesos_por_llegada, reloj, terminados)

        if not disponibles:
            reloj += 1
            continue

        elegido = elegir_mayor_prioridad(disponibles, tiempo_restante)

        if elegido.id not in primer_acceso:
            primer_acceso[elegido.id] = reloj

        indice_color  = buscar_indice_proceso(procesos, elegido.id)
        inicio_bloque = reloj
        reloj        += tiempo_restante[elegido.id]
        tiempo_restante[elegido.id] = 0
        terminados.add(elegido.id)
        fin[elegido.id] = reloj
        gantt.append(SegmentoGantt(elegido.id, inicio_bloque, reloj, indice_color))

    return gantt, calcular_metricas(procesos, fin, primer_acceso)


def planificar_round_robin(procesos: list[Proceso], quantum: int = 2) -> tuple[list[SegmentoGantt], dict[str, MetricasProceso]]:
    """
    Algoritmo Round Robin — Compartición de tiempo.
    Cada proceso corre como máximo 'quantum' unidades antes de regresar al final de la cola.
    """
    tiempo_restante = inicializar_tiempos_restantes(procesos)
    terminados: set[str] = set()
    primer_acceso: dict[str, int] = {}
    fin: dict[str, int] = {}
    gantt: list[SegmentoGantt] = []
    reloj = 0
    cola: list[Proceso] = []
    en_cola: set[str] = set()

    ordenados = ordenar_por_llegada_y_prioridad(procesos)

    for p in ordenados:
        if p.llegada == 0:
            cola.append(p)
            en_cola.add(p.id)

    techo_seguridad = calcular_techo_seguridad(procesos, margen=10)

    while len(terminados) < len(procesos) and reloj < techo_seguridad:
        if not cola:
            reloj += 1
            recien_llegados = filtrar_recien_llegados(ordenados, reloj, terminados, en_cola)
            for p in recien_llegados:
                cola.append(p)
                en_cola.add(p.id)
            continue

        actual       = cola.pop(0)
        indice_color = buscar_indice_proceso(procesos, actual.id)

        if actual.id not in primer_acceso:
            primer_acceso[actual.id] = reloj

        duracion      = min(quantum, tiempo_restante[actual.id])
        inicio_bloque = reloj
        reloj        += duracion
        tiempo_restante[actual.id] -= duracion

        # Encola los procesos que llegaron durante la ejecución del actual
        recien_llegados = filtrar_recien_llegados(ordenados, reloj, terminados, en_cola)
        recien_llegados = ordenar_por_llegada_y_prioridad(recien_llegados)
        for p in recien_llegados:
            en_cola.add(p.id)

        gantt.append(SegmentoGantt(actual.id, inicio_bloque, reloj, indice_color))

        if tiempo_restante[actual.id] == 0:
            terminados.add(actual.id)
            fin[actual.id] = reloj
            cola.extend(recien_llegados)
        else:
            # Los recién llegados tienen prioridad sobre el proceso interrumpido
            cola.extend(recien_llegados)
            cola.append(actual)

    return gantt, calcular_metricas(procesos, fin, primer_acceso)


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES (HELPERS) DE DIBUJO EN PYGAME
# ═══════════════════════════════════════════════════════════════════════════════

def dibujar_rectangulo_redondeado(superficie, color, rectangulo, radio_bordes=6, grosor_borde=0, color_borde=None):
    pygame.draw.rect(superficie, color, rectangulo, border_radius=radio_bordes)
    if grosor_borde:
        pygame.draw.rect(superficie, color_borde or PALETA_COLORES["borde_estandar"], rectangulo, grosor_borde, border_radius=radio_bordes)


def dibujar_texto(superficie, texto, fuente, color, coordenada_x, coordenada_y, punto_anclaje="tl"):
    imagen_texto = fuente.render(str(texto), True, color)
    ancho_texto, alto_texto = imagen_texto.get_size()

    desplazamiento_x = {"tl": 0, "tc": -ancho_texto // 2, "tr": -ancho_texto,
                        "cl": 0, "cc": -ancho_texto // 2, "cr": -ancho_texto}.get(punto_anclaje, 0)
    desplazamiento_y = {"tl": 0, "tc": 0, "tr": 0,
                        "cl": -alto_texto // 2, "cc": -alto_texto // 2, "cr": -alto_texto // 2}.get(punto_anclaje, 0)

    superficie.blit(imagen_texto, (coordenada_x + desplazamiento_x, coordenada_y + desplazamiento_y))
    return ancho_texto, alto_texto


def dibujar_efecto_resplandor(superficie, color, rectangulo, radio_bordes=6, nivel_transparencia=55):
    superficie_temporal = pygame.Surface((rectangulo.w + 16, rectangulo.h + 16), pygame.SRCALPHA)
    pygame.draw.rect(superficie_temporal, (*color[:3], nivel_transparencia), superficie_temporal.get_rect(), border_radius=radio_bordes + 5)
    superficie.blit(superficie_temporal, (rectangulo.x - 8, rectangulo.y - 8))


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASE BOTÓN
# ═══════════════════════════════════════════════════════════════════════════════
class BotonInteractivo:
    def __init__(self, rectangulo, etiqueta, color_normal, color_hover, color_activo=None, color_texto=None):
        self.rectangulo = pygame.Rect(rectangulo)
        self.etiqueta = etiqueta
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_activo = color_activo or color_hover
        self.color_texto = color_texto or PALETA_COLORES["texto_alto_contraste"]
        self.mouse_encima = self.esta_seleccionado = False

    def dibujar(self, superficie):
        color_final = self.color_activo if self.esta_seleccionado else (self.color_hover if self.mouse_encima else self.color_normal)
        if self.mouse_encima or self.esta_seleccionado:
            dibujar_efecto_resplandor(superficie, color_final, self.rectangulo, nivel_transparencia=45)
        dibujar_rectangulo_redondeado(superficie, color_final, self.rectangulo, radio_bordes=6)
        color_borde = PALETA_COLORES["color_acento_alerta"] if self.esta_seleccionado else (PALETA_COLORES["borde_destacado"] if self.mouse_encima else PALETA_COLORES["borde_estandar"])
        pygame.draw.rect(superficie, color_borde, self.rectangulo, 1, border_radius=6)
        dibujar_texto(superficie, self.etiqueta, FUENTE_ENCABEZADO, self.color_texto, self.rectangulo.centerx, self.rectangulo.centery, "cc")

    def actualizar_estado_mouse(self, mouse_x, mouse_y):
        self.mouse_encima = self.rectangulo.collidepoint(mouse_x, mouse_y)

    def fue_clicado(self, mouse_x, mouse_y):
        return self.rectangulo.collidepoint(mouse_x, mouse_y)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASE TOOLTIP
# ═══════════════════════════════════════════════════════════════════════════════
class EtiquetaInformativaFlotante:
    def __init__(self):
        self.mensaje = ""
        self.coordenada_x = self.coordenada_y = 0
        self.esta_visible = False

    def mostrar(self, mensaje, mouse_x, mouse_y):
        self.mensaje, self.coordenada_x, self.coordenada_y, self.esta_visible = mensaje, mouse_x, mouse_y, True

    def ocultar(self):
        self.esta_visible = False

    def dibujar(self, superficie):
        if not self.esta_visible or not self.mensaje:
            return
        ancho_texto, alto_texto = FUENTE_PEQUENA.size(self.mensaje)
        margen = 6
        pos_x = min(self.coordenada_x + 14, superficie.get_width() - ancho_texto - margen * 2 - 4)
        pos_y = self.coordenada_y - alto_texto - margen * 2 - 4
        caja = pygame.Rect(pos_x, pos_y, ancho_texto + margen * 2, alto_texto + margen * 2)
        dibujar_rectangulo_redondeado(superficie, PALETA_COLORES["fondo_componentes_enfocados"], caja, 4, 1, PALETA_COLORES["color_acento_atenuado"])
        dibujar_texto(superficie, self.mensaje, FUENTE_PEQUENA, PALETA_COLORES["color_acento_alerta"], caja.x + margen, caja.y + margen)


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
PROCESOS_POR_DEFECTO = [
    Proceso("P1", 1, 3, 1),
    Proceso("P2", 2, 3, 4),
    Proceso("P3", 3, 4, 2),
    Proceso("P4", 1, 4, 1),
    Proceso("P5", 4, 2, 3),
    Proceso("P6", 0, 6, 7),
]

NOMBRES_ALGORITMOS = ["SJF", "SRTF", "Prioridades", "Round Robin"]
DESCRIPCIONES_ALGORITMOS = [
    "Shortest Job First — no expulsivo",
    "Shortest Remaining Time First — expulsivo",
    "Planificación por Prioridad — no expulsivo",
    "Round Robin — quantum configurable",
]

# Columnas de la tabla de edición: (etiqueta, atributo del Proceso, ancho en px)
COLUMNAS_TABLA = [
    ("P",   "id",        60),
    ("TLL", "llegada",   64),
    ("TR",  "rafaga",    64),
    ("PD",  "prioridad", 64),
]

ANCHO_TABLA_PROCESOS  = 316
ESPACIADOR_HORIZONTAL = 12
ORIGEN_Y_CONTENIDO    = 72
ALTO_FILA_TABLA       = 32
DISTANCIA_INICIO_FILAS = 52
ANCHO_TABLA_METRICAS  = 430


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL DE LA APLICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
class AplicacionSimulador:
    def __init__(self):
        self.ANCHO_VENTANA, self.ALTO_VENTANA = 1400, 830
        self.pantalla = pygame.display.set_mode((self.ANCHO_VENTANA, self.ALTO_VENTANA), pygame.RESIZABLE)
        pygame.display.set_caption("CPU Scheduler Simulator")
        self.reloj_fps = pygame.time.Clock()

        self.lista_de_procesos: list[Proceso] = list(PROCESOS_POR_DEFECTO)
        self.indice_algoritmo_seleccionado = 0
        self.quantum_round_robin = 2
        self.gantt: list[SegmentoGantt] = []
        self.metricas: dict[str, MetricasProceso] = {}

        # Edición de celdas: (indice_fila, nombre_atributo) o None
        self.celda_en_edicion: tuple[int, str] | None = None
        self.buffer_texto_edicion = ""
        self.error_en_entrada_edicion = False

        self.duracion_destello_exito = 0
        self.etiqueta_flotante = EtiquetaInformativaFlotante()
        self.inicializar_botones()
        self.ejecutar_simulacion()

    def inicializar_botones(self):
        self.botones_algoritmos = []
        for i, nombre in enumerate(NOMBRES_ALGORITMOS):
            boton = BotonInteractivo(
                (338 + i * 158, 14, 151, 36), nombre,
                PALETA_COLORES["fondo_componentes"],
                PALETA_COLORES["fondo_componentes_enfocados"]
            )
            self.botones_algoritmos.append(boton)
        self.boton_quantum_menos  = BotonInteractivo((1010, 14, 32, 36), "−", PALETA_COLORES["fondo_componentes"], PALETA_COLORES["fondo_componentes_enfocados"])
        self.boton_quantum_mas    = BotonInteractivo((1090, 14, 32, 36), "+", PALETA_COLORES["fondo_componentes"], PALETA_COLORES["fondo_componentes_enfocados"])
        self.boton_simular        = BotonInteractivo((0, 14, 162, 36), "▶  SIMULAR", (18, 58, 28), (24, 88, 44), (30, 108, 52), color_texto=PALETA_COLORES["color_exito"])
        self.boton_agregar_proceso  = BotonInteractivo((0, 0, 140, 28), "+ Proceso",  (18, 46, 22), (24, 66, 30), color_texto=PALETA_COLORES["color_exito"])
        self.boton_eliminar_proceso = BotonInteractivo((0, 0, 140, 28), "− Eliminar", (50, 16, 16), (70, 22, 22), color_texto=(255, 110, 110))

    def ejecutar_simulacion(self):
        if not self.lista_de_procesos:
            self.gantt, self.metricas = [], {}
            return

        algoritmos = [sjf, srtf, planificar_prioridades]
        if self.indice_algoritmo_seleccionado < len(algoritmos):
            self.gantt, self.metricas = algoritmos[self.indice_algoritmo_seleccionado](self.lista_de_procesos)
        else:
            self.gantt, self.metricas = planificar_round_robin(self.lista_de_procesos, self.quantum_round_robin)

        self.duracion_destello_exito = 20

    # ═════════════════════════════════════════════════════════════════════════
    #  RENDERIZADO
    # ═════════════════════════════════════════════════════════════════════════
    def renderizar_interfaz(self):
        ancho_actual, alto_actual = self.pantalla.get_size()
        self.pantalla.fill(PALETA_COLORES["fondo_principal"])

        # Rejilla de fondo
        for x in range(0, ancho_actual, 40):
            pygame.draw.line(self.pantalla, (16, 20, 32), (x, 0), (x, alto_actual))
        for y in range(0, alto_actual, 40):
            pygame.draw.line(self.pantalla, (16, 20, 32), (0, y), (ancho_actual, y))

        # ── HEADER ────────────────────────────────────────────────────────────
        pygame.draw.rect(self.pantalla, PALETA_COLORES["fondo_paneles"], (0, 0, ancho_actual, 64))
        pygame.draw.line(self.pantalla, PALETA_COLORES["color_acento_atenuado"], (0, 64), (ancho_actual, 64))
        dibujar_texto(self.pantalla, "⬡", FUENTE_GIGANTE, PALETA_COLORES["color_acento_alerta"], 16, 32, "cl")
        dibujar_texto(self.pantalla, "CPU SCHEDULER", FUENTE_TITULO, PALETA_COLORES["color_acento_alerta"], 50, 15)
        dibujar_texto(self.pantalla, "simulator — SJF · SRTF · Prioridades · Round Robin", FUENTE_PEQUENA, PALETA_COLORES["texto_secundario"], 52, 38)
        dibujar_texto(self.pantalla, "v2.2", FUENTE_DIMINUTA, PALETA_COLORES["color_acento_atenuado"], 52, 52)

        # Botones de algoritmos
        for i, boton in enumerate(self.botones_algoritmos):
            if i == self.indice_algoritmo_seleccionado:
                dibujar_efecto_resplandor(self.pantalla, PALETA_COLORES["color_acento_alerta"], boton.rectangulo, nivel_transparencia=50)
                dibujar_rectangulo_redondeado(self.pantalla, (48, 36, 6), boton.rectangulo, 6)
                pygame.draw.rect(self.pantalla, PALETA_COLORES["color_acento_alerta"], boton.rectangulo, 1, border_radius=6)
                dibujar_texto(self.pantalla, boton.etiqueta, FUENTE_ENCABEZADO, PALETA_COLORES["color_acento_alerta"], boton.rectangulo.centerx, boton.rectangulo.centery, "cc")
            else:
                boton.dibujar(self.pantalla)

        # Control de Quantum
        origen_x_q = 1010
        dibujar_texto(self.pantalla, "Q=", FUENTE_ENCABEZADO, PALETA_COLORES["texto_secundario"], origen_x_q - 36, 32, "cl")
        self.boton_quantum_menos.rectangulo = pygame.Rect(origen_x_q, 14, 32, 36)
        self.boton_quantum_mas.rectangulo   = pygame.Rect(origen_x_q + 78, 14, 32, 36)
        self.boton_quantum_menos.dibujar(self.pantalla)
        self.boton_quantum_mas.dibujar(self.pantalla)
        caja_q = pygame.Rect(origen_x_q + 34, 14, 42, 36)
        color_q = PALETA_COLORES["color_acento_alerta"] if self.indice_algoritmo_seleccionado == 3 else PALETA_COLORES["texto_secundario"]
        dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_componentes"], caja_q, 4, 1, PALETA_COLORES["borde_estandar"])
        dibujar_texto(self.pantalla, str(self.quantum_round_robin), FUENTE_TITULO, color_q, caja_q.centerx, caja_q.centery, "cc")

        # Botón SIMULAR
        self.boton_simular.rectangulo = pygame.Rect(ancho_actual - 176, 14, 163, 36)
        if self.duracion_destello_exito > 0:
            dibujar_efecto_resplandor(self.pantalla, PALETA_COLORES["color_exito"], self.boton_simular.rectangulo, nivel_transparencia=90)
            self.duracion_destello_exito -= 1
        self.boton_simular.dibujar(self.pantalla)

        # ── PANEL IZQUIERDO — TABLA DE PROCESOS ──────────────────────────────
        panel_izq = pygame.Rect(10, ORIGEN_Y_CONTENIDO, ANCHO_TABLA_PROCESOS, alto_actual - ORIGEN_Y_CONTENIDO - 10)
        dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_paneles"], panel_izq, 8, 1, PALETA_COLORES["borde_estandar"])

        encabezado = pygame.Rect(panel_izq.x, panel_izq.y, panel_izq.w, 30)
        dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_componentes_enfocados"], encabezado, 8)
        pygame.draw.rect(self.pantalla, PALETA_COLORES["fondo_componentes_enfocados"], pygame.Rect(panel_izq.x, panel_izq.y + 14, panel_izq.w, 16))
        pygame.draw.line(self.pantalla, PALETA_COLORES["borde_estandar"], (panel_izq.x, panel_izq.y + 30), (panel_izq.x + panel_izq.w, panel_izq.y + 30))

        # Coordenadas X de columnas, calculadas a partir de COLUMNAS_TABLA
        coords_x_cols = [panel_izq.x + 14]
        for etiqueta, atributo, ancho in COLUMNAS_TABLA[:-1]:
            coords_x_cols.append(coords_x_cols[-1] + ancho)

        for (etiqueta, atributo, ancho), cx in zip(COLUMNAS_TABLA, coords_x_cols):
            dibujar_texto(self.pantalla, etiqueta, FUENTE_ENCABEZADO, PALETA_COLORES["color_informativo"], cx + 4, panel_izq.y + 8)

        dibujar_texto(self.pantalla, "TLL=llegada   TR=ráfaga   PD=prioridad", FUENTE_DIMINUTA, PALETA_COLORES["texto_secundario"], panel_izq.x + 8, panel_izq.y + 34)

        origen_y_filas = panel_izq.y + DISTANCIA_INICIO_FILAS
        for i_fila, proceso in enumerate(self.lista_de_procesos):
            cy = origen_y_filas + i_fila * ALTO_FILA_TABLA
            color_fondo = PALETA_COLORES["fila_tabla_par"] if i_fila % 2 == 0 else PALETA_COLORES["fila_tabla_impar"]
            dibujar_rectangulo_redondeado(self.pantalla, color_fondo, pygame.Rect(panel_izq.x + 4, cy + 1, panel_izq.w - 8, ALTO_FILA_TABLA - 2), 4)

            color_proceso = COLORES_PROCESOS[i_fila % len(COLORES_PROCESOS)]
            pygame.draw.rect(self.pantalla, color_proceso, pygame.Rect(panel_izq.x + 4, cy + 1, 4, ALTO_FILA_TABLA - 2), border_radius=2)

            for (etiqueta, atributo, ancho), cx in zip(COLUMNAS_TABLA, coords_x_cols):
                valor = getattr(proceso, atributo)
                if self.celda_en_edicion == (i_fila, atributo):
                    rect_edit = pygame.Rect(cx + 2, cy + 5, ancho - 6, ALTO_FILA_TABLA - 10)
                    color_borde = PALETA_COLORES["color_error"] if self.error_en_entrada_edicion else PALETA_COLORES["color_informativo"]
                    dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_principal"], rect_edit, 3, 2, color_borde)
                    cursor = "_" if pygame.time.get_ticks() // 500 % 2 == 0 else " "
                    dibujar_texto(self.pantalla, self.buffer_texto_edicion + cursor, FUENTE_CUERPO, color_borde, cx + 5, cy + 8)
                else:
                    dibujar_texto(self.pantalla, str(valor), FUENTE_CUERPO, PALETA_COLORES["texto_principal"], cx + 6, cy + 8)

        pos_y_crud = origen_y_filas + len(self.lista_de_procesos) * ALTO_FILA_TABLA + 8
        self.boton_agregar_proceso.rectangulo  = pygame.Rect(panel_izq.x + 6,   pos_y_crud, 140, 28)
        self.boton_eliminar_proceso.rectangulo = pygame.Rect(panel_izq.x + 154, pos_y_crud, 140, 28)
        self.boton_agregar_proceso.dibujar(self.pantalla)
        self.boton_eliminar_proceso.dibujar(self.pantalla)

        pos_y_inst = pos_y_crud + 36
        for linea in [
            "↑ Clic en celda para editar valor",
            "  Enter = confirmar  |  Tab = siguiente",
            "  Esc = cancelar",
            "",
            "▶ SIMULAR aplica todos los cambios",
            "  y recalcula el diagrama.",
        ]:
            color_inst = PALETA_COLORES["color_acento_atenuado"] if "SIMULAR" in linea else PALETA_COLORES["texto_secundario"]
            dibujar_texto(self.pantalla, linea, FUENTE_DIMINUTA, color_inst, panel_izq.x + 8, pos_y_inst)
            pos_y_inst += 14

        separador_x = ANCHO_TABLA_PROCESOS + 18
        pygame.draw.line(self.pantalla, PALETA_COLORES["borde_estandar"], (separador_x, ORIGEN_Y_CONTENIDO + 4), (separador_x, alto_actual - 14))

        # ── PANEL DERECHO ─────────────────────────────────────────────────────
        ox = separador_x + ESPACIADOR_HORIZONTAL
        ancho_der = ancho_actual - ox - 12

        if not self.gantt:
            dibujar_texto(self.pantalla, "Sin datos — agrega procesos y pulsa  ▶ SIMULAR", FUENTE_CUERPO, PALETA_COLORES["texto_secundario"], ox + 20, ORIGEN_Y_CONTENIDO + 40)
            self.etiqueta_flotante.dibujar(self.pantalla)
            pygame.display.flip()
            return

        tiempo_max = 0
        for seg in self.gantt:
            if seg.fin > tiempo_max:
                tiempo_max = seg.fin
        total_procesos = len(self.lista_de_procesos)

        # ── DIAGRAMA DE GANTT ─────────────────────────────────────────────────
        dibujar_texto(self.pantalla, "DIAGRAMA DE GANTT", FUENTE_ENCABEZADO, PALETA_COLORES["color_informativo"], ox, ORIGEN_Y_CONTENIDO)
        dibujar_texto(self.pantalla, f"  [{DESCRIPCIONES_ALGORITMOS[self.indice_algoritmo_seleccionado]}]", FUENTE_PEQUENA, PALETA_COLORES["texto_secundario"],
                      ox + FUENTE_ENCABEZADO.size("DIAGRAMA DE GANTT")[0] + 4, ORIGEN_Y_CONTENIDO + 2)

        oy_gantt       = ORIGEN_Y_CONTENIDO + 22
        alto_celda     = 26
        sep_barras     = 4
        ancho_pid      = 40
        espacio_gantt  = ancho_der - ancho_pid - 4
        ancho_tick     = max(10, min(30, espacio_gantt // (tiempo_max + 1)))
        alto_bloque    = total_procesos * (alto_celda + sep_barras) + 30

        caja_gantt = pygame.Rect(ox - 4, oy_gantt - 4, ancho_pid + tiempo_max * ancho_tick + 8, alto_bloque + 4)
        dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_paneles"], caja_gantt, 8, 1, PALETA_COLORES["borde_estandar"])

        for i_fila, proceso in enumerate(self.lista_de_procesos):
            cy_barra = oy_gantt + i_fila * (alto_celda + sep_barras)
            color_proc = COLORES_PROCESOS[i_fila % len(COLORES_PROCESOS)]

            dibujar_texto(self.pantalla, proceso.id, FUENTE_MONOESPACIO, color_proc, ox + ancho_pid // 2, cy_barra + alto_celda // 2, "cc")

            segmentos = []
            for seg in self.gantt:
                if seg.proceso_id == proceso.id:
                    segmentos.append((seg.inicio, seg.fin))

            pygame.draw.rect(self.pantalla, PALETA_COLORES["fondo_celda_espera"],
                             pygame.Rect(ox + ancho_pid, cy_barra, tiempo_max * ancho_tick, alto_celda), border_radius=2)

            for inicio, fin in segmentos:
                cx_bloque  = ox + ancho_pid + inicio * ancho_tick
                ancho_bloque = (fin - inicio) * ancho_tick
                rect_bloque = pygame.Rect(cx_bloque + 1, cy_barra + 1, ancho_bloque - 2, alto_celda - 2)
                dibujar_rectangulo_redondeado(self.pantalla, color_proc, rect_bloque, 3)
                brillo = pygame.Surface((ancho_bloque - 2, 5), pygame.SRCALPHA)
                brillo.fill((255, 255, 255, 35))
                self.pantalla.blit(brillo, (cx_bloque + 1, cy_barra + 1))
                if ancho_bloque > 20:
                    dibujar_texto(self.pantalla, proceso.id, FUENTE_DIMINUTA, PALETA_COLORES["fondo_principal"],
                                  cx_bloque + ancho_bloque // 2, cy_barra + alto_celda // 2, "cc")

            # Línea de llegada
            cx_llegada = ox + ancho_pid + proceso.llegada * ancho_tick
            pygame.draw.line(self.pantalla, PALETA_COLORES["color_acento_alerta"],
                             (cx_llegada, cy_barra), (cx_llegada, cy_barra + alto_celda), 2)

        # Eje temporal
        cy_eje = oy_gantt + total_procesos * (alto_celda + sep_barras) + 2
        paso   = max(1, tiempo_max // 26)
        for t in range(0, tiempo_max + 1, paso):
            cx_marca = ox + ancho_pid + t * ancho_tick
            pygame.draw.line(self.pantalla, PALETA_COLORES["borde_estandar"], (cx_marca, cy_eje), (cx_marca, cy_eje + 5))
            dibujar_texto(self.pantalla, str(t), FUENTE_DIMINUTA, PALETA_COLORES["texto_secundario"], cx_marca, cy_eje + 7, "tc")

        cx_final = ox + ancho_pid + tiempo_max * ancho_tick
        pygame.draw.line(self.pantalla, PALETA_COLORES["color_informativo"], (cx_final, cy_eje), (cx_final, cy_eje + 5))
        dibujar_texto(self.pantalla, str(tiempo_max), FUENTE_DIMINUTA, PALETA_COLORES["color_informativo"], cx_final, cy_eje + 7, "tc")

        cy_leyenda = cy_eje + 22
        pygame.draw.rect(self.pantalla, PALETA_COLORES["color_acento_alerta"], (ox, cy_leyenda + 5, 3, 12))
        dibujar_texto(self.pantalla, "= llegada (TLL)", FUENTE_DIMINUTA, PALETA_COLORES["color_acento_atenuado"], ox + 6, cy_leyenda + 4)
        pygame.draw.rect(self.pantalla, PALETA_COLORES["fondo_celda_espera"], (ox + 130, cy_leyenda + 4, 16, 12), border_radius=2)
        dibujar_texto(self.pantalla, "= en espera", FUENTE_DIMINUTA, PALETA_COLORES["texto_secundario"], ox + 150, cy_leyenda + 4)

        # ── TABLA DE MÉTRICAS ─────────────────────────────────────────────────
        cy_metricas = oy_gantt + alto_bloque + 36
        dibujar_texto(self.pantalla, "MÉTRICAS DE RENDIMIENTO", FUENTE_ENCABEZADO, PALETA_COLORES["color_informativo"], ox, cy_metricas - 18)
        pygame.draw.line(self.pantalla, PALETA_COLORES["color_informativo_oscuro"], (ox - 4, cy_metricas - 4), (ox + ANCHO_TABLA_METRICAS, cy_metricas - 4))

        cx_met = [ox + 4, ox + 72, ox + 200, ox + 320]

        caja_enc = pygame.Rect(ox - 4, cy_metricas, ANCHO_TABLA_METRICAS + 4, 26)
        dibujar_rectangulo_redondeado(self.pantalla, PALETA_COLORES["fondo_componentes_enfocados"], caja_enc, 6)
        pygame.draw.line(self.pantalla, PALETA_COLORES["color_informativo"], (ox - 4, cy_metricas + 26), (ox + ANCHO_TABLA_METRICAS, cy_metricas + 26))

        ENCABEZADOS_METRICAS = [
            ("Proceso",      cx_met[0], PALETA_COLORES["color_informativo"]),
            ("T. Espera",    cx_met[1], PALETA_COLORES["color_acento_alerta"]),
            ("T. Respuesta", cx_met[2], PALETA_COLORES["color_informativo"]),
            ("TRE",          cx_met[3], PALETA_COLORES["color_metrica_retorno"]),
        ]
        for texto, cx, color in ENCABEZADOS_METRICAS:
            dibujar_texto(self.pantalla, texto, FUENTE_ENCABEZADO, color, cx, cy_metricas + 5)

        dibujar_texto(self.pantalla, "TRE = T.Espera + T.Ráfaga  (Turnaround / Retorno)",
                      FUENTE_DIMINUTA, PALETA_COLORES["color_metrica_retorno"], ox + ANCHO_TABLA_METRICAS + 8, cy_metricas + 8)

        acc_espera = acc_respuesta = acc_retorno = 0
        for i_fila, proceso in enumerate(self.lista_de_procesos):
            if proceso.id not in self.metricas:
                continue
            m = self.metricas[proceso.id]
            acc_espera    += m.espera
            acc_respuesta += m.respuesta
            acc_retorno   += m.retorno

            cy_fila = cy_metricas + 28 + i_fila * 24
            color_fondo = PALETA_COLORES["fila_tabla_par"] if i_fila % 2 == 0 else PALETA_COLORES["fila_tabla_impar"]
            dibujar_rectangulo_redondeado(self.pantalla, color_fondo, pygame.Rect(ox - 4, cy_fila + 1, ANCHO_TABLA_METRICAS + 4, 22), 4)
            color_proc = COLORES_PROCESOS[i_fila % len(COLORES_PROCESOS)]
            pygame.draw.rect(self.pantalla, color_proc, pygame.Rect(ox - 4, cy_fila + 1, 3, 22), border_radius=1)

            dibujar_texto(self.pantalla, proceso.id,       FUENTE_CUERPO,      PALETA_COLORES["texto_principal"],       cx_met[0], cy_fila + 4)
            dibujar_texto(self.pantalla, str(m.espera),    FUENTE_MONOESPACIO, PALETA_COLORES["color_acento_alerta"],   cx_met[1], cy_fila + 4)
            dibujar_texto(self.pantalla, str(m.respuesta), FUENTE_MONOESPACIO, PALETA_COLORES["color_informativo"],     cx_met[2], cy_fila + 4)
            badge = pygame.Rect(cx_met[3] - 2, cy_fila + 3, 52, 16)
            dibujar_rectangulo_redondeado(self.pantalla, (48, 38, 68), badge, 3, 1, PALETA_COLORES["color_metrica_retorno"])
            dibujar_texto(self.pantalla, str(m.retorno),   FUENTE_MONOESPACIO, PALETA_COLORES["color_metrica_retorno"], cx_met[3] + 2, cy_fila + 4)

        if total_procesos > 0:
            cy_prom = cy_metricas + 28 + total_procesos * 24 + 4
            dibujar_rectangulo_redondeado(self.pantalla, (38, 48, 28), pygame.Rect(ox - 4, cy_prom, ANCHO_TABLA_METRICAS + 4, 26), 5, 1, PALETA_COLORES["color_acento_atenuado"])
            dibujar_texto(self.pantalla, "PROMEDIO", FUENTE_ENCABEZADO, PALETA_COLORES["color_acento_atenuado"], cx_met[0], cy_prom + 5)
            dibujar_texto(self.pantalla, f"{acc_espera    / total_procesos:.3f}", FUENTE_ENCABEZADO, PALETA_COLORES["color_acento_alerta"],   cx_met[1], cy_prom + 5)
            dibujar_texto(self.pantalla, f"{acc_respuesta / total_procesos:.3f}", FUENTE_ENCABEZADO, PALETA_COLORES["color_informativo"],     cx_met[2], cy_prom + 5)
            caja_prom = pygame.Rect(cx_met[3] - 2, cy_prom + 3, 72, 18)
            dibujar_rectangulo_redondeado(self.pantalla, (48, 38, 68), caja_prom, 3, 1, PALETA_COLORES["color_metrica_retorno"])
            dibujar_texto(self.pantalla, f"{acc_retorno   / total_procesos:.3f}", FUENTE_ENCABEZADO, PALETA_COLORES["color_metrica_retorno"], cx_met[3] + 2, cy_prom + 5)

        # ── STATUS BAR ────────────────────────────────────────────────────────
        cy_status = alto_actual - 22
        pygame.draw.line(self.pantalla, PALETA_COLORES["borde_estandar"], (0, cy_status), (ancho_actual, cy_status))
        pygame.draw.rect(self.pantalla, PALETA_COLORES["fondo_paneles"], pygame.Rect(0, cy_status, ancho_actual, 22))
        if total_procesos > 0:
            texto_status = (
                f"  Procesos: {total_procesos}  |  Algoritmo: {NOMBRES_ALGORITMOS[self.indice_algoritmo_seleccionado]}"
                + (f"  Q={self.quantum_round_robin}" if self.indice_algoritmo_seleccionado == 3 else "")
                + f"  |  Tiempo total: {tiempo_max} u.t."
                + f"  |  Prom. espera: {acc_espera / total_procesos:.3f}"
            )
            dibujar_texto(self.pantalla, texto_status, FUENTE_DIMINUTA, PALETA_COLORES["texto_secundario"], 0, cy_status + 5)

        self.etiqueta_flotante.dibujar(self.pantalla)
        pygame.display.flip()

    # ═════════════════════════════════════════════════════════════════════════
    #  EVENTOS
    # ═════════════════════════════════════════════════════════════════════════
    def controlar_eventos(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.etiqueta_flotante.ocultar()

        for i, boton in enumerate(self.botones_algoritmos):
            boton.actualizar_estado_mouse(mouse_x, mouse_y)
            if boton.mouse_encima:
                self.etiqueta_flotante.mostrar(DESCRIPCIONES_ALGORITMOS[i], mouse_x, mouse_y)

        for boton in [self.boton_quantum_menos, self.boton_quantum_mas, self.boton_simular, self.boton_agregar_proceso, self.boton_eliminar_proceso]:
            boton.actualizar_estado_mouse(mouse_x, mouse_y)

        if self.boton_simular.mouse_encima:
            self.etiqueta_flotante.mostrar("Aplica cambios y recalcula el diagrama", mouse_x, mouse_y)
        if self.boton_quantum_menos.mouse_encima or self.boton_quantum_mas.mouse_encima:
            self.etiqueta_flotante.mostrar("Quantum para Round Robin", mouse_x, mouse_y)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif evento.type == pygame.VIDEORESIZE:
                self.ANCHO_VENTANA, self.ALTO_VENTANA = evento.w, evento.h
                self.pantalla = pygame.display.set_mode((self.ANCHO_VENTANA, self.ALTO_VENTANA), pygame.RESIZABLE)

            elif evento.type == pygame.KEYDOWN:
                if self.celda_en_edicion is not None:
                    i_fila, atributo = self.celda_en_edicion
                    if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.guardar_cambios_edicion()
                        self.ejecutar_simulacion()
                    elif evento.key == pygame.K_TAB:
                        self.guardar_cambios_edicion()
                        atributos = []
                        for col in COLUMNAS_TABLA:
                            atributos.append(col[1])
                        siguiente = atributos[(atributos.index(atributo) + 1) % len(atributos)]
                        self.celda_en_edicion = (i_fila, siguiente)
                        self.buffer_texto_edicion = str(getattr(self.lista_de_procesos[i_fila], siguiente))
                        self.error_en_entrada_edicion = False
                    elif evento.key == pygame.K_ESCAPE:
                        self.celda_en_edicion = None
                        self.buffer_texto_edicion = ""
                        self.error_en_entrada_edicion = False
                    elif evento.key == pygame.K_BACKSPACE:
                        self.buffer_texto_edicion = self.buffer_texto_edicion[:-1]
                    else:
                        if evento.unicode:
                            self.buffer_texto_edicion += evento.unicode
                            self.error_en_entrada_edicion = False

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self.procesar_click_mouse(mouse_x, mouse_y)

    def procesar_click_mouse(self, mouse_x, mouse_y):
        if self.celda_en_edicion is not None:
            self.guardar_cambios_edicion()

        for i, boton in enumerate(self.botones_algoritmos):
            if boton.fue_clicado(mouse_x, mouse_y):
                self.indice_algoritmo_seleccionado = i
                self.ejecutar_simulacion()
                return

        if self.boton_quantum_menos.fue_clicado(mouse_x, mouse_y):
            self.quantum_round_robin = max(1, self.quantum_round_robin - 1)
            self.ejecutar_simulacion()
            return
        if self.boton_quantum_mas.fue_clicado(mouse_x, mouse_y):
            self.quantum_round_robin += 1
            self.ejecutar_simulacion()
            return
        if self.boton_simular.fue_clicado(mouse_x, mouse_y):
            self.ejecutar_simulacion()
            return
        if self.boton_agregar_proceso.fue_clicado(mouse_x, mouse_y):
            n = len(self.lista_de_procesos) + 1
            self.lista_de_procesos.append(Proceso(f"P{n}", 0, 1, 1))
            self.ejecutar_simulacion()
            return
        if self.boton_eliminar_proceso.fue_clicado(mouse_x, mouse_y) and self.lista_de_procesos:
            self.lista_de_procesos.pop()
            self.ejecutar_simulacion()
            return

        # Detección de clicks en celdas de la tabla
        origen_y_filas = ORIGEN_Y_CONTENIDO + DISTANCIA_INICIO_FILAS
        panel_x = 10
        coords_x_cols = [panel_x + 14]
        for etiqueta, atributo, ancho in COLUMNAS_TABLA[:-1]:
            coords_x_cols.append(coords_x_cols[-1] + ancho)

        for i_fila, proceso in enumerate(self.lista_de_procesos):
            cy = origen_y_filas + i_fila * ALTO_FILA_TABLA
            for (etiqueta, atributo, ancho), cx in zip(COLUMNAS_TABLA, coords_x_cols):
                rect_celda = pygame.Rect(cx + 2, cy + 5, ancho - 6, ALTO_FILA_TABLA - 10)
                if rect_celda.collidepoint(mouse_x, mouse_y):
                    self.celda_en_edicion = (i_fila, atributo)
                    self.buffer_texto_edicion = str(getattr(proceso, atributo))
                    self.error_en_entrada_edicion = False
                    return

    def guardar_cambios_edicion(self):
        if self.celda_en_edicion is None:
            return

        i_fila, atributo = self.celda_en_edicion
        proceso = self.lista_de_procesos[i_fila]
        texto = self.buffer_texto_edicion.strip()

        if atributo == "id":
            if texto:
                proceso.id = texto
        else:
            try:
                valor = int(texto)
                # La ráfaga debe ser al menos 1; llegada y prioridad pueden ser 0
                valor = max(1 if atributo == "rafaga" else 0, valor)
                setattr(proceso, atributo, valor)
                self.error_en_entrada_edicion = False
            except ValueError:
                self.error_en_entrada_edicion = True
                self.celda_en_edicion = None
                self.buffer_texto_edicion = ""
                return

        self.celda_en_edicion = None
        self.buffer_texto_edicion = ""

    # ═════════════════════════════════════════════════════════════════════════
    #  BUCLE PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════
    def ejecutar(self):
        while True:
            self.controlar_eventos()
            self.renderizar_interfaz()
            self.reloj_fps.tick(60)


if __name__ == "__main__":
    simulador = AplicacionSimulador()
    simulador.ejecutar()
