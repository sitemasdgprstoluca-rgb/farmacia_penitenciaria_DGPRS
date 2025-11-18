from django.db import models

# Ejemplo de modelo para reportes
class EjemploReportes(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre
