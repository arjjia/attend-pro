import { useEffect, useId, useState } from "react";

import type { Html5Qrcode } from "html5-qrcode";

import { parseAttendanceCode } from "../lib/attendance";

interface QrScannerProps {
  onCode: (code: string) => void;
}

export function QrScanner({ onCode }: QrScannerProps) {
  const scannerId = `qr-reader-${useId().replace(/:/g, "")}`;
  const [error, setError] = useState("");

  useEffect(() => {
    let disposed = false;
    let scanner: Html5Qrcode | null = null;

    async function startScanner() {
      try {
        const { Html5Qrcode: Scanner } = await import("html5-qrcode");
        if (disposed) return;
        scanner = new Scanner(scannerId);
        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 230, height: 230 } },
          (decodedText) => {
            const code = parseAttendanceCode(decodedText);
            if (code) onCode(code);
          },
          () => undefined,
        );
      } catch {
        if (!disposed) setError("Не удалось включить камеру. Разрешите доступ или введите код вручную.");
      }
    }
    void startScanner();

    return () => {
      disposed = true;
      const activeScanner = scanner;
      if (activeScanner?.isScanning) {
        void activeScanner.stop().then(() => activeScanner.clear()).catch(() => undefined);
      } else {
        activeScanner?.clear();
      }
    };
  }, [onCode, scannerId]);

  return (
    <div className="scanner-panel">
      <div id={scannerId} className="qr-reader" aria-label="Область сканирования QR-кода" />
      {error && <p className="field-error" role="alert">{error}</p>}
    </div>
  );
}
