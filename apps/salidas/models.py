from django.db import models

# Ejemplo de modelo para salidas
class EjemploSalidas(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre
