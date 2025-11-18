# filepath: backend/middleware.py
from django.shortcuts import redirect


class RedirectNonSuperuserFromAdminMiddleware:
    """
    - Si es usuario autenticado NO superusuario y entra a /admin/,
      lo mandamos al front (post_login).
    - PERO dejamos pasar /admin/logout/ para que sí pueda cerrar sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith("/admin/"):
            # 👇 SIEMPRE permitir el logout
            if path.startswith("/admin/logout"):
                return self.get_response(request)

            user = request.user

            # Usuario logueado y NO superusuario -> fuera del admin
            if user.is_authenticated and not user.is_superuser:
                return redirect("post_login")

        return self.get_response(request)
