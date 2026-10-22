import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useApi } from "../api.js";
import {
  Aviso, Ayuda, EncabezadoPresa, ErrorCarga, EsqueletoGrafica, EsqueletoMetricas, EsqueletoTabla, Intro, Metrica,
  Termino,
} from "../componentes.jsx";
import { fecha, fechaCorta, num, pct } from "../formato.js";
import { TERMINO_MODELO } from "../glosario.js";

const ms = (iso) => new Date(iso + "T00:00:00").getTime();
const isoDe = (t) => new Date(t).toISOString().slice(0, 10);

/** Une historia, pronóstico (con intervalo) y lo ocurrido en una sola tabla por fecha. */
function datosGrafica(p) {
  const filas = new Map();
  const fila = (iso) => {
    const t = ms(iso);
    if (!filas.has(t)) filas.set(t, { t });
    return filas.get(t);
  };
  p.historia.forEach((h) => (fila(h.fecha).historia = h.llenado_pct));
  p.ocurrido.forEach((h) => (fila(h.fecha).ocurrido = h.llenado_pct));
  const v0 = p.historia.at(-1)?.llenado_pct;
  if (v0 != null && p.pronosticos.length) Object.assign(fila(p.fecha_emision), { pron: v0, rango: [v0, v0] });
  p.pronosticos.forEach((x) => Object.assign(fila(x.fecha_objetivo), { pron: x.llenado_pct, rango: [x.inf_pct, x.sup_pct] }));
  return [...filas.values()].sort((a, b) => a.t - b.t);
}

const NOMBRES_SERIE = { historia: "Observado", pron: "Pronóstico", rango: "Intervalo", ocurrido: "Lo que ocurrió",
  real: "Real", pred: "Modelo", persistencia: "Persistencia" };

/** Tooltip común a las dos gráficas: nombre de la serie y valor (o rango) formateados. */
function TooltipPronostico({ active, payload, label, aFecha }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip-grafica">
      <b>{fecha(aFecha(label))}</b>
      {payload.filter((x) => x.value != null).map((x) => (
        <div key={x.dataKey} className="tooltip-fila">
          <i style={{ background: x.color === "none" ? x.fill : x.color }} /> {NOMBRES_SERIE[x.dataKey] || x.name}
          <span>{Array.isArray(x.value) ? `${pct(x.value[0])} – ${pct(x.value[1])}` : pct(x.value)}</span>
        </div>
      ))}
    </div>
  );
}

