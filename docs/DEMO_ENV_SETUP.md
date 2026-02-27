# Preparación del Entorno Demo — Farmacia Penitenciaria

Propósito: Proveer un entorno reproducible para grabar demos y validar flujos (incluyendo restablecer contraseña).

Requisitos previos
- Git
- Node 18+ / npm
- Python 3.12
- SQLite (opcional) o PostgreSQL si prefieres
- Tener el repositorio clonado y branches actualizados (`dev`/`main`)

Estructura (resumen)
- Backend: `backend/`
- Frontend: `inventario-front/`
- DB por defecto: `backend/db.sqlite3` (hay `db.sqlite3.backup` disponible)

1) Backend — crear entorno y levantar
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Si quieres partir de datos limpios, reemplaza la DB por el backup
copy db.sqlite3.backup db.sqlite3
# Si prefieres crear usuarios manualmente:
python manage.py migrate
python manage.py createsuperuser --username=admin_demo --email=admin@example.com
# Opcional: cargar fixtures si existen
# python manage.py loaddata fixtures/demo_data.json
python manage.py runserver
```
- Endpoint API base recomendado para frontend local: `http://localhost:8000/api`

2) Frontend — instalar y correr en modo dev
```powershell
cd inventario-front
npm install
npm run dev   # abre Vite en localhost:5173 por defecto
```
- Alternativa build (para comprobar archivos estáticos):
```powershell
npm run build
npm run preview
```

3) Variables de entorno útiles
- Backend: `.env` o variables del entorno (si usas servicios externos)
  - `RESEND_API_KEY` (si pruebas envío real de correo en demo)
  - `DJANGO_SETTINGS_MODULE` según tu configuración
- Frontend: archivo `.env` en `inventario-front` con:
```
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME="Farmacia Penitenciaria Demo"
```

4) Cuentas de prueba (crear desde Django shell o admin)
- Centro (usuario_centro@example.com) — rol: centro
- Encargado (encargado_centro@example.com) — rol: encargado
- Farmacia local (farmacia_local@example.com) — rol: farmacia_local
- Coordinador (coordinador@example.com) — rol: coordinador
- Farmacia Central / Admin (admin_demo@example.com) — superuser

Comandos útiles para crear usuarios en Django shell:
```python
# python manage.py shell
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_user('centro', 'usuario_centro@example.com', 'Password123!')
User.objects.create_user('encargado', 'encargado_centro@example.com', 'Password123!')
User.objects.create_user('farmacia', 'farmacia_local@example.com', 'Password123!')
User.objects.create_superuser('admin_demo', 'admin_demo@example.com', 'AdminPass123!')
```

5) Datos de inventario (sugerencias)
- Si existe un script `fixtures` úsalo. Si no, crear manualmente algunos productos, lotes y existencias vía admin.
- Crear 5–10 productos y asignar lotes con distintas fechas de caducidad para mostrar trazabilidad.

6) Correo y enlaces de restablecimiento
- En demo local normalmente se usa consola: `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` para ver el contenido del correo en la consola.
- Para probar el link real en ambiente público (Render), asegúrate que `VITE_API_URL` apunte al backend desplegado y que Render tenga las variables necesarias.

7) Endpoints que deberás probar manualmente durante la grabación
- Inicio de sesión: `/login`
- Solicitar recuperación: `/recuperar-password`
- Enlace enviado -> `/restablecer-password?uid=<uid>&token=<token>`
- Confirmar nueva contraseña: POST a la API `password/confirm`

8) Consejos para grabación
- Usa ventana de incógnito para evitar cache y sesión previa
- Define cuentas de demostración con contraseñas cortas (solo demo) y que cumplan requisitos
- Ten abierta la consola del backend (para ver token/email si usas console backend)
- Usa resolución 1920x1080 para video y escala UI por defecto

9) Limpieza después de demo
- Reemplaza `db.sqlite3` con backup si deseas limpiar los datos:
```powershell
copy db.sqlite3.backup db.sqlite3
```

---
Archivo de referencia: `docs/DEMO_ENV_SETUP.md` creado automáticamente.
