# -*- coding: utf-8 -*-
"""
ISS-PROD-VAR: Sistema de variantes por presentación para productos.

PROBLEMA QUE RESUELVE
=====================
Un mismo código de producto (ej. 663) no puede representar múltiples
presentaciones del mismo medicamento. Si existe 663 - PARACETAMOL con
presentación "CAJA CON 10 TABLETAS" y se intenta importar/crear
663 - PARACETAMOL con "CAJA CON 15 TABLETAS", el sistema DEBE crear
automáticamente la variante 663.2 en lugar de sobreescribir o duplicar.

ESTÁNDAR ELEGIDO: Opción A
===========================
- El producto original se queda con su clave sin modificar (ej. 663).
- Cada nueva presentación del mismo código base se registra como:
    663.2, 663.3, 663.4, ...
- Esto es retrocompatible: no requiere migración de códigos existentes.

NORMALIZACIÓN SEMÁNTICA
=======================
Para comparar presentaciones, se aplica normalización en dos capas:

1. Básica:
   - Convertir a mayúsculas
   - Quitar acentos y caracteres especiales
   - Normalizar espacios

2. Semántica:
   - Expandir abreviaturas: c/ → con, tabs → tabletas, caps → cápsulas
   - Normalizar unidades: ml → ml, mg → mg, UI → ui
   - Eliminar artículos: de, del, las, los (de "caja de 10" → "caja 10")

Con fallback seguro: si la normalización semántica falla por cualquier
motivo, se usa el texto en mayúsculas limpio.

API PÚBLICA
===========
- normalizar_presentacion(texto: str) -> str
- extraer_codigo_base(clave: str) -> str
- es_variante(clave: str) -> bool
- obtener_o_crear_variante(clave_input, nombre, presentacion, defaults, usuario=None)
  -> (producto, created: bool, info: dict)
- migrar_variantes_existentes() -> list[dict]  (script de migración)
"""

import re
import unicodedata
import logging

from django.db import transaction

logger = logging.getLogger(__name__)

# ===========================================================================
# TABLAS DE NORMALIZACIÓN SEMÁNTICA
# Orden: más específicas primero para evitar solapamientos
# ===========================================================================

_ABREVIATURAS = [
    # Conectores / preposiciones (quitar antes de tokenizar)
    (r'\b(de|del|las|los|la|el|un|una)\b', ''),

    # Abreviatura c/ (con)
    (r'\bc/\b', 'con'),

    # Empaques / contenedores
    (r'\bfrascos?\b',       'frasco'),
    (r'\btubos?\b',         'tubo'),
    (r'\bblister\b',        'blister'),
    (r'\bjeringas?\b',      'jeringa'),
    (r'\bjeringuillas?\b',  'jeringa'),
    (r'\bbolsas?\b',        'bolsa'),
    (r'\benvases?\b',       'envase'),
    (r'\bviales?\b',        'vial'),
    (r'\bampolletas?\b',    'ampolleta'),
    (r'\bampulas?\b',       'ampolleta'),
    (r'\bampolla\b',        'ampolleta'),
    (r'\bsobres?\b',        'sobre'),
    (r'\bpiezas?\b',        'pieza'),
    (r'\bpzas?\b',          'pieza'),

    # Unidades farmacéuticas
    (r'\btabletas?\b',      'tableta'),
    (r'\btabs?\b',          'tableta'),
    (r'\btablets?\b',       'tableta'),
    (r'\bcomprimidos?\b',   'tableta'),
    (r'\bcomp\b',           'tableta'),
    (r'\bcapsulas?\b',      'capsula'),
    (r'\bcaps?\b',          'capsula'),
    (r'\bovulos?\b',        'ovulo'),
    (r'\bsupositorios?\b',  'supositorio'),

    # Unidades de volumen
    (r'\bmililitros?\b',    'ml'),
    (r'\blitros?\b',        'litro'),
    (r'\blt\b',             'litro'),

    # Unidades de masa / potencia
    (r'\bkilogramos?\b',    'kg'),
    (r'\bgramos?\b',        'g'),
    (r'\bmiligramos?\b',    'mg'),
    (r'\bmicrogramos?\b',   'mcg'),
    (r'\bunidades?\b',      'unidad'),
    (r'\buds?\b',           'unidad'),
    (r'\bui\b',             'ui'),
    (r'\bu\.i\.\b',         'ui'),

    # Porcentajes: "5%" → "5 porciento"
    (r'(\d+(?:\.\d+)?)\s*%', r'\1 porciento'),
]

# Pre-compilar regex para máxima performance
_ABREVIATURAS_RE = [
    (re.compile(pat, re.IGNORECASE | re.UNICODE), rep)
    for pat, rep in _ABREVIATURAS
]


