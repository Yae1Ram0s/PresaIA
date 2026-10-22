import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { NavLink } from "react-router-dom";
import { usePeticionesEnCurso, useApi } from "./api.js";
import { ETIQUETA, ICONO, fecha, num } from "./formato.js";
import { GLOSARIO, normalizar } from "./glosario.js";

// ---------------------------------------------------------------------------
// Iconos (trazos al estilo Lucide, licencia ISC)
// ---------------------------------------------------------------------------
const TRAZOS = {
  buscar: ["M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "m21 21-4.3-4.3"],
  cerrar: ["M18 6 6 18", "m6 6 12 12"],
  info: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M12 16v-4", "M12 8h.01"],
  panorama: ["M3 3h7v9H3z", "M14 3h7v5h-7z", "M14 12h7v9h-7z", "M3 16h7v5H3z"],
  consulta: ["M12 8c5 0 9-1.3 9-3s-4-3-9-3-9 1.3-9 3 4 3 9 3z", "M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5", "M3 12c0 1.7 4 3 9 3s9-1.3 9-3"],
  prediccion: ["M22 7 13.5 15.5 8.5 10.5 2 17", "M16 7h6v6"],
  avisos: ["M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.3 21a1.94 1.94 0 0 0 3.4 0"],
  cargar: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "m17 8-5-5-5 5", "M12 3v12"],
  descargar: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "m7 10 5 5 5-5", "M12 15V3"],
  glosario: ["M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"],
  acerca: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3", "M12 17h.01"],
  recargar: ["M21 12a9 9 0 1 1-2.6-6.4L21 8", "M21 3v5h-5"],
  arriba: ["m18 15-6-6-6 6"],
  abajo: ["m6 9 6 6 6-6"],
  ordenar: ["m7 15 5 5 5-5", "m7 9 5-5 5 5"],
  gota: ["M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"],
  alerta: ["m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3", "M12 9v4", "M12 17h.01"],
  menu: ["M4 6h16", "M4 12h16", "M4 18h16"],
};

export function Icono({ nombre, tam = 18, className = "" }) {
  return (
    <svg className={`icono ${className}`} width={tam} height={tam} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {TRAZOS[nombre]?.map((d) => <path key={d} d={d} />)}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Tooltips: se dibujan en <body> para que ninguna tarjeta los recorte
// ---------------------------------------------------------------------------
function Burbuja({ id, ancla, children }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ top: -9999, left: -9999, abajo: false });
  useLayoutEffect(() => {
    const b = ref.current.getBoundingClientRect();
    const margen = 8;
    const abajo = ancla.top - b.height - margen < 0;
    const top = abajo ? ancla.bottom + margen : ancla.top - b.height - margen;
    const centro = ancla.left + ancla.width / 2 - b.width / 2;
    const left = Math.min(Math.max(centro, margen), window.innerWidth - b.width - margen);
    setPos({ top, left, abajo });
  }, [ancla]);
  return createPortal(
    <div ref={ref} id={id} role="tooltip" className={`burbuja${pos.abajo ? " abajo" : ""}`}
      style={{ top: pos.top, left: pos.left }}>
      {children}
    </div>,
    document.body,
  );
}

/** Envuelve cualquier elemento y muestra `contenido` al pasar el cursor, enfocar o tocar. */
export function Tip({ contenido, children, className = "", como: Etiqueta = "span", ...resto }) {
  const [ancla, setAncla] = useState(null);
  const ref = useRef(null);
  const id = useId();
  const mostrar = () => ref.current && setAncla(ref.current.getBoundingClientRect());
  const ocultar = () => setAncla(null);

  useEffect(() => {
    if (!ancla) return;
    const esc = (e) => e.key === "Escape" && ocultar();
    window.addEventListener("keydown", esc);
    window.addEventListener("scroll", ocultar, true);
    return () => {
      window.removeEventListener("keydown", esc);
      window.removeEventListener("scroll", ocultar, true);
    };
  }, [ancla]);

  if (!contenido) return children;
  return (
    <>
      <Etiqueta ref={ref} className={className} aria-describedby={ancla ? id : undefined}
        onMouseEnter={mostrar} onMouseLeave={ocultar} onFocus={mostrar} onBlur={ocultar} {...resto}>
        {children}
      </Etiqueta>
      {ancla && <Burbuja id={id} ancla={ancla}>{contenido}</Burbuja>}
    </>
  );
}

