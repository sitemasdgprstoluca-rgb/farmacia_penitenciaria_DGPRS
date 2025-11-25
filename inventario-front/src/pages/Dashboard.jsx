import { useState, useEffect, useCallback } from 'react';
import {
  FaBox,
  FaWarehouse,
  FaExclamationTriangle,
  FaArrowUp,
  FaArrowDown,
  FaChartLine,
  FaExchangeAlt,
} from 'react-icons/fa';
import { usePermissions } from '../hooks/usePermissions';
import '../styles/Dashboard.css';
import apiClient from '../services/api';

const Dashboard = () => {
  const { getRolPrincipal, permisos } = usePermissions();
  const rolPrincipal = getRolPrincipal();
  const esVistaUser = rolPrincipal === 'VISTA_USER';

  const [kpis, setKpis] = useState({
    total_productos: 0,
    stock_total: 0,
    lotes_activos: 0,
    movimientos_mes: 0,
  });
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const applyMockDashboard = useCallback(() => {
    setKpis({
      total_productos: 124,
      stock_total: 4800,
      lotes_activos: 52,
      movimientos_mes: 37,
    });
    setMovimientos([
      {
        id: 1,
        tipo_movimiento: 'ENTRADA',
        producto__clave: 'MED-001',
        producto__descripcion: 'Paracetamol 500mg',
        lote__codigo_lote: 'LOTE-001',
        cantidad: 150,
        fecha_movimiento: new Date().toISOString(),
      },
      {
        id: 2,
        tipo_movimiento: 'SALIDA',
        producto__clave: 'MED-008',
        producto__descripcion: 'Ibuprofeno 400mg',
        lote__codigo_lote: 'LOTE-014',
        cantidad: 80,
        fecha_movimiento: new Date().toISOString(),
      },
    ]);
    setError(null);
    setLoading(false);
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Sesión no encontrada');
      }

      const response = await apiClient.get('/dashboard/');

      const nextKpis = response.data.kpi || {
        total_productos: 0,
        stock_total: 0,
        lotes_activos: 0,
        movimientos_mes: 0,
      };

      setKpis(
        esVistaUser
          ? {
              lotes_activos: nextKpis.lotes_activos,
              stock_total: nextKpis.stock_total,
            }
          : nextKpis,
      );

      const movimientosData = response.data.ultimos_movimientos || [];
      setMovimientos(
        esVistaUser ? movimientosData.filter((mov) => mov.producto__clave) : movimientosData,
      );
    } catch (err) {
      console.error('Error al cargar dashboard:', err);
      if (err.response?.status === 401) {
        setError('Sesion expirada. Inicia sesion nuevamente.');
      } else {
        setError(err.response?.data?.error || err.message || 'Error al cargar el dashboard');
      }
      setKpis({
        total_productos: 0,
        stock_total: 0,
        lotes_activos: 0,
        movimientos_mes: 0,
      });
      setMovimientos([]);
    } finally {
      setLoading(false);
    }
  }, [applyMockDashboard, esVistaUser]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const formatFecha = (fecha) =>
    new Date(fecha).toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });

  if (!permisos?.verProductos) {
    return (
      <div className="dashboard-container">
        <div className="error-alert">No tiene permisos para ver el dashboard.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">
          <div className="spinner" />
          <p>Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'TOTAL',
      subtitle: 'PRODUCTOS',
      value: kpis.total_productos || 10,
      subtext: 'Activos',
      icon: FaBox,
      gradient: 'linear-gradient(135deg, #9F2241 0%, #7D1B35 100%)',
      iconBg: '#9F2241',
      badge: '↑ 12%',
      badgeColor: '#10B981',
      show: permisos.verProductos,
    },
    {
      title: 'STOCK TOTAL',
      subtitle: '',
      value: kpis.stock_total || 0,
      subtext: 'Unidades',
      icon: FaChartLine,
      gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
      iconBg: '#10B981',
      badge: '↑ 6%',
      badgeColor: '#10B981',
      show: permisos.verLotes,
    },
    {
      title: 'LOTES ACTIVOS',
      subtitle: '',
      value: kpis.lotes_activos || 0,
      subtext: 'Con stock',
      icon: FaWarehouse,
      gradient: 'linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)',
      iconBg: '#06B6D4',
      badge: '≈ 0%',
      badgeColor: '#6B7280',
      show: permisos.verRequisiciones,
    },
    {
      title: 'MOVIMIENTOS',
      subtitle: '',
      value: kpis.movimientos_mes || 0,
      subtext: 'Este mes',
      icon: FaExchangeAlt,
      gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
      iconBg: '#F59E0B',
      badge: '↑ 15%',
      badgeColor: '#10B981',
      show: permisos.verCentros,
    },
  ];

  return (
    <div className="dashboard-container">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold" style={{ color: '#6B1839' }}>
            Panel de Control
          </h1>
          <p className="text-base mt-2" style={{ color: '#6B7280' }}>
            Resumen general del sistema de inventario
          </p>
        </div>
        <div
          className="px-5 py-2.5 rounded-2xl font-semibold text-sm"
          style={{ background: 'linear-gradient(135deg, #9F2241 0%, #6B1839 100%)', color: 'white' }}
        >
          <span>
            {new Date().toLocaleDateString('es-MX', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </span>
        </div>
      </div>

      {error && (
        <div className="error-alert">
          <FaExclamationTriangle />
          <div>
            <strong>Error de conexión con el backend</strong>
            <p>{error}</p>
            <button onClick={loadDashboard} className="btn btn-primary">
              Reintentar
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards
          .filter((card) => card.show)
          .map((card, index) => {
            const Icon = card.icon;
            return (
              <div
                key={index}
                className="bg-white rounded-xl shadow-lg p-6 border-l-4 hover:shadow-2xl transition-all transform hover:-translate-y-1"
                style={{ borderLeftColor: card.iconBg }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <p className="text-xs font-bold mb-1" style={{ color: '#6B7280', letterSpacing: '0.5px' }}>
                      {card.title}
                    </p>
                    {card.subtitle && (
                      <p className="text-xs font-semibold" style={{ color: '#9CA3AF' }}>
                        {card.subtitle}
                      </p>
                    )}
                  </div>
                  <div className="rounded-xl p-3 shadow-md" style={{ background: card.gradient }}>
                    <Icon className="text-white text-2xl" />
                  </div>
                </div>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-4xl font-bold" style={{ color: '#1F2937' }}>
                      {card.value}
                    </p>
                    <p className="text-sm font-medium mt-1" style={{ color: '#6B7280' }}>
                      {card.subtext}
                    </p>
                  </div>
                  <div className="px-3 py-1 rounded-full text-xs font-bold text-white" style={{ backgroundColor: card.badgeColor }}>
                    {card.badge}
                  </div>
                </div>
              </div>
            );
          })}
      </div>

      {!esVistaUser && (
        <div className="dashboard-section">
          <div className="section-header">
            <h3>
              <FaExchangeAlt /> Últimos Movimientos
            </h3>
            <span className="badge-count">{movimientos.length} registros</span>
          </div>

          <div className="movements-container">
            {movimientos.length === 0 ? (
              <div className="empty-state">
                <FaExclamationTriangle />
                <p>No hay movimientos registrados</p>
              </div>
            ) : (
              <div className="movements-list">
                {movimientos.map((mov, index) => (
                  <div key={mov.id || index} className={`movement-item ${mov.tipo_movimiento.toLowerCase()}`}>
                    <div className="movement-number">{index + 1}</div>
                    <div className="movement-type">
                      <span className={`type-badge ${mov.tipo_movimiento.toLowerCase()}`}>
                        {mov.tipo_movimiento === 'ENTRADA' ? <FaArrowDown /> : <FaArrowUp />}
                        {mov.tipo_movimiento}
                      </span>
                    </div>
                    <div className="movement-product">
                      <strong>{mov.producto__clave}</strong>
                      <p>{mov.producto__descripcion}</p>
                    </div>
                    <div className="movement-lote">
                      <span className="label">Lote:</span>
                      <span className="value">{mov.lote__codigo_lote}</span>
                    </div>
                    <div className="movement-quantity">
                      <span className="quantity-value">{mov.cantidad}</span>
                      <span className="quantity-label">unidades</span>
                    </div>
                    <div className="movement-date">{formatFecha(mov.fecha_movimiento)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;






