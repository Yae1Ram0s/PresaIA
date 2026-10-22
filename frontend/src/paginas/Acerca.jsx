import { Link } from "react-router-dom";
import { Termino } from "../componentes.jsx";

export default function Acerca({ modelos }) {
  const versiones = Object.entries(modelos || {});
  return (
    <article className="prosa">
      <h1>Acerca de PresaIA</h1>
      <p className="intro">
        ¿No conoces algún término? Consulta el <Link to="/glosario">glosario</Link> o pasa el cursor sobre las palabras
        subrayadas.
      </p>
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
      <h2>Arquitectura</h2>
      <p>
        El núcleo de aprendizaje automático (<code>src/presaia/</code>) genera datos, modelos y métricas con{" "}
        <code>python -m presaia todo</code>. Una API en Django los expone como JSON y esta aplicación en React los
        presenta. Ninguna capa duplica la lógica de la otra.
      </p>
      <h2>Limitaciones</h2>
      <ul>
        <li>No incorpora pronósticos meteorológicos; una tormenta extraordinaria futura no se anticipa.</li>
        <li>No conoce decisiones de operación (cambios en extracciones o trasvases).</li>
        <li>Las alertas son reglas sobre umbrales, no una evaluación de seguridad estructural.</li>
      </ul>
      {versiones.length > 0 && (
        <p className="tenue">
          Versión de los modelos:{" "}
          {versiones.map(([k, f]) => `${k} entrenado con datos hasta ${f ?? "?"}`).join(", ")}
        </p>
      )}
    </article>
  );
}
