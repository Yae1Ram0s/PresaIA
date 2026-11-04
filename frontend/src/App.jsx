import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { limpiarCache, useApi } from "./api.js";
import { Aviso, BarraCarga, Cargando, ErrorCarga, Icono, Tip } from "./componentes.jsx";
import Panorama from "./paginas/Panorama.jsx";
import Consulta from "./paginas/Consulta.jsx";
import Prediccion from "./paginas/Prediccion.jsx";
import Avisos from "./paginas/Avisos.jsx";
import Acerca from "./paginas/Acerca.jsx";
import Cargar from "./paginas/Cargar.jsx";
import Glosario from "./paginas/Glosario.jsx";
import BotonActualizar from "./BotonActualizar.jsx";

const fechaLarga = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });

const MODULOS = [
  { ruta: "consulta", nombre: "Consulta", icono: "consulta", ayuda: "Situación actual, historia y calidad de datos" },
  { ruta: "prediccion", nombre: "Predicción", icono: "prediccion", ayuda: "Llenado estimado a 7, 15 y 30 días" },
  { ruta: "avisos", nombre: "Indicadores y avisos", icono: "avisos", ayuda: "Alertas con umbrales ajustables y exportación" },
];

const TITULOS = { consulta: "Consulta", prediccion: "Predicción", avisos: "Avisos", cargar: "Cargar datos",
  acerca: "Acerca de", glosario: "Glosario" };

// Logo en frontend/public/logo-conagua.png; si falta el archivo se muestra el nombre.
function LogoConagua() {
  const [falta, setFalta] = useState(false);
  return (
    <span className="cabecera-logo" title="Datos: Sistema de Información Hidrológica de CONAGUA">
      {falta ? <b>CONAGUA</b> : <img src="/logo-conagua.png" alt="CONAGUA" onError={() => setFalta(true)} />}
    </span>
  );
}

export default function App() {
  const [version, setVersion] = useState(0);
  const { datos: estado, error, cargando, recargar } = useApi("estado", { v: version });
  const { pathname } = useLocation();
  const [menuAbierto, setMenuAbierto] = useState(() => window.matchMedia("(min-width: 861px)").matches);
  const [mensajeActualizacion, setMensajeActualizacion] = useState(null);

  const partes = pathname.split("/"); // ["", "presas", clave, modulo]
  const presas = estado?.presas || [];
  const claveActual = partes[1] === "presas" ? partes[2] : null;
  const moduloActual = partes[1] === "presas" ? partes[3] || "consulta" : null;
  const clave = claveActual || presas[0]?.clave;
  const presaActual = presas.find((p) => p.clave === clave);

  // Título de la pestaña del navegador y cierre del menú móvil al navegar
  useEffect(() => {
    const seccion = TITULOS[moduloActual || partes[1]] || "Panorama general";
    const nombre = claveActual && presas.find((p) => p.clave === claveActual)?.nombre;
    document.title = `${nombre ? `${nombre} · ` : ""}${seccion} — PresaIA`;
    if (window.matchMedia("(max-width: 860px)").matches) setMenuAbierto(false);
    window.scrollTo({ top: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, presas.length]);

  const alCargar = useCallback(() => {
    limpiarCache();
    setVersion((v) => v + 1);
  }, []);

  return (
    <div className={`marco${menuAbierto ? "" : " menu-cerrado"}`}>
      <BarraCarga />
      <a className="saltar" href="#contenido">Saltar al contenido</a>

      <header className="cabecera">
        <NavLink to="/" className="cabecera-titulo">
          <img src="/logo-presa.png" alt="" />
          <span>PresaIA <small>Monitoreo y predicción del almacenamiento de presas</small></span>
        </NavLink>
        <div className="cabecera-derecha">
          <div className="cabecera-estado">
            {estado?.actualizacion?.fecha && (
              <Tip contenido="Cuándo se ejecutó por última vez el proceso de actualización (descarga y pronóstico)."
                tabIndex={0}>
                <span className="punto-vivo" aria-hidden="true" /> Actualizado{" "}
                <b>{new Date(estado.actualizacion.fecha).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })}</b>
              </Tip>
            )}
            {estado?.actualizacion?.ultimo_dato && (
              <Tip contenido="Fecha más reciente con mediciones publicadas por el SIH." tabIndex={0}>
                Último dato <b>{fechaLarga(estado.actualizacion.ultimo_dato)}</b>
              </Tip>
            )}
            {mensajeActualizacion && (
              <span className={mensajeActualizacion.fallo ? "error" : "actualizacion-mensaje"}>
                {mensajeActualizacion.texto}
              </span>
            )}
          </div>
          <LogoConagua />
          <BotonActualizar alTerminar={alCargar} onMensajeChange={setMensajeActualizacion} />
        </div>
      </header>

      <aside className={`lateral${menuAbierto ? " abierto" : ""}`}>
        <button className="menu-escritorio" onClick={() => setMenuAbierto((abierto) => !abierto)}
          aria-expanded={menuAbierto} aria-label={menuAbierto ? "Reducir menú" : "Expandir menú"}
          title={menuAbierto ? "Reducir menú" : "Expandir menú"}>
          <Icono nombre={menuAbierto ? "panel-izquierda" : "panel-derecha"} tam={16} />
        </button>
        <button className="menu-movil" onClick={() => setMenuAbierto((a) => !a)} aria-expanded={menuAbierto}>
          <Icono nombre={menuAbierto ? "cerrar" : "menu"} />
          <span>{menuAbierto ? "Cerrar menú" : `Menú${presaActual && claveActual ? ` · ${presaActual.nombre}` : ""}`}</span>
        </button>

        <div className="lateral-cuerpo">
          <nav className="nav" aria-label="Secciones">
            <NavLink to="/" end title="Resumen de todas las presas, mapa y ranking por riesgo"
              aria-label="Panorama general">
              <Icono nombre="panorama" /><span className="nav-texto">Panorama general</span>
            </NavLink>
          </nav>

          {cargando && !estado && <div className="lateral-cargando"><Cargando texto="Cargando presas…" /></div>}

          {presas.length > 0 && (
            <nav className="nav" aria-label="Presas">
              <div className="nav-grupo">Presas</div>
              {presas.map((p) => (
                <NavLink key={p.clave} to={`/presas/${p.clave}/${moduloActual || "consulta"}`}
                  title={p.nombre} aria-label={p.nombre}>
                  <Icono nombre="ubicacion" />
                  <span className="nav-texto">
                    {p.nombre}
                    <small>{p.estado}</small>
                  </span>
                </NavLink>
              ))}
            </nav>
          )}

          {clave && (
            <nav className="nav" aria-label="Módulos de la presa">
              <div className="nav-grupo">
                Analizar <b>{presaActual?.nombre}</b>
              </div>
              {MODULOS.map((m) => (
                <NavLink key={m.ruta} to={`/presas/${clave}/${m.ruta}`} title={m.ayuda}
                  aria-label={`${m.nombre}: ${m.ayuda}`}>
                  <Icono nombre={m.icono} />
                  <span className="nav-texto">
                    {m.nombre}
                    <small>{m.ayuda}</small>
                  </span>
                </NavLink>
              ))}
            </nav>
          )}

          <nav className="nav" aria-label="Herramientas">
            <div className="nav-grupo">Herramientas</div>
            <NavLink to="/cargar" title="Subir archivos CSV descargados del SIH" aria-label="Cargar datos">
              <Icono nombre="cargar" /><span className="nav-texto">Cargar datos</span>
            </NavLink>
            <NavLink to="/glosario" title="Qué significa cada término técnico" aria-label="Glosario">
              <Icono nombre="glosario" /><span className="nav-texto">Glosario</span>
            </NavLink>
            <NavLink to="/acerca" title="Cómo funciona y limitaciones" aria-label="Acerca de">
              <Icono nombre="acerca" /><span className="nav-texto">Acerca de</span>
            </NavLink>
          </nav>

          <p className="tenue pie">
            Herramienta de apoyo a la decisión. No sustituye a CONAGUA ni a un sistema certificado de seguridad de
            presas.
          </p>
        </div>
      </aside>

      <main className="contenido" id="contenido">
        {cargando && !estado && <Cargando texto="Conectando con PresaIA…" />}
        {error && <ErrorCarga mensaje={`No se pudo conectar con la API: ${error}`} reintentar={recargar} />}
        {estado && !estado.hay_datos && pathname !== "/cargar" && pathname !== "/glosario" && (
          <Aviso nivel="critico">
            <b>No hay datos procesados.</b> Súbelos en <NavLink to="/cargar">Cargar datos</NavLink> o ejecuta:
            <pre>{"python -m presaia todo --demo   # datos de prueba\npython -m presaia descargar && python -m presaia todo   # datos reales"}</pre>
          </Aviso>
        )}
        <div className="pagina" key={pathname}>
          {pathname === "/glosario" && <Glosario />}
          {estado && pathname === "/cargar" && (
            <Cargar presas={estado.presas_configuradas || estado.presas} alTerminar={alCargar} />
          )}
          {estado?.hay_datos && pathname !== "/cargar" && pathname !== "/glosario" && (
            <Routes>
              <Route path="/" element={<Panorama />} />
              <Route path="/presas/:clave/consulta" element={<Consulta />} />
              <Route path="/presas/:clave/prediccion" element={<Prediccion />} />
              <Route path="/presas/:clave/avisos" element={<Avisos umbralesBase={estado.umbrales} />} />
              <Route path="/presas/:clave" element={<Navigate to="consulta" replace />} />
              <Route path="/acerca" element={<Acerca modelos={estado.modelos} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
        </div>
      </main>
    </div>
  );
}