# ===========================================================================
# NORMALIZACIÓN
# ===========================================================================

def _quitar_acentos(texto: str) -> str:
    """Descompone en NFD y descarta los diacríticos (acentos)."""
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('ascii')


def normalizar_texto_base(texto: str) -> str:
    """
    Normalización básica (capa 1):
    - Mayúsculas
    - Quitar acentos
    - Quitar caracteres no alfanuméricos (conserva espacio y punto)
    - Normalizar espacios múltiples
    """
    if not texto:
        return ''
    s = str(texto).strip().upper()
    s = _quitar_acentos(s)
    # Reemplazar todo lo que no sea letra, dígito, espacio o punto por espacio
    s = re.sub(r'[^A-Z0-9\s\.]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def normalizar_presentacion(texto: str) -> str:
    """
    Normalización semántica completa (capas 1 + 2).

    Transforma variantes de escritura en una clave canónica.

    Ejemplos:
        "Caja c/10 tabletas"  → "CAJA CON 10 TABLETA"
        "CAJA CON 10 TABS"    → "CAJA CON 10 TABLETA"
        "caja 10 tabs"        → "CAJA 10 TABLETA"
        "FRASCO c/ 120ml"     → "FRASCO CON 120 ML"
        "FRASCO 120 ML"       → "FRASCO 120 ML"

    Fallback: si cualquier paso falla, usa normalizar_texto_base().
    """
    if not texto:
        return ''

    try:
        # Capa 1: básica
        s = normalizar_texto_base(texto)
        s = s.lower()

        # Capa 2: semántica
        for patron, reemplazo in _ABREVIATURAS_RE:
            s = patron.sub(reemplazo, s)

        # Limpiar espacios múltiples tras sustituciones
        s = re.sub(r'\s+', ' ', s).strip()

        return s.upper()

    except Exception as exc:
        logger.warning(
            f"ISS-PROD-VAR: normalizar_presentacion fallback para '{texto}': {exc}"
        )
        try:
            return normalizar_texto_base(texto)
        except Exception:
            return str(texto).strip().upper()[:200]


# ===========================================================================
# MANEJO DE CLAVES Y VARIANTES
# ===========================================================================

_VARIANTE_RE = re.compile(r'^(?P<base>.+)\.(?P<sufijo>\d+)$')


def extraer_codigo_base(clave: str) -> str:
    """
    Extrae el código base quitando el sufijo numérico si existe.

    Ejemplos:
        "663"     → "663"
        "663.2"   → "663"
        "663.10"  → "663"
        "MED-001" → "MED-001"
        "1A"      → "1A"

    Regla: sufijo válido = ".<uno o más dígitos>" al final de la cadena.
    """
    if not clave:
        return ''
    m = _VARIANTE_RE.match(str(clave).strip())
    return m.group('base') if m else str(clave).strip()


def es_variante(clave: str) -> bool:
    """True si la clave tiene sufijo numérico (663.2 → True, 663 → False)."""
    return bool(_VARIANTE_RE.match(str(clave or '').strip()))


def _claves_del_mismo_base(codigo_base: str):
    """
    Devuelve QuerySet de Productos cuya clave corresponde al código base
    o a cualquiera de sus variantes (663, 663.2, 663.3, ...).

    Usa LIKE para eficiencia; filtra en Python para exactitud.
    """
    from core.models import Producto
    patron = re.compile(
        r'^' + re.escape(codigo_base) + r'(\.\d+)?$',
        re.IGNORECASE
    )
    qs = Producto.objects.filter(
        clave__istartswith=codigo_base
    ).only('id', 'clave', 'nombre', 'presentacion')

    # Filtrar en Python para asegurar exactitud del patrón
    ids_validos = [p.pk for p in qs if patron.match(p.clave)]
    return Producto.objects.filter(pk__in=ids_validos)


def siguiente_codigo_variante(codigo_base: str) -> str:
    """
    Calcula el siguiente código de variante disponible.

    Busca todos los productos del mismo base (663, 663.2, 663.3…) y
    retorna el siguiente sufijo libre: 663.(max_sufijo + 1).

    IMPORTANTE: Llamar siempre dentro de una transacción con SELECT FOR UPDATE
    para prevenir colisiones en inserciones concurrentes.
    """
    from core.models import Producto

    patron = re.compile(
        r'^' + re.escape(codigo_base) + r'\.(\d+)$',
        re.IGNORECASE
    )

    # Bloqueo optimista: buscar con LIKE y filtrar en Python
    claves = list(
        Producto.objects.select_for_update()
        .filter(clave__istartswith=codigo_base + '.')
        .values_list('clave', flat=True)
    )

    sufijos = [1]  # El producto base cuenta como sufijo "1" implícito
    for clave in claves:
        m = patron.match(clave)
        if m:
            try:
                sufijos.append(int(m.group(1)))
            except ValueError:
                pass

    siguiente = max(sufijos) + 1
    return f"{codigo_base}.{siguiente}"


# ===========================================================================
# FUNCIÓN PRINCIPAL: OBTENER O CREAR VARIANTE
# ===========================================================================

@transaction.atomic
def obtener_o_crear_variante(
    clave_input: str,
    nombre: str,
    presentacion: str,
    defaults: dict,
    usuario=None,
) -> tuple:
    """
    Función principal del sistema de variantes por presentación.

    Implementa Opción A:
    - El producto original conserva su clave.
    - Nuevas presentaciones del mismo base obtienen sufijo: 663.2, 663.3...

    Parámetros
    ----------
    clave_input : str
        Clave enviada por el usuario/importador (puede ser "663" o "663.2").
    nombre : str
        Nombre del producto.
    presentacion : str
        Texto de presentación tal como viene (se normaliza internamente).
    defaults : dict
        Resto de campos del producto (unidad_medida, categoria, etc.).
        NO debe incluir 'clave', 'nombre' ni 'presentacion'.
    usuario : optional
        Usuario que realiza la operación (para auditoría futura).

    Returns
    -------
    (producto, created, info)

    producto : Producto
        Instancia del producto (existente o recién creado).
    created : bool
        True si se creó una nueva variante.
    info : dict
        Contiene:
        - codigo_base: "663"
        - codigo_asignado: "663.2" (puede ser igual a clave_input)
        - codigo_input: "663" (lo que el usuario envió)
        - es_variante: True/False
        - presentacion_normalizada: "CAJA CON 15 TABLETA"
        - motivo: descripción de lo que ocurrió

    Raises
    ------
    ValueError
        Si el usuario envía explícitamente una clave con sufijo (ej. 663.2)
        y la presentación no coincide con la ya registrada para ese sufijo.
    """
    from core.models import Producto

    clave_input = str(clave_input).strip().upper()[:50]
    codigo_base = extraer_codigo_base(clave_input)
    presentacion_norm = normalizar_presentacion(presentacion)

    info = {
        'codigo_base': codigo_base,
        'codigo_input': clave_input,
        'codigo_asignado': clave_input,   # se actualiza abajo
        'es_variante': es_variante(clave_input),
        'presentacion_normalizada': presentacion_norm,
        'motivo': '',
    }

    # ------------------------------------------------------------------
    # PASO A: ¿Existe exactamente esa clave?
    # ------------------------------------------------------------------
    try:
        producto_exacto = (
            Producto.objects.select_for_update()
            .get(clave__iexact=clave_input)
        )
        pres_existente_norm = normalizar_presentacion(
            producto_exacto.presentacion or ''
        )

        if presentacion_norm and pres_existente_norm:
            if pres_existente_norm == presentacion_norm:
                # Clave existe y presentación coincide → reusar
                info.update({
                    'codigo_asignado': producto_exacto.clave,
                    'es_variante': es_variante(producto_exacto.clave),
                    'motivo': 'reutilizado_presentacion_identica',
                })
                return (producto_exacto, False, info)

            # Presentación DIFERENTE
            if es_variante(clave_input):
                # Usuario envió explícitamente "663.2" pero presentación no match
                raise ValueError(
                    f"La clave {clave_input} está registrada con la presentación "
                    f"«{producto_exacto.presentacion}», que difiere de "
                    f"«{presentacion}». Verifique la clave o la presentación."
                )

            # Es el código base — hay que crear una nueva variante (sigue al paso B)
        else:
            # Sin presentación para comparar → reusar el producto existente
            info.update({
                'codigo_asignado': producto_exacto.clave,
                'es_variante': es_variante(producto_exacto.clave),
                'motivo': 'reutilizado_sin_presentacion',
            })
            return (producto_exacto, False, info)

    except Producto.DoesNotExist:
        pass  # La clave no existe → continuar

    # ------------------------------------------------------------------
    # PASO B: ¿Existe algún producto del mismo base con la MISMA presentación?
    # ------------------------------------------------------------------
    if presentacion_norm:
        candidatos = _claves_del_mismo_base(codigo_base)
        for candidato in candidatos.iterator():
            pres_cand = normalizar_presentacion(candidato.presentacion or '')
            if pres_cand == presentacion_norm:
                info.update({
                    'codigo_asignado': candidato.clave,
                    'es_variante': es_variante(candidato.clave),
                    'motivo': 'reutilizado_variante_existente',
                })
                return (candidato, False, info)

    # ------------------------------------------------------------------
    # PASO C: Nueva presentación (o nuevo código) → crear
    # ------------------------------------------------------------------
    existe_base_ya = _claves_del_mismo_base(codigo_base).exists()

    if existe_base_ya:
        nuevo_codigo = siguiente_codigo_variante(codigo_base)
        motivo = 'variante_nueva_creada'
    else:
        nuevo_codigo = clave_input
        motivo = 'producto_base_nuevo'

    # Construir defaults limpios (sin clave/nombre/presentacion)
    campos_permitidos = {
        k: v for k, v in defaults.items()
        if k not in ('clave', 'nombre', 'presentacion')
    }

    producto_nuevo = Producto.objects.create(
        clave=nuevo_codigo,
        nombre=str(nombre)[:500],
        presentacion=str(presentacion)[:200] if presentacion else None,
        **campos_permitidos,
    )

    logger.info(
        f"ISS-PROD-VAR: {'Variante' if existe_base_ya else 'Producto base'} creado. "
        f"Base={codigo_base}, Asignado={nuevo_codigo}, "
        f"Presentación=«{presentacion}»"
    )

    info.update({
        'codigo_asignado': nuevo_codigo,
        'es_variante': es_variante(nuevo_codigo),
        'motivo': motivo,
    })

    return (producto_nuevo, True, info)


# ===========================================================================
# SCRIPT DE MIGRACIÓN: detectar inconsistencias existentes
# ===========================================================================

def migrar_variantes_existentes(dry_run: bool = True) -> list:
    """
    Detecta y (opcionalmente) corrige productos con mismo código base pero
    distinta presentación en la base de datos existente.

    Parámetros
    ----------
    dry_run : bool (default True)
        Si True, sólo reporta los conflictos sin hacer cambios.
        Si False, renombra las variantes asignando sufijos .2, .3...

    Retorna
    -------
    list[dict] con los conflictos detectados/corregidos, cada uno con:
        - codigo_base
        - claves_afectadas: list de claves
        - presentaciones: list de presentaciones
        - accion: 'detectado' | 'corregido'

    USO:
        from core.utils.producto_variante import migrar_variantes_existentes
        conflictos = migrar_variantes_existentes(dry_run=True)
        for c in conflictos:
            print(c)
        # Si todo se ve bien:
        corregidos = migrar_variantes_existentes(dry_run=False)
    """
    from core.models import Producto

    resultados = []

    # Agrupar productos por codigo_base
    todos = list(
        Producto.objects.all().only('id', 'clave', 'nombre', 'presentacion')
        .order_by('clave')
    )

    grupos: dict[str, list] = {}
    for p in todos:
        base = extraer_codigo_base(p.clave)
        grupos.setdefault(base, []).append(p)

    for base, productos in grupos.items():
        if len(productos) <= 1:
            continue

        # Verificar si hay presentaciones diferentes
        presentaciones_norm = []
        for p in productos:
            n = normalizar_presentacion(p.presentacion or '')
            presentaciones_norm.append(n)

        unicas = set(presentaciones_norm)
        if len(unicas) <= 1:
            continue  # Todas iguales, sin conflicto

        # Hay múltiples presentaciones bajo el mismo base
        conflicto = {
            'codigo_base': base,
            'claves_afectadas': [p.clave for p in productos],
            'presentaciones': [p.presentacion for p in productos],
            'presentaciones_norm': presentaciones_norm,
            'accion': 'detectado',
        }

        if not dry_run:
            # Corregir: el primer producto (orden alfabético) se queda con el base,
            # los demás reciben sufijos .2, .3...
            productos_ordenados = sorted(productos, key=lambda x: x.clave)
            # Verificar cuál ya tiene el código base exacto
            base_exacto = next((p for p in productos_ordenados if p.clave == base), None)
            if not base_exacto and productos_ordenados:
                base_exacto = productos_ordenados[0]

            sufijo = 2
            with transaction.atomic():
                for p in productos_ordenados:
                    if p.pk == base_exacto.pk:
                        continue  # Este se queda como está
                    nuevo_codigo = f"{base}.{sufijo}"
                    while Producto.objects.filter(clave=nuevo_codigo).exists():
                        sufijo += 1
                        nuevo_codigo = f"{base}.{sufijo}"
                    p.clave = nuevo_codigo
                    p.save(update_fields=['clave'])
                    sufijo += 1

            conflicto['accion'] = 'corregido'
            logger.info(
                f"ISS-PROD-VAR: Migración corregió conflicto base={base}, "
                f"claves={conflicto['claves_afectadas']}"
            )

        resultados.append(conflicto)

    return resultados
