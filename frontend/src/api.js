// Cliente de la API de Django. Todas las rutas son relativas: en desarrollo
// las atiende el proxy de Vite y en producción el mismo Django.
import { useEffect, useState, useSyncExternalStore } from "react";

// Peticiones en curso: alimentan la barra de carga superior
let enCurso = 0;
const oyentes = new Set();
const avisar = () => oyentes.forEach((f) => f());
function suscribir(f) {
  oyentes.add(f);
  return () => oyentes.delete(f);
}
/** Número de peticiones a la API en curso (se actualiza solo). */
export const usePeticionesEnCurso = () => useSyncExternalStore(suscribir, () => enCurso);

// Respuestas recientes: al volver a una pantalla se muestran al instante mientras se refrescan
const cache = new Map();
export const limpiarCache = () => cache.clear();

export async function obtener(ruta, params) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  enCurso++;
  avisar();
  try {
    const r = await fetch(`/api/${ruta}${qs}`);
    const datos = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(datos.error || `Error ${r.status} al consultar ${ruta}`);
    return datos;
  } catch (e) {
    throw e instanceof TypeError ? new Error("No hay conexión con el servidor. ¿Está corriendo Django?") : e;
  } finally {
    enCurso--;
    avisar();
  }
}

export function urlApi(ruta, params) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return `/api/${ruta}${qs}`;
}

/** Hook de carga: { datos, error, cargando, recargar }. Se vuelve a pedir cuando cambian ruta o parámetros. */
export function useApi(ruta, params) {
  const clave = ruta + JSON.stringify(params || {});
  const [intento, setIntento] = useState(0);
  const [estado, setEstado] = useState(() => {
    const previo = ruta && cache.get(clave);
    return { datos: previo ?? null, error: null, cargando: !previo };
  });
  useEffect(() => {
    if (!ruta) return;
    let vigente = true;
    // Mientras llega la respuesta se conservan los datos anteriores (la pantalla se atenúa, no parpadea)
    const previo = cache.get(clave);
    setEstado((e) => ({ datos: previo ?? e.datos, error: null, cargando: !previo }));
    obtener(ruta, params)
      .then((datos) => {
        cache.set(clave, datos);
        if (vigente) setEstado({ datos, error: null, cargando: false });
      })
      .catch((error) => vigente && setEstado({ datos: null, error: error.message, cargando: false }));
    return () => {
      vigente = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave, intento]);
  return { ...estado, recargar: () => setIntento((n) => n + 1) };
}
