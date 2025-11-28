import { useEffect, useRef, useState } from "react";

const BarcodeScannerInput = ({ onCodigoDetectado, disabled = false }) => {
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!codigo.trim()) {
      setError("Ingresa un código de barras");
      return;
    }
    setError("");
    onCodigoDetectado?.(codigo.trim());
    setCodigo("");
  };

  const iniciarEscaneo = async () => {
    if (!("BarcodeDetector" in window)) {
      setError("El navegador no soporta escaneo nativo");
      return;
    }

    try {
      setError("");
      setScanning(true);
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      const detenerStream = () => {
        setScanning(false);
        if (videoRef.current?.srcObject) {
          videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
          videoRef.current.srcObject = null;
        }
      };

      const detector = new window.BarcodeDetector();

      const leer = async () => {
        if (!scanning) return;
        try {
          const codes = await detector.detect(videoRef.current);
          if (codes.length) {
            const codeValue = codes[0].rawValue;
            setCodigo(codeValue);
            onCodigoDetectado?.(codeValue);
            detenerStream();
            return;
          }
        } catch (err) {
          setError(err.message || "No se pudo leer el código");
        }
        requestAnimationFrame(leer);
      };

      videoRef.current?.addEventListener("pause", detenerStream, { once: true });
      leer();
    } catch (err) {
      setError(err.message || "No se pudo acceder a la cámara");
      setScanning(false);
    }
  };

  const cancelarEscaneo = () => {
    setScanning(false);
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
  };

  useEffect(() => () => cancelarEscaneo(), []);

  return (
    <div className="space-y-3">
      {!scanning && (
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            placeholder="Escanea o ingresa código..."
            disabled={disabled}
            className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none disabled:bg-gray-100"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <button
              type="submit"
              disabled={disabled}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition disabled:bg-gray-400"
            >
              Usar código
            </button>
            <button
              type="button"
              onClick={iniciarEscaneo}
              disabled={disabled}
              className="p-2 text-gray-600 hover:text-blue-600 transition disabled:text-gray-400"
              title="Escanear con cámara"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" />
              </svg>
            </button>
          </div>
        </form>
      )}

      {scanning && (
        <div className="relative bg-gray-900 rounded-lg overflow-hidden">
          <video ref={videoRef} className="w-full" autoPlay muted playsInline />
          <button
            type="button"
            onClick={cancelarEscaneo}
            className="absolute top-3 right-3 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition"
          >
            Cancelar
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
};

export default BarcodeScannerInput;
