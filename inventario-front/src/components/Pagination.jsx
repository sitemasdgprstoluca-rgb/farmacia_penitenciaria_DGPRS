function Pagination({
  page = 1,
  totalPages = 1,
  totalItems = 0,
  pageSize,
  onPageChange,
  onPageSizeChange,
}) {
  const goTo = (nextPage) => {
    if (!onPageChange) return;
    const target = Math.max(1, Math.min(totalPages || 1, nextPage));
    onPageChange(target);
  };

  const renderPages = () => {
    const pages = [];
    const maxButtons = 5;
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + maxButtons - 1);
    for (let p = start; p <= end; p += 1) {
      pages.push(
        <button
          type="button"
          key={p}
          onClick={() => goTo(p)}
          className={`px-3 py-1 rounded-lg border text-sm ${p === page ? 'bg-[#9F2241] text-white border-[#9F2241]' : 'bg-white text-gray-700 border-gray-200'}`}
          disabled={p === page}
        >
          {p}
        </button>
      );
    }
    return pages;
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-sm text-gray-600">
        {totalItems > 0
          ? `Mostrando ${Math.min((page - 1) * (pageSize || 1) + 1, totalItems)}-${Math.min(page * (pageSize || 1), totalItems)} de ${totalItems} registros`
          : 'No hay registros'}
      </p>
      <div className="flex items-center gap-2">
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="border rounded-lg px-2 py-1 text-sm text-gray-700"
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>
                {size} por página
              </option>
            ))}
          </select>
        )}
        <button
          type="button"
          onClick={() => goTo(page - 1)}
          disabled={page <= 1}
          className="rounded-full px-3 py-1 text-white disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #9F2241, #6B1839)' }}
        >
          Anterior
        </button>
        {renderPages()}
        <button
          type="button"
          onClick={() => goTo(page + 1)}
          disabled={page >= totalPages}
          className="rounded-full px-3 py-1 text-white disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #9F2241, #6B1839)' }}
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}

export default Pagination;
