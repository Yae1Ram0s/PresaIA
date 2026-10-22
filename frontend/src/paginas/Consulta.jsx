import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { urlApi, useApi } from "../api.js";
import {
  Ayuda, Descarga, EncabezadoPresa, ErrorCarga, EsqueletoGrafica, EsqueletoMetricas, EsqueletoTabla, Intro, Metrica,
  Termino,
} from "../componentes.jsx";
import { fecha, fechaCorta, num, pct, pp } from "../formato.js";

const PERIODOS = [["1", "1 año"], ["3", "3 años"], ["10", "10 años"], ["todo", "Todo"]];

// Banderas de calidad: término del glosario y color de la barra
const BANDERAS = {
  observado: ["observado", "var(--normal)"],
  reconstruido_nivel: ["reconstruido_nivel", "var(--serie-3)"],
  interpolado: ["interpolado", "var(--serie-2)"],
  atipico_eliminado: ["atipico_eliminado", "var(--atencion)"],
  faltante: ["faltante", "var(--critico)"],
};

// Campos de la ficha que tienen explicación en el glosario
const TERMINOS_FICHA = {
  "Clave SIH": "clave_sih", Sistema: "sistema", "Capacidad NAMO (hm³)": "namo", Cuenca: "cuenca",
  "Región hidrológica": "region_hidrologica",
};

function TooltipSerie({ active, payload, label, enPct, cap }) {
  if (!active || !payload?.length) return null;
  const f = payload[0].payload;
  return (
    <div className="tooltip-grafica">
      <b>{fecha(label)}</b>
      <div className="tooltip-fila">Llenado <span>{pct(f.llenado_pct)}</span></div>
      <div className="tooltip-fila">Volumen <span>{num(f.volumen_hm3)} hm³</span></div>
      {!enPct && cap && <div className="tooltip-fila tenue">de {num(cap)} hm³ de capacidad</div>}
    </div>
  );
}