function ContenidoGlosario({ termino }) {
  const g = GLOSARIO[termino];
  if (!g) return null;
  return (
    <>
      <b className="burbuja-titulo">{g.titulo}</b>
      <span>{g.definicion}</span>
      {g.ejemplo && <span className="burbuja-ejemplo">Ejemplo: {g.ejemplo}</span>}
    </>
  );
}

/** Icono ⓘ con la explicación de un término del glosario o de un texto libre. */
export function Ayuda({ termino, texto }) {
  const contenido = termino ? <ContenidoGlosario termino={termino} /> : texto;
  const etiqueta = termino ? `¿Qué es ${GLOSARIO[termino]?.titulo}?` : "Más información";
  return (
    <Tip contenido={contenido} como="button" type="button" className="ayuda" aria-label={etiqueta}
      onClick={(e) => e.stopPropagation()}>
      <Icono nombre="info" tam={14} />
    </Tip>
  );
}

/** Texto subrayado con puntos que explica un término al pasar el cursor. */
export function Termino({ t, texto, children }) {
  const contenido = t ? <ContenidoGlosario termino={t} /> : texto;
  return (
    <Tip contenido={contenido} className="termino" tabIndex={0}>
      {children}
    </Tip>
  );
}

// ---------------------------------------------------------------------------
// Estados de carga
// ---------------------------------------------------------------------------
export const Cargando = ({ texto = "Cargando datos…" }) => (
  <div className="cargando" role="status">
    <span className="spinner" aria-hidden="true" />
    <span>{texto}</span>
  </div>
);

/** Bloque gris animado que ocupa el lugar del contenido mientras llega. */
export const Hueso = ({ ancho = "100%", alto = 16, redondo }) => (
  <span className={`hueso${redondo ? " redondo" : ""}`} style={{ width: ancho, height: alto }} aria-hidden="true" />
);

export const EsqueletoMetricas = ({ n = 4 }) => (
  <div className="metricas" aria-busy="true" aria-label="Cargando indicadores">
    {Array.from({ length: n }, (_, i) => (
      <div key={i} className="metrica">
        <Hueso ancho="60%" alto={14} />
        <Hueso ancho="45%" alto={32} />
        <Hueso ancho="35%" alto={12} />
      </div>
    ))}
  </div>
);

export const EsqueletoGrafica = ({ alto = 320, texto = "Preparando la gráfica…" }) => (
  <div className="esqueleto-grafica" style={{ height: alto }}>
    <Cargando texto={texto} />
  </div>
);

