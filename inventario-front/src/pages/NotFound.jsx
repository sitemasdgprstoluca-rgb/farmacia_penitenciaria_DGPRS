import { Link } from 'react-router-dom';
import { FaHome, FaExclamationTriangle } from 'react-icons/fa';

function NotFound() {
  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4"
      style={{
        background: 'linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)',
      }}
    >
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-amber-100 rounded-full mb-6">
            <FaExclamationTriangle className="text-5xl text-amber-500" />
          </div>
          <h1 className="text-6xl font-bold text-gray-800 mb-4">404</h1>
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">Página no encontrada</h2>
          <p className="text-gray-600 mb-8">
            Lo sentimos, la página que buscas no existe o ha sido movida.
          </p>
        </div>

        <div className="space-y-3">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 text-white rounded-lg font-semibold transition-all transform hover:scale-105 hover:shadow-lg bg-theme-gradient"
          >
            <FaHome />
            Ir al Dashboard
          </Link>
          <p className="text-sm text-gray-500 mt-4">
            Sistema Integral de Farmacia Penitenciaria
          </p>
        </div>
      </div>
    </div>
  );
}

export default NotFound;
