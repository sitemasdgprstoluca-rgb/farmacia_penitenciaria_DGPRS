import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import "./index.css";

// Suprimir errores de promesas no capturadas que son errores esperados:
// - Errores de red/API de axios (tienen .isAxiosError o .response)
// - CONFIRMATION_REQUIRED del guard de DELETE
// - Errores de conexión en cold-start de Render
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason;
  if (
    reason?.isAxiosError || // cualquier error de Axios
    reason?.response || // error de axios con respuesta HTTP
    reason?.message === 'CONFIRMATION_REQUIRED' || // guard de DELETE sin confirmación
    reason?.code === 'ERR_NETWORK' || // error de red
    reason?.code === 'ECONNABORTED' || // timeout
    reason?.code === 'ERR_CONNECTION_CLOSED' || // conexión cerrada (Render cold start)
    reason?.code === 'ERR_CONNECTION_RESET' || // conexión reseteada
    reason?.code === 'ERR_CONNECTION_REFUSED' || // conexión rechazada
    reason?.code === 'ECONNREFUSED' || // conexión rechazada (Node)
    reason?.code === 'ERR_BAD_RESPONSE' || // respuesta malformada
    reason?.code === 'ERR_BAD_REQUEST' || // request malformado
    reason?.message?.includes('Network Error') || // error de red genérico
    reason?.message?.includes('timeout') || // timeout genérico
    (typeof reason === 'object' && reason !== null && 'status_code' in reason) // objeto error del backend
  ) {
    event.preventDefault(); // evitar log rojo en consola
  }
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