export const EsqueletoTabla = ({ filas = 4, columnas = 5 }) => (
  <div className="tabla-scroll" aria-busy="true">
    <table className="tabla">
      <tbody>
        {Array.from({ length: filas }, (_, i) => (
          <tr key={i}>
            {Array.from({ length: columnas }, (_, j) => (
              <td key={j}><Hueso ancho={j === 0 ? "70%" : "50%"} alto={14} /></td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

/** Barra fina en la parte superior mientras haya peticiones a la API en curso. */
export function BarraCarga() {
  const n = usePeticionesEnCurso();
  return <div className={`barra-carga${n > 0 ? " activa" : ""}`} aria-hidden="true" />;
}

// ---------------------------------------------------------------------------
// Avisos y estados
// ---------------------------------------------------------------------------
export function Aviso({ nivel = "informativo", children }) {
  return <div className={`caja caja-${nivel}`} role={nivel === "critico" ? "alert" : undefined}>{children}</div>;
}

export function ErrorCarga({ mensaje, reintentar }) {
  return (
    <Aviso nivel="critico">
      <div className="error-carga">
        <Icono nombre="alerta" />
        <div>
          <b>No se pudieron cargar los datos.</b>
          <p>{mensaje}</p>
        </div>
        {reintentar && (
          <button className="boton" onClick={reintentar}><Icono nombre="recargar" tam={16} /> Reintentar</button>
        )}
      </div>
    </Aviso>
  );
}

export function BandaDemo({ origen }) {
  if (origen !== "SINTETICO") return null;
  return (
    <Aviso nivel="atencion">
      ⚠️ <b>Datos de demostración (<Termino t="sintetico">sintéticos</Termino>).</b> Las cifras de esta pantalla NO
      describen la situación real. Descarga los datos del SIH y vuelve a entrenar para usar datos oficiales.
    </Aviso>
  );
}

export function Metrica({ titulo, valor, delta, ayuda, termino, neutro, nota }) {
  const signo = typeof delta === "string" ? delta.trim()[0] : null;
  const clase = neutro ? "" : signo === "+" ? "sube" : signo === "-" || signo === "−" ? "baja" : "";
  return (
    <div className="metrica">
      <div className="metrica-titulo">
        <span>{titulo}</span>
        {(termino || ayuda) && <Ayuda termino={termino} texto={ayuda} />}
      </div>
      <div className="metrica-valor">{valor}</div>
      {delta && <div className={`metrica-delta ${clase}`}>{clase === "sube" ? "▲ " : clase === "baja" ? "▼ " : ""}{delta}</div>}
      {nota && <div className="metrica-nota">{nota}</div>}
    </div>
  );
}

export const Estado = ({ nivel }) => (
  <Tip contenido={<ContenidoGlosario termino={nivel} />} className={`estado estado-${nivel}`}>
    {ICONO[nivel]} {ETIQUETA[nivel]}
  </Tip>
);

/** Explicación breve de para qué sirve la pantalla. */
export function Intro({ children }) {
  return <p className="intro">{children}</p>;
}

// ---------------------------------------------------------------------------
// Presa
// ---------------------------------------------------------------------------
const PESTANAS = [
  { ruta: "consulta", nombre: "Consulta", icono: "consulta", ayuda: "Situación actual e historia de la presa" },
  { ruta: "prediccion", nombre: "Predicción", icono: "prediccion", ayuda: "Cómo estará en 7, 15 y 30 días" },
  { ruta: "avisos", nombre: "Indicadores y avisos", icono: "avisos", ayuda: "Alertas según umbrales ajustables" },
];

/** Encabezado común a los módulos 1 a 3, con pestañas para saltar entre ellos. */
export function EncabezadoPresa({ clave }) {
  const { datos } = useApi(`presas/${clave}`);
  if (!datos) {
    return (
      <div className="encabezado-presa">
        <Hueso ancho="40%" alto={40} />
        <div className="chips"><Hueso ancho={120} alto={28} redondo /><Hueso ancho={160} alto={28} redondo /><Hueso ancho={140} alto={28} redondo /></div>
      </div>
    );
  }
  const p = datos.presa;
  return (
    <div className="encabezado-presa">
      <BandaDemo origen={datos.origen_datos} />
      <h1>{p.nombre}</h1>
      <div className="chips">
        <span className="chip">📍 {p.estado}</span>
        <Tip contenido={<ContenidoGlosario termino="sistema" />} className="chip" tabIndex={0}>
          Sistema {p.sistema}
        </Tip>
        <Tip contenido={<ContenidoGlosario termino="namo" />} className="chip" tabIndex={0}>
          Capacidad NAMO <b>{num(p.capacidad_namo_hm3)} hm³</b>
        </Tip>
        <span className="chip">Último dato <b>{fecha(datos.ultima_obs)}</b></span>
        <Tip contenido={<ContenidoGlosario termino={datos.origen_datos === "SINTETICO" ? "sintetico" : "sih"} />}
          className="chip" tabIndex={0}>
          Fuente <b>{datos.origen_datos}</b>
        </Tip>
      </div>
      <nav className="pestanas" aria-label="Módulos de la presa">
        {PESTANAS.map((m) => (
          <NavLink key={m.ruta} to={`/presas/${clave}/${m.ruta}`} title={m.ayuda}>
            <Icono nombre={m.icono} tam={16} /> {m.nombre}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function Descarga({ href, children, ayuda }) {
  return (
    <a className="boton" href={href} download title={ayuda}>
      <Icono nombre="descargar" tam={16} /> {children}
    </a>
  );
}

/** Marca en negritas la parte de `texto` que coincide con la búsqueda `q` (sin importar acentos). */
export function Resaltar({ texto, q }) {
  const s = String(texto ?? "");
  const i = q ? normalizar(s).indexOf(normalizar(q)) : -1;
  if (i < 0) return s;
  return (
    <>
      {s.slice(0, i)}
      <mark>{s.slice(i, i + q.length)}</mark>
      {s.slice(i + q.length)}
    </>
  );
}
