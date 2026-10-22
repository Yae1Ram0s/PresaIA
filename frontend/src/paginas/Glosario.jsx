import { useState } from "react";
import { Icono, Intro, Resaltar } from "../componentes.jsx";
import { CATEGORIAS, GLOSARIO, normalizar } from "../glosario.js";

export default function Glosario() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("todas");
  const n = normalizar(q.trim());

  const entradas = Object.entries(GLOSARIO).filter(
    ([, g]) => (cat === "todas" || g.categoria === cat) && normalizar(`${g.titulo} ${g.definicion}`).includes(n),
  );
  const grupos = Object.keys(CATEGORIAS)
    .map((c) => [c, entradas.filter(([, g]) => g.categoria === c)])
    .filter(([, lista]) => lista.length);

  return (
    <>
      <h1>Glosario</h1>
      <Intro>
        Significado de los términos técnicos que aparecen en el tablero. En cualquier pantalla también puedes pasar el
        cursor sobre el icono <Icono nombre="info" tam={14} /> o sobre las palabras <span className="termino">subrayadas
        con puntos</span> para ver su explicación.
      </Intro>

      <div className="filtros">
        <div className="buscador-caja grande">
          <Icono nombre="buscar" tam={18} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar un término (p. ej. MAE, NAMO, intervalo)…"
            aria-label="Buscar en el glosario" autoFocus />
          {q && (
            <button className="buscador-limpiar" onClick={() => setQ("")} aria-label="Borrar búsqueda">
              <Icono nombre="cerrar" tam={14} />
            </button>
          )}
        </div>
        <div className="segmentado envolver" role="group" aria-label="Categoría">
          {[["todas", "Todas"], ...Object.entries(CATEGORIAS)].map(([k, t]) => (
            <button key={k} className={cat === k ? "activo" : ""} onClick={() => setCat(k)}>{t}</button>
          ))}
        </div>
      </div>

      {grupos.length === 0 && <p className="vacio">No hay términos que coincidan con «{q}».</p>}
      {grupos.map(([c, lista]) => (
        <section key={c}>
          <h2>{CATEGORIAS[c]}</h2>
          <dl className="glosario">
            {lista.map(([k, g]) => (
              <div key={k} className="glosario-entrada" id={k}>
                <dt><Resaltar texto={g.titulo} q={q.trim()} /></dt>
                <dd>
                  <Resaltar texto={g.definicion} q={q.trim()} />
                  {g.ejemplo && <span className="glosario-ejemplo">Ejemplo: {g.ejemplo}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </>
  );
}
