import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { urlApi, useApi } from "../api.js";
import {
  Aviso, Ayuda, Cargando, Descarga, EncabezadoPresa, ErrorCarga, EsqueletoMetricas, Estado, Intro, Metrica, Termino,
} from "../componentes.jsx";
import { ETIQUETA, ICONO, pct, pp } from "../formato.js";

// [clave, título, máximo, paso, término del glosario, unidad]
const CAMPOS = [
  ["llenado_atencion_pct", "Llenado de atención", 100, 1, "umbral_llenado_atencion", "%"],
  ["llenado_critico_pct", "Llenado crítico", 100, 1, "umbral_llenado_critico", "%"],
  ["descenso_atencion_pp", "Descenso de atención", 50, 0.5, "umbral_descenso_atencion", "pp"],
  ["descenso_critico_pp", "Descenso crítico", 50, 0.5, "umbral_descenso_critico", "pp"],
];

const ESPERA_MS = 400; // se recalcula cuando el usuario deja de teclear

export default function Avisos({ umbralesBase }) {
  const { clave } = useParams();
  const inicial = () => Object.fromEntries(CAMPOS.map(([k]) => [k, umbralesBase[k]]));
  // Los umbrales viven en el estado de la página: se pueden ajustar sin tocar config.toml
  const [u, setU] = useState(inicial);
  const [uAplicados, setUAplicados] = useState(u);
  useEffect(() => {
    const t = setTimeout(() => setUAplicados(u), ESPERA_MS);
    return () => clearTimeout(t);
  }, [u]);

  const incoherente = u.llenado_critico_pct > u.llenado_atencion_pct || u.descenso_critico_pp < u.descenso_atencion_pp;
  const { datos, error, cargando, recargar } = useApi(incoherente ? null : `presas/${clave}/avisos`, uAplicados);
  const pendiente = cargando || JSON.stringify(u) !== JSON.stringify(uAplicados);
  const modificados = CAMPOS.some(([k]) => u[k] !== umbralesBase[k]);

  return (
    <>
      <EncabezadoPresa clave={clave} />
      <Intro>
        Reglas de alerta sobre el llenado actual y el proyectado. Ajusta los umbrales para ver cómo cambian los avisos;
        los cambios solo afectan a esta pantalla y a los archivos que exportes.
      </Intro>

      <div className="fila-titulo">
        <h2>Umbrales</h2>
        {modificados && (
          <button className="boton" onClick={() => setU(inicial())}>Restablecer valores de config.toml</button>
        )}
      </div>
      <div className="umbrales">
        {CAMPOS.map(([k, t, max, paso, termino, unidad]) => (
          <label key={k} className={u[k] !== umbralesBase[k] ? "modificado" : ""}>
            <span className="th-contenido">{t} ({unidad}) <Ayuda termino={termino} /></span>
            <div className="entrada-unidad">
              <input type="number" min={0} max={max} step={paso} value={u[k]}
                onChange={(e) => setU({ ...u, [k]: e.target.value === "" ? 0 : Number(e.target.value) })} />
              <span>{unidad}</span>
            </div>
          </label>
        ))}
      </div>

      {incoherente ? (
        <Aviso nivel="critico">
          El umbral crítico debe ser más severo que el de atención: el llenado crítico debe ser <b>menor</b> que el de
          atención y el descenso crítico <b>mayor</b> que el de atención.
        </Aviso>
      ) : error ? (
        <ErrorCarga mensaje={error} reintentar={recargar} />
      ) : !datos ? (
        <>
          <EsqueletoMetricas n={3} />
          <Cargando texto="Evaluando avisos…" />
        </>
      ) : (
        <div className={pendiente ? "actualizando" : ""}>
          {pendiente && <Cargando texto="Recalculando con los nuevos umbrales…" />}
          <div className="metricas">
            <Metrica titulo="Estado general" valor={<Estado nivel={datos.estado} />} termino="estado_presa" />
            <Metrica titulo={`Tendencia observada (${datos.ventana_tendencia_dias} días)`} termino="tendencia"
              valor={datos.tendencia_pp_mes == null ? "s/d" : `${pp(datos.tendencia_pp_mes, 2)}/mes`} />
            {datos.proyeccion && (
              <Metrica titulo={`Llenado proyectado a ${datos.proyeccion.horizonte} días`} termino="proyectado"
                valor={pct(datos.proyeccion.llenado_pct)} delta={pp(datos.proyeccion.cambio_pp)} />
            )}
          </div>

          <h2>Avisos {datos.avisos.length > 0 && <span className="contador">{datos.avisos.length}</span>}</h2>
          {datos.avisos.length === 0 && <Aviso nivel="normal">🟢 Sin avisos con los umbrales actuales.</Aviso>}
          {datos.avisos.map((a, i) => (
            <Aviso key={i} nivel={a.nivel}>
              <b>{ICONO[a.nivel]} <Termino t={a.nivel}>{ETIQUETA[a.nivel]}</Termino> — {a.titulo}</b>
              <p>{a.motivo}</p>
              <details className="detalle">
                <summary>Ver los datos con que se calculó</summary>
                <dl className="datos-aviso">
                  {Object.entries(a.datos || {}).map(([k, v]) => (
                    <div key={k}>
                      <dt>{k.replaceAll("_", " ")}</dt>
                      <dd>{typeof v === "number" ? v.toLocaleString("es-MX", { maximumFractionDigits: 2 }) : String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </details>
            </Aviso>
          ))}

          <h2>Exportar</h2>
          <div className="acciones">
            <Descarga href={urlApi(`presas/${clave}/reporte.html`, uAplicados)} ayuda="Reporte listo para imprimir o compartir">
              Reporte (HTML)
            </Descarga>
            <Descarga href={urlApi(`presas/${clave}/pronostico.csv`, uAplicados)} ayuda="Tabla de pronósticos para Excel">
              Pronóstico (CSV)
            </Descarga>
            <Descarga href={urlApi(`presas/${clave}/avisos.json`, uAplicados)} ayuda="Avisos en formato para otros sistemas">
              Avisos (JSON)
            </Descarga>
          </div>
          <p className="tenue">
            Los umbrales son configurables y deben definirse con criterios documentados, de preferencia revisados por
            un especialista en gestión del agua. Un descenso no implica por sí mismo una emergencia.
          </p>
        </div>
      )}
    </>
  );
}
