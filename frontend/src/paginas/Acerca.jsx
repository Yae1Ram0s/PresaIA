import { Link } from "react-router-dom";
import { Icono, Termino } from "../componentes.jsx";

export default function Acerca({ modelos }) {
  const versiones = Object.entries(modelos || {});
  return (
    <article className="prosa acerca">
      <div className="acerca-marca">
        <img src="/logo-presa.png" alt="Logo de PresaIA" />
        <h1>Acerca de PresaIA</h1>
      </div>
      <div className="caja caja-informativo acerca-nota">
        <p className="intro">
          ¿No conoces algún término? Consulta el <Link to="/glosario">glosario</Link> o pasa el cursor sobre las palabras
          subrayadas.
        </p>
      </div>
      <div className="acerca-tarjetas">
        <section className="caja acerca-tarjeta acerca-funciona">
          <h2>¿Cómo funciona?</h2>
          <ol>
            <li><b>Datos</b>: registros diarios del <Termino t="sih">Sistema de Información Hidrológica (SIH)</Termino> de CONAGUA: volumen
              almacenado, nivel, precipitación, extracciones y evaporación.</li>
            <li><b>Limpieza</b>: rango físico, picos aislados, reconstrucción desde nivel (<Termino t="curva_ev">curva elevación–volumen</Termino>) y
              relleno solo de huecos cortos. Cada dato conserva una <Termino t="bandera">bandera de calidad</Termino>.</li>
            <li><b>Variables</b>: estado actual, cambios recientes, dinámica de 7/30/90 días, lluvia acumulada y
              calendario. Todas usan solo información disponible el día de emisión.</li>
            <li><b>Modelos</b>: se predice el <i>cambio</i> de almacenamiento a 7, 15 y 30 días con <Termino t="random_forest">Random Forest</Termino> y{" "}
              <Termino t="xgboost">XGBoost</Termino>, y se comparan contra <Termino t="persistencia">persistencia</Termino>, tendencia reciente y regresión lineal.</li>
            <li><b>Evaluación</b>: <Termino t="embargo">partición cronológica con embargo</Termino>; el periodo más reciente se reserva para prueba.</li>
            <li><b>Incertidumbre</b>: intervalo calibrado con los errores del periodo de validación (<Termino t="conformal">método conformal</Termino>).</li>
          </ol>
        </section>
        <section className="caja acerca-tarjeta">
          <h2>Arquitectura</h2>
          <div className="arquitectura-flujo">
            <div className="arquitectura-paso">
              <span className="arquitectura-icono"><Icono nombre="codigo" tam={30} /></span>
              <p>
                El núcleo de aprendizaje automático (<code>src/presaia/</code>) genera datos, modelos y métricas con{" "}
                <code>python -m presaia todo</code>.
              </p>
            </div>
            <Icono nombre="flecha-derecha" className="arquitectura-conector" tam={18} />
            <div className="arquitectura-paso">
              <span className="arquitectura-icono"><Icono nombre="api" tam={30} /></span>
              <p>Una API en Django los expone como JSON</p>
            </div>
            <Icono nombre="flecha-derecha" className="arquitectura-conector" tam={18} />
            <div className="arquitectura-paso">
              <span className="arquitectura-icono"><Icono nombre="interfaz" tam={30} /></span>
              <p>React se encarga de presentarlos. Ninguna capa duplica la lógica de la otra.</p>
            </div>
          </div>
        </section>
        <section className="caja acerca-tarjeta">
          <h2>Limitaciones</h2>
          <ul>
            <li><Icono nombre="cerrar" className="acerca-limitacion-icono" />No incorpora pronósticos meteorológicos; una tormenta extraordinaria futura no se anticipa.</li>
            <li><Icono nombre="cerrar" className="acerca-limitacion-icono" />No conoce decisiones de operación (cambios en extracciones o trasvases).</li>
            <li><Icono nombre="alerta" className="acerca-limitacion-icono acerca-limitacion-alerta" />Las alertas son reglas sobre umbrales, no una evaluación de seguridad estructural.</li>
          </ul>
        </section>
      </div>
      {versiones.length > 0 && (
        <p className="tenue caja acerca-versiones">
          Versión de los modelos:{" "}
          {versiones.map(([k, f]) => `${k} entrenado con datos hasta ${f ?? "?"}`).join(", ")}
        </p>
      )}
    </article>
  );
}
