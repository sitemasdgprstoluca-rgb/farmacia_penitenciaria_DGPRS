export default function AccesoRestringido() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#8A1538]">
      <div className="bg-[#6E102D] text-center text-[#FFEBD2] px-10 py-8 rounded-3xl shadow-2xl max-w-md w-full">
        <h1 className="text-2xl font-bold mb-3">Acceso restringido al sistema</h1>
        <p className="text-sm mb-6 leading-relaxed">
          Debes iniciar sesión para utilizar el Sistema de Control de Inventario de Farmacia.
        </p>

        {/* Enlace directo al login del panel administrativo de Django */}
        <a
          href="http://localhost:8000/admin/login/?next=/post-login/"
          className="inline-block px-5 py-2.5 rounded-full bg-[#FFEBD2] text-[#8A1538] text-sm font-semibold shadow hover:bg-[#F8D9AF] transition"
        >
          Ir a pantalla de acceso
        </a>

        <p className="text-[11px] mt-4 opacity-80">
          Usa tu usuario de <strong>Administrador</strong>, <strong>Farmacia</strong> o <strong>Consulta</strong>.
        </p>
      </div>
    </div>
  );
}






