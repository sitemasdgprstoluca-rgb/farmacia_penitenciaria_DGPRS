/**
 * ProductosSkeleton - Plantilla de carga para módulo de Productos
 */

const ProductosSkeleton = () => {
  const SkeletonRow = () => (
    <tr className="animate-pulse">
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-20" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-48" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-24" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-16" /></td>
      <td className="px-4 py-3"><div className="h-6 bg-gray-200 rounded w-20" /></td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          <div className="h-8 w-8 bg-gray-200 rounded" />
          <div className="h-8 w-8 bg-gray-200 rounded" />
        </div>
      </td>
    </tr>
  );

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="bg-white rounded-lg p-4 shadow animate-pulse">
        <div className="flex flex-wrap gap-4">
          <div className="h-10 bg-gray-200 rounded w-64" />
          <div className="h-10 bg-gray-200 rounded w-40" />
          <div className="h-10 bg-gray-200 rounded w-32 ml-auto" />
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-16 animate-pulse" /></th>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-24 animate-pulse" /></th>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-20 animate-pulse" /></th>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-16 animate-pulse" /></th>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-16 animate-pulse" /></th>
              <th className="px-4 py-3 text-left"><div className="h-4 bg-gray-300 rounded w-20 animate-pulse" /></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="flex justify-between items-center animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-40" />
        <div className="flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 w-8 bg-gray-200 rounded" />
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProductosSkeleton;
