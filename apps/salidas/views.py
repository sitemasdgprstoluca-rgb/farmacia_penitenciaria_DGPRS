from django.http import HttpResponse

def home(request):
    return HttpResponse('✅ Módulo salidas funcionando correctamente.')
