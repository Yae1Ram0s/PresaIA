// Botón «Actualizar»: pide a Django que descargue el SIH con Chromium en segundo plano
// y consulta el avance cada pocos segundos hasta que termina.
import { useEffect, useState } from "react";
import { obtener } from "./api.js";
import { Icono } from "./componentes.jsx";

export default function BotonActualizar({ alTerminar, onMensajeChange }) {
  const [tarea, setTarea] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtener("actualizar").then(setTarea).catch(() => {}); // por si ya había una en curso
  }, []);

  useEffect(() => {
    if (!tarea?.en_curso) return;
    const t = setInterval(async () => {
      try {
        const nueva = await obtener("actualizar");
        setTarea(nueva);
        if (!nueva.en_curso && nueva.ok) alTerminar?.();
      } catch (e) {
        setError(e.message);
      }
    }, 3000);
    return () => clearInterval(t);
  }, [tarea?.en_curso, alTerminar]);

  async function iniciar() {
    setError(null);
    const r = await fetch("/api/actualizar", { method: "POST" });
    const datos = await r.json().catch(() => ({}));
    if (!r.ok && r.status !== 409) setError(datos.error || `Error ${r.status}`);
    setTarea(datos);
  }

  const enCurso = tarea?.en_curso;
  const mensaje = error || (enCurso ? tarea.mensaje : tarea?.fin && tarea.mensaje);
  const fallo = error || tarea?.ok === false;

  useEffect(() => {
    onMensajeChange(mensaje ? { texto: mensaje, fallo: Boolean(fallo) } : null);
  }, [mensaje, fallo, onMensajeChange]);

  return (
    <span className="actualizar">
      <button className="boton" disabled={enCurso} onClick={iniciar}>
        {enCurso ? "Actualizando…" : <><Icono nombre="recargar" tam={15} /> Actualizar</>}
      </button>
    </span>
  );
}
