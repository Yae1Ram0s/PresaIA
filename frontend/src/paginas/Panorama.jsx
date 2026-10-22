import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { urlApi, useApi } from "../api.js";
import {
  Ayuda, BandaDemo, Descarga, ErrorCarga, EsqueletoGrafica, EsqueletoMetricas, EsqueletoTabla, Estado, Hueso, Icono,
  Intro, Metrica, Resaltar, Termino,
} from "../componentes.jsx";
import MapaPresas from "../MapaPresas.jsx";
import { COLORES, ETIQUETA, fecha, fechaCorta, num, pct, pp } from "../formato.js";
import { normalizar } from "../glosario.js";

const GRAVEDAD = { critico: 0, atencion: 1, informativo: 2, normal: 3 };

function MiniSerie({ valores }) {
  const datos = valores.map((y, i) => ({ i, y }));
  return (
    <ResponsiveContainer width={110} height={28}>
      <LineChart data={datos}>
        <YAxis hide domain={[0, 100]} />
        <Line dataKey="y" dot={false} stroke="var(--serie-1)" strokeWidth={1.5} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Barra({ valor, umbrales }) {
  const nivel = valor < umbrales.llenado_critico_pct ? "critico" : valor < umbrales.llenado_atencion_pct ? "atencion" : "normal";
  return (
    <div className="barra" title={`Llenado actual: ${pct(valor)}`}>
      <div className={`barra-${nivel}`} style={{ width: `${Math.min(Math.max(valor || 0, 0), 100)}%` }} />
      <span>{pct(valor)}</span>
    </div>
  );
}

/** Nombres de las presas en un estado, cada uno enlazado a su detalle. */
function PresasEn({ presas, nivel }) {
  const lista = presas.filter((p) => p.estado === nivel);
  if (!lista.length) return "Ninguna";
  return (
    <span className="presas-en">
      {lista.map((p) => (
        <Link key={p.clave} to={`/presas/${p.clave}/consulta`} title={`${p.estado_rep} · llenado ${pct(p.llenado_pct)}`}>
          {p.presa}
        </Link>
      ))}
    </span>
  );
}

/** Tooltip de la gráfica comparativa: presas ordenadas de mayor a menor llenado. */
function TooltipComparativo({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const filas = [...payload].filter((p) => p.value != null).sort((a, b) => b.value - a.value);
  return (
    <div className="tooltip-grafica">
      <b>{fecha(label)}</b>
      {filas.map((p) => (
        <div key={p.dataKey} className="tooltip-fila">
          <i style={{ background: p.color }} /> {p.name} <span>{pct(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

// Columnas ordenables de la tabla: [campo, título, término del glosario, numérica]
const COLUMNAS = [
  ["estado", "Estado", "estado_presa"],
  ["presa", "Presa"],
  ["estado_rep", "Entidad"],
  ["llenado_pct", "Llenado", "llenado", true],
  [null, "Últimos 90 días", null],
  ["cambio_30d_pp", "Δ 30 días", "delta", true],
  ["llenado_proyectado_pct", "Proyectado", "proyectado", true],
  ["cambio_proyectado_pp", "Δ proyectado", "delta", true],
  ["aviso_principal", "Aviso principal"],
  ["ultima_obs", "Último dato"],
];

function TablaPresas({ presas, umbrales, hmax }) {
  const navegar = useNavigate();
  const [q, setQ] = useState("");
  const [filtro, setFiltro] = useState("todos");
  const [orden, setOrden] = useState({ campo: "estado", asc: true });

  const conteo = (e) => presas.filter((p) => p.estado === e).length;
  const n = normalizar(q.trim());
  const filas = presas
    .filter((p) => (filtro === "todos" || p.estado === filtro) &&
      normalizar(`${p.presa} ${p.estado_rep} ${p.clave} ${p.sistema}`).includes(n))
    .sort((a, b) => {
      const { campo, asc } = orden;
      let x = campo === "estado" ? GRAVEDAD[a.estado] : a[campo];
      let y = campo === "estado" ? GRAVEDAD[b.estado] : b[campo];
      // Empate en estado: primero el menor llenado proyectado (el orden original de riesgo)
      if (campo === "estado" && x === y) [x, y] = [a.llenado_proyectado_pct, b.llenado_proyectado_pct];
      if (x == null) return 1;
      if (y == null) return -1;
      const r = typeof x === "string" ? x.localeCompare(y, "es") : x - y;
      return asc ? r : -r;
    });

  const ordenarPor = (campo) =>
    setOrden((o) => ({ campo, asc: o.campo === campo ? !o.asc : true }));

  return (
    <>
      <div className="filtros">
        <div className="buscador-caja">
          <Icono nombre="buscar" tam={16} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filtrar por presa, estado o sistema…"
            aria-label="Filtrar presas" />
          {q && (
            <button className="buscador-limpiar" onClick={() => setQ("")} aria-label="Borrar filtro">
              <Icono nombre="cerrar" tam={14} />
            </button>
          )}
        </div>
        <div className="segmentado" role="group" aria-label="Filtrar por estado">
          {["todos", "critico", "atencion", "normal"].map((e) => (
            <button key={e} className={filtro === e ? "activo" : ""} onClick={() => setFiltro(e)}>
              {e === "todos" ? `Todos (${presas.length})` : `${ETIQUETA[e]} (${conteo(e)})`}
            </button>
          ))}
        </div>
      </div>

      <div className="tabla-scroll">
        <table className="tabla clicable">
          <thead>
            <tr>
              {COLUMNAS.map(([campo, titulo, termino, numerica]) => {
                const t = campo === "llenado_proyectado_pct" && hmax ? `${titulo} ${hmax} d` : titulo;
                const activa = orden.campo === campo;
                return (
                  <th key={titulo} className={numerica ? "num" : ""}
                    aria-sort={activa ? (orden.asc ? "ascending" : "descending") : undefined}>
                    <span className="th-contenido">
                      {campo ? (
                        <button className={`ordenar${activa ? " activa" : ""}`} onClick={() => ordenarPor(campo)}
                          title={`Ordenar por ${titulo.toLowerCase()}`}>
                          {t}
                          <Icono nombre={activa ? (orden.asc ? "arriba" : "abajo") : "ordenar"} tam={12} />
                        </button>
                      ) : t}
                      {termino && <Ayuda termino={termino} />}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {filas.map((p) => (
              <tr key={p.clave} tabIndex={0} onClick={() => navegar(`/presas/${p.clave}/consulta`)}
                onKeyDown={(e) => e.key === "Enter" && navegar(`/presas/${p.clave}/consulta`)}
                title={`Abrir el detalle de ${p.presa}`}>
                <td><Estado nivel={p.estado} /></td>
                <td><b><Resaltar texto={p.presa} q={q.trim()} /></b><div className="tenue-chico">{p.clave}</div></td>
                <td><Resaltar texto={p.estado_rep} q={q.trim()} /></td>
                <td><Barra valor={p.llenado_pct} umbrales={umbrales} /></td>
                <td><MiniSerie valores={p.historia_90d} /></td>
                <td className={`num ${p.cambio_30d_pp > 0 ? "sube" : p.cambio_30d_pp < 0 ? "baja" : ""}`}>{pp(p.cambio_30d_pp)}</td>
                <td className="num">{pct(p.llenado_proyectado_pct)}</td>
                <td className={`num ${p.cambio_proyectado_pp > 0 ? "sube" : p.cambio_proyectado_pp < 0 ? "baja" : ""}`}>
                  {pp(p.cambio_proyectado_pp)}
                </td>
                <td>{p.aviso_principal || <span className="tenue">Sin avisos</span>}</td>
                <td>{fecha(p.ultima_obs)}</td>
              </tr>
            ))}
            {filas.length === 0 && (
              <tr><td colSpan={COLUMNAS.length} className="vacio">Ninguna presa coincide con el filtro.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Panorama() {
  const { datos, error, cargando, recargar } = useApi("panorama");

  if (cargando) {
    return (
      <>
        <h1>Panorama general</h1>
        <Hueso ancho="70%" alto={14} />
        <EsqueletoMetricas n={5} />
        <div className="columnas columnas-panorama">
          <EsqueletoGrafica alto={340} texto="Cargando mapa…" />
          <EsqueletoGrafica alto={340} texto="Calculando el último año…" />
        </div>
        <EsqueletoTabla filas={3} columnas={8} />
      </>
    );
  }
  if (error) return <ErrorCarga mensaje={error} reintentar={recargar} />;
  const g = datos.indicadores;
  const u = datos.umbrales;
  const hmax = Math.max(...datos.presas.map((p) => p.horizonte_max || 0)) || null;

  return (
    <>
      {g.hay_sinteticos && <BandaDemo origen="SINTETICO" />}
      <h1>Panorama general</h1>
      <Intro>
        Resumen de las {g.presas} presas monitoreadas: cuánta agua tienen hoy, cómo se espera que estén en {hmax ?? "los próximos"}{" "}
        días y cuáles requieren atención. Haz clic en una presa (en el mapa o en la tabla) para ver su detalle.
      </Intro>
      <p className="tenue">
        Capacidad conjunta {num(g.capacidad_total_hm3, 0)} <Termino t="hm3">hm³</Termino> · última observación{" "}
        {fecha(g.ultima_obs)} · umbrales de llenado:{" "}
        <Termino t="umbral_llenado_atencion">atención &lt; {u.llenado_atencion_pct} %</Termino>,{" "}
        <Termino t="umbral_llenado_critico">crítico &lt; {u.llenado_critico_pct} %</Termino>
      </p>

      <div className="metricas">
        <Metrica
          titulo="Almacenamiento conjunto"
          valor={pct(g.llenado_conjunto_pct)}
          termino="almacenamiento_conjunto"
          nota={`${num(g.volumen_total_hm3, 0)} de ${num(g.capacidad_total_hm3, 0)} hm³`}
        />
        <Metrica
          titulo={hmax ? `Proyección conjunta a ${hmax} días` : "Proyección conjunta"}
          valor={pct(g.llenado_conjunto_proyectado_pct)}
          termino="proyectado"
          delta={
            g.llenado_conjunto_proyectado_pct != null
              ? pp(g.llenado_conjunto_proyectado_pct - g.llenado_conjunto_actual_con_pron_pct)
              : null
          }
        />
        <Metrica titulo="Estado crítico" valor={`🔴 ${g.en_critico}`} termino="critico"
          nota={<PresasEn presas={datos.presas} nivel="critico" />} />
        <Metrica titulo="Atención" valor={`🟠 ${g.en_atencion}`} termino="atencion"
          nota={<PresasEn presas={datos.presas} nivel="atencion" />} />
        <Metrica titulo="Normal" valor={`🟢 ${g.normales}`} termino="normal"
          nota={<PresasEn presas={datos.presas} nivel="normal" />} />
      </div>

      <div className="columnas columnas-panorama">
        <section>
          <h2>Ubicación y estado <Ayuda texto="Cada punto es una presa, coloreada según su estado. Pasa el cursor para ver su llenado y haz clic para abrirla." /></h2>
          <div className="grafica">
            <MapaPresas presas={datos.presas} />
          </div>
        </section>
        <section>
          <h2>Llenado en el último año <Ayuda texto="Porcentaje de llenado diario de cada presa durante los últimos 12 meses. Las líneas punteadas son los umbrales de atención (naranja) y crítico (rojo). Haz clic en un nombre de la leyenda para resaltarlo." /></h2>
          <div className="grafica">
            <GraficaComparativa datos={datos} u={u} />
          </div>
        </section>
      </div>

      <h2>Presas ordenadas por riesgo</h2>
      <p className="tenue">
        Haz clic en una fila para abrir el detalle, o en el título de una columna para ordenar. Por defecto se muestran
        primero los estados más graves y, dentro de cada estado, el menor llenado proyectado.
      </p>
      <TablaPresas presas={datos.presas} umbrales={u} hmax={hmax} />
      <div className="acciones">
        <Descarga href={urlApi("panorama.csv")} ayuda="Tabla completa para abrir en Excel">Descargar panorama (CSV)</Descarga>
      </div>
    </>
  );
}

function GraficaComparativa({ datos, u }) {
  const [resaltada, setResaltada] = useState(null);
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={datos.comparativo} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--rejilla)" vertical={false} />
        <XAxis dataKey="fecha" tickFormatter={fechaCorta} minTickGap={40} stroke="var(--tenue)" />
        <YAxis domain={[0, 100]} unit=" %" stroke="var(--tenue)" width={52} />
        <Tooltip content={<TooltipComparativo />} />
        <Legend onClick={(e) => setResaltada((r) => (r === e.dataKey ? null : e.dataKey))}
          wrapperStyle={{ cursor: "pointer" }} />
        <ReferenceLine y={u.llenado_atencion_pct} stroke="var(--atencion)" strokeDasharray="4 4" />
        <ReferenceLine y={u.llenado_critico_pct} stroke="var(--critico)" strokeDasharray="4 4" />
        {datos.presas.map((p, i) => (
          <Line
            key={p.clave}
            dataKey={p.clave}
            name={p.presa}
            dot={false}
            stroke={COLORES[i % COLORES.length]}
            strokeWidth={resaltada === p.clave ? 3 : 2}
            strokeOpacity={resaltada && resaltada !== p.clave ? 0.2 : 1}
            connectNulls
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