function GraficaPronostico({ p }) {
  const datos = datosGrafica(p);
  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--rejilla)" vertical={false} />
        <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]}
          tickFormatter={(t) => fechaCorta(isoDe(t))} stroke="var(--tenue)" minTickGap={50} />
        <YAxis domain={["auto", "auto"]} unit=" %" stroke="var(--tenue)" width={56} tickFormatter={(v) => num(v, 0)} />
        <Tooltip content={<TooltipPronostico aFecha={isoDe} />} />
        <Legend />
        <ReferenceLine x={ms(p.fecha_emision)} stroke="var(--tenue)" strokeDasharray="2 4"
          label={{ value: "Emisión", position: "insideTopLeft", fill: "var(--tenue)", fontSize: 12 }} />
        <Area dataKey="rango" name="Intervalo" stroke="none" fill="var(--serie-2)" fillOpacity={0.2}
          connectNulls isAnimationActive={false} />
        <Line dataKey="historia" name="Observado" dot={false} stroke="var(--serie-1)" strokeWidth={1.8}
          isAnimationActive={false} />
        <Line dataKey="pron" name="Pronóstico" stroke="var(--serie-2)" strokeWidth={2} strokeDasharray="5 4"
          dot={{ r: 4 }} connectNulls isAnimationActive={false} />
        {p.simulado && (
          <Line dataKey="ocurrido" name="Lo que ocurrió" dot={false} stroke="var(--serie-3)" strokeWidth={2}
            isAnimationActive={false} />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function GraficaBacktest({ datos }) {
  const filas = datos.map((d) => ({ ...d, rango: [d.inf, d.sup] }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={filas} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--rejilla)" vertical={false} />
        <XAxis dataKey="fecha" tickFormatter={fechaCorta} minTickGap={50} stroke="var(--tenue)" />
        <YAxis domain={["auto", "auto"]} unit=" %" stroke="var(--tenue)" width={56} tickFormatter={(v) => num(v, 0)} />
        <Tooltip content={<TooltipPronostico aFecha={(x) => x} />} />
        <Legend />
        <Area dataKey="rango" name="Intervalo" stroke="none" fill="var(--serie-2)" fillOpacity={0.18}
          isAnimationActive={false} />
        <Line dataKey="real" name="Real" dot={false} stroke="var(--serie-1)" strokeWidth={1.8} isAnimationActive={false} />
        <Line dataKey="pred" name="Modelo" dot={false} stroke="var(--serie-2)" strokeWidth={1.5} isAnimationActive={false} />
        <Line dataKey="persistencia" name="Persistencia" dot={false} stroke="var(--tenue)" strokeWidth={1}
          strokeDasharray="3 3" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const NombreModelo = ({ nombre }) =>
  TERMINO_MODELO[nombre] ? <Termino t={TERMINO_MODELO[nombre]}>{nombre}</Termino> : nombre;

/** Título de columna con explicación del glosario. */
const Th = ({ t, num: numerica, children }) => (
  <th className={numerica ? "num" : ""}><span className="th-contenido">{children}<Ayuda termino={t} /></span></th>
);

function Precision({ clave }) {
  const { datos: m, error } = useApi(`presas/${clave}/metricas`);
  const hs = m ? Object.keys(m.horizontes) : [];
  const [hEval, setHEval] = useState(null);
  const h = hEval && hs.includes(hEval) ? hEval : hs[0];
  const { datos: bt, cargando: cargandoBt } = useApi(h ? `presas/${clave}/backtest/${h}` : null);
  if (error) return <ErrorCarga mensaje={error} />;
  if (!m) return <><EsqueletoMetricas /><EsqueletoGrafica alto={300} texto="Cargando la evaluación del modelo…" /></>;
  if (!hs.length) return <p className="vacio">Sin métricas de prueba para esta presa.</p>;
  const r = m.horizontes[h];
  const b = r.mejor;
  const cobertura = 100 * r.intervalo.cobertura_real_prueba;
  const nominal = Math.round(100 * r.intervalo.nivel);
  const mejora = b.mejora_vs_persistencia_pct ?? 0;

  return (
    <>
      <Intro>
        Para saber si el modelo es confiable, se le pidió pronosticar un <Termino t="periodo_prueba">periodo de prueba</Termino>{" "}
        que nunca vio al entrenar y se comparó con lo que realmente ocurrió.
      </Intro>
      <div className="segmentado" role="group" aria-label="Horizonte a evaluar">
        {hs.map((x) => (
          <button key={x} className={x === h ? "activo" : ""} onClick={() => setHEval(x)}>Pronóstico a {x} días</button>
        ))}
      </div>
      <div className="metricas">
        <Metrica titulo="Error absoluto medio (MAE)" valor={`${num(b.MAE_hm3, 2)} hm³`} termino="mae"
          delta={`${num(b.MAE_pp_llenado, 2)} pp de llenado`} neutro
          nota="Cuánto se equivoca en promedio" />
        <Metrica titulo="RMSE" valor={`${num(b.RMSE_hm3, 2)} hm³`} termino="rmse"
          nota={b.RMSE_hm3 > 1.5 * b.MAE_hm3 ? "Hay errores grandes ocasionales" : "Errores parejos, sin fallos extremos"} />
        <Metrica titulo="Mejora vs. persistencia" valor={pct(mejora)} termino="mejora_persistencia"
          nota={mejora > 0 ? "Mejor que suponer que nada cambia" : "No supera a la referencia simple"} />
        <Metrica titulo={`Cobertura del intervalo ${nominal} %`} valor={pct(cobertura, 0)} termino="cobertura_intervalo"
          nota={cobertura >= nominal - 3 ? "Intervalo bien calibrado" : "Intervalo algo optimista"} />
      </div>
      <p className="tenue">
        Periodo de prueba: {fecha(r.particion_prueba.inicio)} a {fecha(r.particion_prueba.fin)} (
        {num(r.particion_prueba.filas, 0)} pronósticos). Modelo seleccionado: <b><NombreModelo nombre={r.mejor_modelo_nombre} /></b>.
      </p>

      <h3>
        Pronóstico vs. realidad en el periodo de prueba <Ayuda termino="backtest" />
      </h3>
      <div className={`grafica${cargandoBt && bt ? " actualizando" : ""}`}>
        {bt ? <GraficaBacktest datos={bt} /> : <EsqueletoGrafica alto={300} texto="Cargando predicciones de prueba…" />}
      </div>

      <h3>Comparación de modelos</h3>
      <p className="tenue">La fila resaltada es el modelo elegido (el de menor error). Pasa el cursor sobre cada nombre para saber cómo funciona.</p>
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr>
              <th>Modelo</th>
              <Th t="mae" num>MAE (hm³)</Th>
              <Th t="rmse" num>RMSE (hm³)</Th>
              <Th t="mae_pp" num>MAE (pp)</Th>
              <Th t="mape" num>MAPE (%)</Th>
              <Th t="acierto_direccion" num>Acierto de dirección</Th>
              <Th t="mejora_persistencia" num>Mejora vs. persistencia (%)</Th>
            </tr>
          </thead>
          <tbody>
            {r.tabla.map((f) => (
              <tr key={f.modelo} className={f.modelo === r.mejor_modelo ? "resaltada" : ""}>
                <td>
                  <NombreModelo nombre={f.nombre} />
                  {f.modelo === r.mejor_modelo && <span className="insignia">elegido</span>}
                </td>
                <td className="num">{num(f.MAE_hm3, 2)}</td>
                <td className="num">{num(f.RMSE_hm3, 2)}</td>
                <td className="num">{num(f.MAE_pp_llenado, 2)}</td>
                <td className="num">{num(f.MAPE_pct, 2)}</td>
                <td className="num">{f.acierto_direccion == null ? "s/d" : pct(100 * f.acierto_direccion, 0)}</td>
                <td className="num">{num(f.mejora_vs_persistencia_pct, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details className="detalle">
        <summary>¿Qué tan confiable es la estimación con los datos disponibles?</summary>
        <ul>
          <li>
            Calidad de datos de esta presa: <b>{pct(100 * (m.calidad.cobertura_volumen || 0))}</b> de días con
            volumen; {m.calidad.reconstruidos} días reconstruidos desde nivel.
          </li>
          <li>El intervalo se calibra con los errores del periodo de validación (<Termino t="conformal">método
            conformal</Termino>); si la cobertura real en prueba queda por debajo del nivel nominal, el intervalo es
            optimista.</li>
          <li>El modelo aprende de lo ocurrido en el pasado; no anticipa lluvias extraordinarias que todavía no se
            observan, ni cambios de operación decididos por el organismo operador.</li>
          {Object.entries(r.por_temporada).map(([k, v]) => (
            <li key={k}>Error en {k.replaceAll("_", " ")}: {num(v.MAE_pp_llenado, 2)} pp</li>
          ))}
        </ul>
      </details>
    </>
  );
}

export default function Prediccion() {
  const { clave } = useParams();
  const { datos: base, error: errorBase } = useApi(`presas/${clave}/pronostico`);
  const [sel, setSel] = useState(null);
  const [simular, setSimular] = useState(false);
  const [fechaSim, setFechaSim] = useState("");

  useEffect(() => {
    setSel(null);
    setSimular(false);
    setFechaSim("");
  }, [clave]);

  const disponibles = base?.horizontes_disponibles || [];
  const horizontes = sel ?? disponibles;
  const params = { horizontes: horizontes.join(",") };
  if (simular && fechaSim) params.fecha = fechaSim;
  const { datos: p, error, cargando } = useApi(base ? `presas/${clave}/pronostico` : null, params);

  useEffect(() => {
    if (simular && !fechaSim && base) {
      const t = new Date(base.fecha_maxima + "T00:00:00");
      t.setDate(t.getDate() - 60);
      setFechaSim(t.toISOString().slice(0, 10));
    }
  }, [simular, fechaSim, base]);

  const alternar = (h) =>
    setSel(horizontes.includes(h) ? horizontes.filter((x) => x !== h) : [...horizontes, h].sort((a, b) => a - b));

  return (
    <>
      <EncabezadoPresa clave={clave} />
      <Intro>
        Estimación de cómo estará la presa en los próximos días. La línea punteada es el{" "}
        <Termino t="pronostico">pronóstico</Termino> y la franja sombreada el{" "}
        <Termino t="intervalo">intervalo</Termino> donde probablemente caerá el valor real.
      </Intro>
      {!base && !errorBase && <EsqueletoGrafica alto={340} texto="Calculando el pronóstico…" />}
      {(errorBase || error) && <Aviso nivel="informativo">{errorBase || error}</Aviso>}
      {base && (
        <>
          <div className="controles barra-controles">
            <fieldset>
              <legend>Horizontes <Ayuda termino="horizonte" /></legend>
              {disponibles.map((h) => (
                <label key={h} className="casilla">
                  <input type="checkbox" checked={horizontes.includes(h)} onChange={() => alternar(h)} /> {h} días
                </label>
              ))}
            </fieldset>
            <label className="casilla">
              <input type="checkbox" checked={simular} onChange={(e) => setSimular(e.target.checked)} />
              Simular un pronóstico en una fecha pasada <Ayuda termino="simulacion" />
            </label>
            {simular && (
              <label>
                Fecha de emisión{" "}
                <input type="date" value={fechaSim} min={base.fecha_minima} max={base.fecha_maxima}
                  onChange={(e) => setFechaSim(e.target.value)} />
              </label>
            )}
          </div>
          {horizontes.length === 0 && <Aviso nivel="atencion">Elige al menos un horizonte para ver el pronóstico.</Aviso>}

          <div className={`grafica${cargando && p ? " actualizando" : ""}`}>
            {p ? <GraficaPronostico p={p} /> : <EsqueletoGrafica alto={340} texto="Calculando el pronóstico…" />}
            {cargando && p && <div className="velo"><span className="spinner" /> Recalculando…</div>}
          </div>

          {!p && <EsqueletoTabla filas={3} columnas={6} />}
          {p?.pronosticos.length > 0 && (
            <>
              <h2>
                Valores estimados <span className="tenue">(emitidos el {fecha(p.fecha_emision)})</span>
              </h2>
              <div className="tarjetas-pronostico">
                {p.pronosticos.map((x) => (
                  <div key={x.horizonte} className="metrica">
                    <div className="metrica-titulo"><span>En {x.horizonte} días · {fecha(x.fecha_objetivo)}</span></div>
                    <div className="metrica-valor">{pct(x.llenado_pct)}</div>
                    <div className="metrica-nota">
                      {num(x.volumen_hm3, 1)} hm³ · <Termino t="intervalo">entre {pct(x.inf_pct)} y {pct(x.sup_pct)}</Termino>
                    </div>
                  </div>
                ))}
              </div>
              <div className="tabla-scroll">
                <table className="tabla">
                  <thead>
                    <tr>
                      <Th t="horizonte" num>Horizonte</Th><th>Fecha objetivo</th>
                      <Th t="volumen" num>Volumen (hm³)</Th>
                      <Th t="llenado" num>Llenado</Th><Th t="intervalo">Intervalo (hm³)</Th>
                      <Th t="mae" num>Error medio histórico (hm³)</Th><th>Modelo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.pronosticos.map((x) => (
                      <tr key={x.horizonte}>
                        <td className="num">{x.horizonte} días</td>
                        <td>{fecha(x.fecha_objetivo)}</td>
                        <td className="num">{num(x.volumen_hm3, 2)}</td>
                        <td className="num">{pct(x.llenado_pct)}</td>
                        <td>{num(x.inf_hm3)} – {num(x.sup_hm3)}</td>
                        <td className="num">{num(x.mae_prueba_hm3, 2)}</td>
                        <td><NombreModelo nombre={x.modelo_nombre} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          <h2>¿Qué tan precisa es la predicción?</h2>
          <Precision clave={clave} />
        </>
      )}
    </>
  );
}