export default function Consulta() {
  const { clave } = useParams();
  const [enPct, setEnPct] = useState(true);
  const [periodo, setPeriodo] = useState("10");
  const { datos: c, error, cargando, recargar } = useApi(`presas/${clave}`);
  const { datos: s, cargando: cargandoSerie } = useApi(`presas/${clave}/serie`, { periodo });

  if (error) return <ErrorCarga mensaje={error} reintentar={recargar} />;
  const campo = enPct ? "llenado_pct" : "volumen_hm3";
  const cap = c?.presa.capacidad_namo_hm3;
  const totalDias = c ? Object.values(c.banderas).reduce((a, b) => a + b, 0) : 0;
  const comparacion = c && c.promedio_mes_pct != null ? c.llenado_pct - c.promedio_mes_pct : null;

  return (
    <>
      <EncabezadoPresa clave={clave} />
      <Intro>
        Situación actual de la presa, su evolución histórica y qué tan completos son sus datos.
      </Intro>

      {cargando ? <EsqueletoMetricas /> : (
        <div className="metricas">
          <Metrica titulo="Llenado actual" valor={pct(c.llenado_pct)} termino="llenado"
            delta={c.cambio_30d_pp != null ? `${pp(c.cambio_30d_pp)} en 30 días` : null} />
          <Metrica titulo="Volumen almacenado" valor={`${num(c.volumen_hm3)} hm³`} termino="hm3"
            nota={`de ${num(cap)} hm³ de capacidad`} />
          <Metrica titulo="Hace un año" valor={pct(c.llenado_hace_1a_pct)} termino="hace_un_anio"
            delta={c.llenado_hace_1a_pct != null ? `${pp(c.llenado_pct - c.llenado_hace_1a_pct)} vs. hoy` : null} />
          <Metrica titulo="Promedio histórico del mes" valor={pct(c.promedio_mes_pct)} termino="promedio_mes"
            nota={comparacion == null ? null : comparacion >= 0
              ? `Hoy está ${num(comparacion)} pp por encima de lo normal`
              : `Hoy está ${num(-comparacion)} pp por debajo de lo normal`} />
        </div>
      )}

      <div className="fila-titulo">
        <h2>Evolución histórica <Ayuda texto="Llenado o volumen diario registrado. Las líneas punteadas marcan los umbrales de atención (naranja) y crítico (rojo). Pasa el cursor sobre la gráfica para ver el valor de cada fecha." /></h2>
        <div className="controles">
          <div className="segmentado" role="group" aria-label="Unidad">
            <button className={enPct ? "activo" : ""} onClick={() => setEnPct(true)} title="Porcentaje de la capacidad NAMO">% de llenado</button>
            <button className={!enPct ? "activo" : ""} onClick={() => setEnPct(false)} title="Millones de metros cúbicos">hm³</button>
          </div>
          <div className="segmentado" role="group" aria-label="Periodo">
            {PERIODOS.map(([v, t]) => (
              <button key={v} className={periodo === v ? "activo" : ""} onClick={() => setPeriodo(v)}>{t}</button>
            ))}
          </div>
        </div>
      </div>
      <div className={`grafica${cargandoSerie && s ? " actualizando" : ""}`}>
        {!s || !c ? <EsqueletoGrafica alto={320} texto="Cargando la serie histórica…" /> : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={s.puntos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--rejilla)" vertical={false} />
              <XAxis dataKey="fecha" tickFormatter={fechaCorta} minTickGap={50} stroke="var(--tenue)" />
              <YAxis domain={enPct ? [0, 100] : [0, "auto"]} stroke="var(--tenue)" width={60}
                tickFormatter={(v) => num(v, 0)} />
              <Tooltip content={<TooltipSerie enPct={enPct} cap={cap} />} />
              {[["llenado_atencion_pct", "var(--atencion)"], ["llenado_critico_pct", "var(--critico)"]].map(([k, col]) => (
                <ReferenceLine key={k} y={enPct ? s.umbrales[k] : (s.umbrales[k] * cap) / 100}
                  stroke={col} strokeDasharray="4 4" />
              ))}
              <Area dataKey={campo} name={enPct ? "Llenado" : "Volumen"} stroke="var(--serie-1)"
                fill="var(--serie-1)" fillOpacity={0.15} strokeWidth={1.5} connectNulls={false}
                isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
        <div className="leyenda-umbrales">
          <span><i className="linea-atencion" /> Umbral de atención</span>
          <span><i className="linea-critico" /> Umbral crítico</span>
          {s?.resumida_semanal && <Termino t="resumida_semanal">Serie resumida por promedio semanal</Termino>}
        </div>
      </div>

      <div className="columnas">
        <section>
          <h2>Calidad de los datos <Ayuda termino="bandera" /></h2>
          {cargando ? <EsqueletoTabla filas={4} columnas={3} /> : (
            <div className="tabla-scroll">
              <table className="tabla">
                <thead><tr><th>Origen del dato</th><th className="num">Días</th><th>Proporción</th></tr></thead>
                <tbody>
                  {Object.entries(c.banderas).map(([b, n]) => {
                    const [termino, color] = BANDERAS[b] || [null, "var(--tenue)"];
                    const fraccion = totalDias ? (100 * n) / totalDias : 0;
                    return (
                      <tr key={b}>
                        <td>{termino ? <Termino t={termino}>{b.replaceAll("_", " ")}</Termino> : b}</td>
                        <td className="num">{num(n, 0)}</td>
                        <td>
                          <div className="barra-mini" title={pct(fraccion)}>
                            <div style={{ width: `${fraccion}%`, background: color }} />
                          </div>
                          <span className="tenue-chico">{pct(fraccion)}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <p className="tenue">Pasa el cursor sobre cada origen para ver qué significa.</p>
        </section>
        <section>
          <h2>Características</h2>
          {cargando ? <EsqueletoTabla filas={6} columnas={2} /> : (
            <div className="tabla-scroll">
              <table className="tabla">
                <tbody>
                  {Object.entries(c.ficha).map(([k, v]) => (
                    <tr key={k}>
                      <th>{TERMINOS_FICHA[k] ? <Termino t={TERMINOS_FICHA[k]}>{k}</Termino> : k}</th>
                      <td>{v ?? "s/d"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
      <div className="acciones">
        <Descarga href={urlApi(`presas/${clave}/serie.csv`)} ayuda="Serie diaria limpia con banderas de calidad">
          Descargar serie procesada (CSV)
        </Descarga>
      </div>
    </>
  );
}
