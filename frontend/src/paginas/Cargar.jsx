import { useEffect, useState } from "react";
import { Aviso, Icono, Intro, Termino } from "../componentes.jsx";

const URL_SIH = "https://sih.conagua.gob.mx/basedatos/Presas/";

// Etapas que se muestran mientras el servidor procesa (orientativas: el servidor no informa avance)
const ETAPAS = ["Subiendo archivos…", "Validando columnas y fechas…", "Limpiando la serie…", "Emitiendo el pronóstico…"];

export default function Cargar({ presas, alTerminar }) {
  const [archivos, setArchivos] = useState([]);
  const [arrastrando, setArrastrando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [etapa, setEtapa] = useState(0);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const claves = new Set(presas.map((p) => p.clave.toUpperCase()));
  const conocido = (f) => claves.has(f.name.replace(/\.csv$/i, "").toUpperCase());

  useEffect(() => {
    if (!enviando) return;
    setEtapa(0);
    const t = setInterval(() => setEtapa((e) => Math.min(e + 1, ETAPAS.length - 1)), 4000);
    return () => clearInterval(t);
  }, [enviando]);

  const elegir = (lista) => {
    const csv = [...lista].filter((f) => f.name.toLowerCase().endsWith(".csv"));
    const ignorados = lista.length - csv.length;
    setArchivos((previos) => [...previos.filter((p) => !csv.some((f) => f.name === p.name)), ...csv]);
    setResultado(null);
    setError(ignorados ? `Se ignoraron ${ignorados} archivo(s) que no son CSV.` : null);
  };
  const quitar = (nombre) => setArchivos((a) => a.filter((f) => f.name !== nombre));

  async function enviar() {
    const datos = new FormData();
    archivos.forEach((f) => datos.append("archivos", f));
    setEnviando(true);
    setError(null);
    try {
      const r = await fetch("/api/cargar", { method: "POST", body: datos });
      const json = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(json.error || `Error ${r.status}`);
      setResultado(json);
      setArchivos([]);
      if (json.actualizado) alTerminar?.();
    } catch (e) {
      setError(e instanceof TypeError ? "No hay conexión con el servidor." : e.message);
    } finally {
      setEnviando(false);
    }
  }

  const desconocidos = archivos.filter((f) => !conocido(f));

  return (
    <article className="prosa">
      <h1>Cargar datos del SIH</h1>
      <Intro>
        Actualiza el tablero con datos nuevos sin usar la terminal. El sistema valida los archivos, limpia la serie y
        emite un pronóstico nuevo con los modelos ya entrenados.
      </Intro>

      <ol className="pasos">
        <li>
          Abre el <Termino t="sih">SIH de CONAGUA</Termino>:{" "}
          <a href={URL_SIH} target="_blank" rel="noreferrer">{URL_SIH}</a>
        </li>
        <li>Descarga el CSV de cada presa. El nombre del archivo debe ser su <Termino t="clave_sih">clave</Termino>:
          <div className="chips">
            {presas.map((p) => <span key={p.clave} className="chip"><b>{p.clave}.csv</b> {p.nombre}</span>)}
          </div>
        </li>
        <li>Arrástralos al recuadro de abajo y pulsa <b>Cargar y actualizar</b>.</li>
      </ol>

      <label
        className={`zona-carga${arrastrando ? " activa" : ""}${enviando ? " deshabilitada" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); if (!enviando) elegir(e.dataTransfer.files); }}
      >
        <input type="file" accept=".csv" multiple hidden disabled={enviando}
          onChange={(e) => { elegir(e.target.files); e.target.value = ""; }} />
        <Icono nombre="cargar" tam={32} />
        <b>{arrastrando ? "Suelta los archivos aquí" : "Arrastra aquí los CSV o haz clic para elegirlos"}</b>
        <span className="tenue">Solo archivos .csv, hasta 50 MB cada uno</span>
      </label>

      {archivos.length > 0 && (
        <ul className="lista-archivos">
          {archivos.map((f) => (
            <li key={f.name} className={conocido(f) ? "" : "desconocido"}>
              <span>{conocido(f) ? "📄" : "⚠️"} <b>{f.name}</b> · {(f.size / 1024).toFixed(0)} KB
                {!conocido(f) && <span className="tenue-chico"> — no coincide con ninguna presa configurada</span>}
              </span>
              <button className="buscador-limpiar" onClick={() => quitar(f.name)} disabled={enviando}
                aria-label={`Quitar ${f.name}`} title="Quitar">
                <Icono nombre="cerrar" tam={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {desconocidos.length > 0 && (
        <Aviso nivel="atencion">
          {desconocidos.length === 1 ? "Un archivo tiene" : `${desconocidos.length} archivos tienen`} un nombre que no
          corresponde a ninguna clave. Renómbralo(s) con la clave de la presa o el servidor los rechazará.
        </Aviso>
      )}

      <button className="boton primario" disabled={!archivos.length || enviando} onClick={enviar}>
        {enviando ? <><span className="spinner claro" /> {ETAPAS[etapa]}</> : <><Icono nombre="cargar" tam={16} /> Cargar y actualizar</>}
      </button>
      {enviando && <p className="tenue">Esto puede tardar hasta un minuto. No cierres la página.</p>}

      {error && <Aviso nivel="critico">{error}</Aviso>}
      {resultado && (
        <>
          {resultado.actualizado && <Aviso nivel="normal">✅ Datos cargados y pronóstico actualizado.</Aviso>}
          <div className="tabla-scroll">
            <table className="tabla">
              <thead>
                <tr><th>Archivo</th><th>Resultado</th><th>Periodo</th><th>Calidad</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {resultado.archivos.map((a) => (
                  <tr key={a.archivo}>
                    <td>{a.archivo}</td>
                    <td className={a.ok ? "sube" : "baja"}>{a.ok ? "✔ cargado" : `✘ ${a.detalle}`}</td>
                    <td>{a.ok ? `${a.desde} → ${a.hasta}` : "—"}</td>
                    <td>{a.ok ? (a.apta ? "apta" : `no apta: ${a.motivo}`) : "—"}</td>
                    <td>{a.estado ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </article>
  );
}
