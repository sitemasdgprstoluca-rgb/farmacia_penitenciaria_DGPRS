# Test semaforo simulando frontend
from datetime import date, timedelta
from core.models import DetalleDonacion

def getSemaforoCaducidad(fecha_caducidad):
    if not fecha_caducidad:
        return {'estado': 'sin_fecha', 'label': 'Sin fecha', 'icono': '?'}
    
    hoy = date.today()
    dias = (fecha_caducidad - hoy).days
    
    if dias < 0:
        return {'estado': 'vencido', 'label': 'VENCIDO', 'icono': 'ROJO', 'dias': dias}
    elif dias <= 30:
        return {'estado': 'critico', 'label': 'CRITICO', 'icono': 'NARANJA', 'dias': dias}
    elif dias <= 90:
        return {'estado': 'proximo', 'label': 'PROXIMO', 'icono': 'AMARILLO', 'dias': dias}
    else:
        return {'estado': 'normal', 'label': 'VIGENTE', 'icono': 'VERDE', 'dias': dias}

def run():
    print('=== SIMULACION DE SEMAFORO FRONTEND ===')
    print('Fecha actual:', date.today())
    print()

    items = DetalleDonacion.objects.filter(numero_lote__startswith='LOTE-').select_related('producto_donacion', 'donacion')

    for item in items:
        semaforo = getSemaforoCaducidad(item.fecha_caducidad)
        print(item.numero_lote + ':')
        print('  Producto:', item.producto_donacion.clave)
        print('  Fecha caducidad:', item.fecha_caducidad)
        print('  Dias restantes:', semaforo.get('dias', 'N/A'))
        print('  Semaforo:', semaforo['icono'], semaforo['label'])
        print()

run()
