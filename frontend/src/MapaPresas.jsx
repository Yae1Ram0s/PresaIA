// Mapa de ubicación y estado de las presas. SVG con d3-geo sobre el contorno de
// Natural Earth servido localmente (public/mapa/), de modo que funciona sin internet.
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { geoMercator, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";
import { Cargando, Icono, Tip } from "./componentes.jsx";
import { ETIQUETA, ICONO, fecha, pct, pp } from "./formato.js";

const ANCHO = 640;
const ALTO = 560;
const MARGEN_GRADOS = 2.5;
let topologiaCache = null;

export default function MapaPresas({ presas }) {
  const [topo, setTopo] = useState(topologiaCache);
  const [error, setError] = useState(null);
  const navegar = useNavigate();
  const [vista, setVista] = useState({ k: 1, x: 0, y: 0 });
  const arrastre = useRef(null);
  const svgRef = useRef(null);
  const conCoords = presas.filter((p) => p.latitud != null && p.longitud != null);

  useEffect(() => {
    if (topo) return;
    fetch("/mapa/north-america_50m.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Error ${r.status}`))))
      .then((t) => setTopo((topologiaCache = t)))
      .catch((e) => setError(e.message));
  }, [topo]);

  // Encuadre: todo México, o más si alguna presa queda fuera
  const proyeccion = useMemo(() => {
    const lats = conCoords.map((p) => p.latitud);
    const lons = conCoords.map((p) => p.longitud);
    const caja = {
      type: "MultiPoint",
      coordinates: [
        [Math.min(-118, ...lons.map((x) => x - MARGEN_GRADOS)), Math.min(10, ...lats.map((x) => x - MARGEN_GRADOS))],
        [Math.max(-86, ...lons.map((x) => x + MARGEN_GRADOS)), Math.max(36, ...lats.map((x) => x + MARGEN_GRADOS))],
      ],
    };
    return geoMercator().fitExtent([[4, 4], [ANCHO - 4, ALTO - 4]], caja);
  }, [conCoords.map((p) => p.clave).join()]); // eslint-disable-line react-hooks/exhaustive-deps

  const capas = useMemo(() => {
    if (!topo) return null;
    const ruta = geoPath(proyeccion);
    const o = topo.objects;
    return {
      tierra: ruta(feature(topo, o.land)),
      lagos: ruta(feature(topo, o.lakes)),
      fronteras: ruta(mesh(topo, o.countries, (a, b) => a !== b)),
      costas: ruta(feature(topo, o.coastlines)),
    };
  }, [topo, proyeccion]);

  if (!conCoords.length) {
    return <p className="tenue">Agrega latitud y longitud de cada presa en config.toml para ver el mapa.</p>;
  }
  if (error) return <p className="tenue">No se pudo cargar el contorno del mapa ({error}).</p>;
  if (!topo) return <div className="esqueleto-grafica" style={{ aspectRatio: `${ANCHO} / ${ALTO}` }}><Cargando texto="Cargando mapa…" /></div>;

  // Etiquetas: si dos presas quedan muy cerca, la de abajo baja su texto para no encimarse
  const colocadas = [];
  const puntos = conCoords
    .map((p) => ({ p, xy: proyeccion([p.longitud, p.latitud]) }))
    .sort((a, b) => a.xy[1] - b.xy[1])
    .map(({ p, xy }) => {
      let dy = 4;
      while (colocadas.some(([x, y]) => Math.abs(x - xy[0]) < 110 && Math.abs(y - (xy[1] + dy)) < 15)) dy += 15;
      colocadas.push([xy[0], xy[1] + dy]);
      return { p, xy, dy };
    });

  // Zoom: la vista es una escala k y un desplazamiento (x, y); el mapa nunca deja ver fuera de su marco
  const ajustar = (k, x, y) => {
    k = Math.min(Math.max(k, 1), 6);
    return { k, x: Math.min(0, Math.max(ANCHO * (1 - k), x)), y: Math.min(0, Math.max(ALTO * (1 - k), y)) };
  };
  const zoom = (factor) => setVista((v) => {
    const k = Math.min(Math.max(v.k * factor, 1), 6);
    const f = k / v.k; // se acerca hacia el centro del marco
    return ajustar(k, ANCHO / 2 - (ANCHO / 2 - v.x) * f, ALTO / 2 - (ALTO / 2 - v.y) * f);
  });
  const alBajar = (e) => {
    if (vista.k === 1 || e.target.closest(".mapa-presa")) return;
    arrastre.current = { cx: e.clientX, cy: e.clientY, ...vista };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const alMover = (e) => {
    const a = arrastre.current;
    if (!a) return;
    const esc = ANCHO / svgRef.current.getBoundingClientRect().width;
    setVista(ajustar(a.k, a.x + (e.clientX - a.cx) * esc, a.y + (e.clientY - a.cy) * esc));
  };
  const alSoltar = () => { arrastre.current = null; };

  const presentes = ["critico", "atencion", "normal"].filter((e) => conCoords.some((p) => p.estado === e));

  return (
    <div className="mapa">
      <div className="mapa-zoom" role="group" aria-label="Zoom del mapa">
        <button onClick={() => zoom(1.5)} disabled={vista.k >= 6} title="Acercar" aria-label="Acercar el mapa">
          <Icono nombre="lupa-mas" tam={15} />
        </button>
        <button onClick={() => zoom(1 / 1.5)} disabled={vista.k <= 1} title="Alejar" aria-label="Alejar el mapa">
          <Icono nombre="lupa-menos" tam={15} />
        </button>
        <button onClick={() => setVista({ k: 1, x: 0, y: 0 })} disabled={vista.k === 1} title="Restablecer vista"
          aria-label="Restablecer la vista del mapa">
          <Icono nombre="recargar" tam={13} />
        </button>
      </div>
      <svg ref={svgRef} viewBox={`0 0 ${ANCHO} ${ALTO}`} role="group" aria-label="Mapa de ubicación y estado de las presas"
        className={vista.k > 1 ? "mapa-movible" : ""}
        onPointerDown={alBajar} onPointerMove={alMover} onPointerUp={alSoltar} onPointerCancel={alSoltar}>
        <rect width={ANCHO} height={ALTO} className="mapa-mar" />
        {capas && (
          <g transform={`translate(${vista.x},${vista.y}) scale(${vista.k})`}>
            <path d={capas.tierra} className="mapa-tierra" />
            <path d={capas.lagos} className="mapa-mar" />
            <path d={capas.fronteras} className="mapa-frontera" />
            <path d={capas.costas} className="mapa-costa" />
          </g>
        )}
        {puntos.map(({ p, xy: [x, y], dy }) => (
          <Tip key={p.clave} como="g" className="mapa-presa" transform={`translate(${x * vista.k + vista.x},${y * vista.k + vista.y})`}
            tabIndex={0} role="link" aria-label={`${p.presa}: ${ETIQUETA[p.estado]}, llenado ${pct(p.llenado_pct)}`}
            onClick={() => navegar(`/presas/${p.clave}/consulta`)}
            onKeyDown={(e) => e.key === "Enter" && navegar(`/presas/${p.clave}/consulta`)}
            contenido={
              <>
                <b className="burbuja-titulo">{p.presa} <span className="tenue-chico">{p.clave} · {p.estado_rep}</span></b>
                <span><Icono nombre={ICONO[p.estado]} className={`estado-icono estado-icono-${p.estado}`} /> {ETIQUETA[p.estado]}</span>
                <span>Llenado actual: <b>{pct(p.llenado_pct)}</b> ({pp(p.cambio_30d_pp)} en 30 d)</span>
                {p.llenado_proyectado_pct != null && (
                  <span>Proyectado a {p.horizonte_max} días: <b>{pct(p.llenado_proyectado_pct)}</b></span>
                )}
                <span className="burbuja-ejemplo">Último dato {fecha(p.ultima_obs)} · clic para abrir</span>
              </>
            }>
            <circle r={8} className={`punto-${p.estado}`} />
            <text x={12} y={dy}>{p.presa}</text>
          </Tip>
        ))}
      </svg>
      <div className="mapa-leyenda">
        {presentes.map((e) => (
          <span key={e}><i className={`punto-${e}`} /> {ETIQUETA[e]}</span>
        ))}
      </div>
    </div>
  );
}
