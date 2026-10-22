// Glosario de términos técnicos. Lo usan los tooltips (<Ayuda termino="..." />) y la página Glosario.
// Cada entrada: titulo, definicion (texto llano) y, opcionalmente, ejemplo y categoria.

export const CATEGORIAS = {
  presa: "La presa",
  medidas: "Unidades y medidas",
  datos: "Datos y calidad",
  modelo: "Modelos de predicción",
  precision: "Precisión y evaluación",
  avisos: "Avisos y umbrales",
};

export const GLOSARIO = {
  // ── La presa ─────────────────────────────────────────────
  namo: {
    titulo: "NAMO (Nivel de Aguas Máximas Ordinarias)",
    definicion:
      "Es el nivel máximo al que la presa puede llenarse en operación normal. La capacidad al NAMO es la referencia del 100 % de llenado.",
    ejemplo: "Si la capacidad NAMO es 400 hm³ y hay 300 hm³ almacenados, la presa está al 75 %.",
    categoria: "presa",
  },
  llenado: {
    titulo: "Porcentaje de llenado",
    definicion:
      "Qué tan llena está la presa respecto a su capacidad NAMO. 100 % = llena en operación normal; puede superarlo durante avenidas.",
    categoria: "presa",
  },
  volumen: {
    titulo: "Volumen almacenado",
    definicion: "Cantidad de agua que hay en el embalse en un día dado, medida en hectómetros cúbicos (hm³).",
    categoria: "presa",
  },
  sistema: {
    titulo: "Sistema",
    definicion:
      "Conjunto de presas y obras que operan juntas para abastecer una región (p. ej. Sistema Cutzamala para la Ciudad de México).",
    categoria: "presa",
  },
  cuenca: {
    titulo: "Cuenca",
    definicion: "Territorio cuya lluvia escurre hacia el mismo río o embalse. Determina de dónde llega el agua a la presa.",
    categoria: "presa",
  },
  region_hidrologica: {
    titulo: "Región hidrológica",
    definicion: "Agrupación de cuencas que CONAGUA usa para administrar el agua a nivel nacional.",
    categoria: "presa",
  },
  clave_sih: {
    titulo: "Clave SIH",
    definicion: "Identificador de cinco letras que usa CONAGUA para cada presa. También es el nombre del archivo CSV de datos.",
    ejemplo: "VBRMX = Valle de Bravo, Estado de México.",
    categoria: "presa",
  },
  promedio_mes: {
    titulo: "Promedio histórico del mes",
    definicion:
      "Llenado promedio de todos los años registrados para el mes actual. Sirve para saber si la presa está por encima o por debajo de lo normal en esta época.",
    categoria: "presa",
  },
  hace_un_anio: {
    titulo: "Llenado hace un año",
    definicion: "Llenado de la misma fecha del año anterior. Permite comparar sin el efecto de la temporada.",
    categoria: "presa",
  },
  almacenamiento_conjunto: {
    titulo: "Almacenamiento conjunto",
    definicion:
      "Llenado de todas las presas sumadas como si fueran una sola: volumen total ÷ capacidad total. Las presas grandes pesan más.",
    categoria: "presa",
  },

  // ── Unidades ────────────────────────────────────────────
  hm3: {
    titulo: "hm³ (hectómetro cúbico)",
    definicion: "Un millón de metros cúbicos de agua (mil millones de litros).",
    ejemplo: "1 hm³ llenaría unas 400 albercas olímpicas.",
    categoria: "medidas",
  },
  pp: {
    titulo: "pp (puntos porcentuales)",
    definicion:
      "Diferencia directa entre dos porcentajes. Pasar de 60 % a 55 % es una caída de 5 pp (no de 5 %).",
    categoria: "medidas",
  },
  delta: {
    titulo: "Δ (delta, cambio)",
    definicion: "El símbolo Δ indica cuánto cambió un valor en un periodo. Positivo = subió; negativo = bajó.",
    ejemplo: "Δ 30 d = +2,0 pp significa que el llenado subió 2 puntos en los últimos 30 días.",
    categoria: "medidas",
  },
  tendencia: {
    titulo: "Tendencia observada",
    definicion:
      "Ritmo al que ha cambiado el llenado en los últimos días, expresado en pp por mes. Se calcula con datos reales, no con el modelo.",
    categoria: "medidas",
  },
  sd: {
    titulo: "s/d (sin dato)",
    definicion: "No hay información suficiente para calcular ese valor.",
    categoria: "medidas",
  },

  // ── Datos ───────────────────────────────────────────────
  sih: {
    titulo: "SIH (Sistema de Información Hidrológica)",
    definicion:
      "Base de datos pública de CONAGUA con mediciones diarias de volumen, nivel, lluvia, extracciones y evaporación de las presas del país.",
    categoria: "datos",
  },
  bandera: {
    titulo: "Bandera de calidad",
    definicion: "Etiqueta que indica de dónde salió cada valor diario: medido, reconstruido, rellenado o faltante.",
    categoria: "datos",
  },
  observado: {
    titulo: "Observado",
    definicion: "Valor medido y publicado directamente por el SIH. Es el dato más confiable.",
    categoria: "datos",
  },
  reconstruido_nivel: {
    titulo: "Reconstruido desde nivel",
    definicion:
      "Día sin volumen pero con nivel del agua. El volumen se estima con la curva elevación–volumen de la presa.",
    categoria: "datos",
  },
  interpolado: {
    titulo: "Interpolado",
    definicion:
      "Hueco corto (pocos días) rellenado trazando una línea entre el valor anterior y el siguiente.",
    categoria: "datos",
  },
  atipico_eliminado: {
    titulo: "Atípico eliminado",
    definicion:
      "Valor descartado por ser físicamente imposible o un pico aislado (p. ej. un salto diario enorme que se revierte al día siguiente).",
    categoria: "datos",
  },
  faltante: {
    titulo: "Faltante",
    definicion: "Día sin dato que no se pudo recuperar. No se usa para entrenar los modelos.",
    categoria: "datos",
  },
  curva_ev: {
    titulo: "Curva elevación–volumen",
    definicion:
      "Relación entre la altura del agua y el volumen almacenado. Se ajusta con los días que tienen ambas mediciones.",
    categoria: "datos",
  },
  cobertura_datos: {
    titulo: "Cobertura de datos",
    definicion: "Porcentaje de días del periodo que tienen un valor de volumen utilizable.",
    categoria: "datos",
  },
  sintetico: {
    titulo: "Datos sintéticos (demostración)",
    definicion: "Datos inventados para probar el sistema. No describen la situación real de ninguna presa.",
    categoria: "datos",
  },
  resumida_semanal: {
    titulo: "Serie resumida por semana",
    definicion:
      "Cuando hay demasiados días para dibujar, se muestra el promedio de cada semana. La tendencia se conserva.",
    categoria: "datos",
  },

  // ── Modelo ──────────────────────────────────────────────
  pronostico: {
    titulo: "Pronóstico",
    definicion: "Estimación del llenado futuro hecha por el modelo con los datos disponibles el día de emisión.",
    categoria: "modelo",
  },
  horizonte: {
    titulo: "Horizonte",
    definicion: "Cuántos días hacia adelante se pronostica. A mayor horizonte, mayor incertidumbre.",
    ejemplo: "Horizonte de 30 días = estimación de cómo estará la presa dentro de un mes.",
    categoria: "modelo",
  },
  fecha_emision: {
    titulo: "Fecha de emisión",
    definicion: "Día en que se hace el pronóstico; el modelo solo usa información conocida hasta esa fecha.",
    categoria: "modelo",
  },
  simulacion: {
    titulo: "Simular en una fecha pasada",
    definicion:
      "Hace el pronóstico como si estuvieras en una fecha del pasado y lo compara con lo que realmente ocurrió después. Útil para ver qué tan bien acierta.",
    categoria: "modelo",
  },
  intervalo: {
    titulo: "Intervalo de confianza",
    definicion:
      "Rango donde se espera que caiga el valor real. Con un intervalo del 90 %, el valor real debería quedar dentro 9 de cada 10 veces.",
    categoria: "modelo",
  },
  conformal: {
    titulo: "Método conformal",
    definicion:
      "Forma de calcular el intervalo usando los errores reales que el modelo cometió en un periodo de validación, sin suponer una distribución.",
    categoria: "modelo",
  },
  random_forest: {
    titulo: "Random Forest",
    definicion:
      "Modelo que combina cientos de árboles de decisión y promedia sus respuestas. Robusto y difícil de sobreajustar.",
    categoria: "modelo",
  },
  xgboost: {
    titulo: "XGBoost",
    definicion:
      "Modelo de árboles construidos uno tras otro, donde cada árbol corrige los errores del anterior. Suele ser muy preciso.",
    categoria: "modelo",
  },
  persistencia: {
    titulo: "Persistencia (referencia)",
    definicion:
      "Modelo más simple posible: supone que la presa seguirá igual que hoy. Si un modelo no mejora a la persistencia, no aporta valor.",
    categoria: "modelo",
  },
  tendencia_30d: {
    titulo: "Tendencia 30 días (referencia)",
    definicion: "Supone que la presa seguirá cambiando al mismo ritmo de los últimos 30 días.",
    categoria: "modelo",
  },
  regresion_lineal: {
    titulo: "Regresión lineal (Ridge)",
    definicion: "Modelo estadístico clásico que combina las variables con pesos fijos. Sirve de referencia intermedia.",
    categoria: "modelo",
  },
  importancia: {
    titulo: "Importancia de variables",
    definicion: "Cuánto influye cada dato de entrada (lluvia, cambios recientes, mes…) en las predicciones del modelo.",
    categoria: "modelo",
  },

  // ── Precisión ───────────────────────────────────────────
  mae: {
    titulo: "MAE (Error Absoluto Medio)",
    definicion:
      "En promedio, cuánto se equivoca el pronóstico, sin importar si fue hacia arriba o hacia abajo. Menor = mejor.",
    ejemplo: "MAE = 2 hm³ → el pronóstico suele fallar por unos 2 hm³.",
    categoria: "precision",
  },
  rmse: {
    titulo: "RMSE (Raíz del Error Cuadrático Medio)",
    definicion:
      "Parecido al MAE, pero castiga más los errores grandes. Si es mucho mayor que el MAE, hay fallos ocasionales fuertes.",
    categoria: "precision",
  },
  mape: {
    titulo: "MAPE (Error Porcentual Absoluto Medio)",
    definicion: "Error promedio expresado como porcentaje del valor real.",
    categoria: "precision",
  },
  mae_pp: {
    titulo: "MAE en pp de llenado",
    definicion: "El error medio convertido a puntos porcentuales de llenado, más fácil de interpretar que los hm³.",
    categoria: "precision",
  },
  acierto_direccion: {
    titulo: "Acierto de dirección",
    definicion: "Porcentaje de veces que el modelo acertó si la presa iba a subir o a bajar.",
    categoria: "precision",
  },
  mejora_persistencia: {
    titulo: "Mejora vs. persistencia",
    definicion:
      "Cuánto menor es el error del modelo comparado con suponer que nada cambia. 30 % = el modelo se equivoca 30 % menos.",
    categoria: "precision",
  },
  cobertura_intervalo: {
    titulo: "Cobertura del intervalo",
    definicion:
      "Porcentaje de veces que el valor real cayó dentro del intervalo en el periodo de prueba. Debería parecerse al nivel nominal (p. ej. 90 %).",
    categoria: "precision",
  },
  periodo_prueba: {
    titulo: "Periodo de prueba",
    definicion:
      "Datos más recientes que se apartaron y el modelo nunca vio al entrenar. Medir ahí da una idea honesta de la precisión real.",
    categoria: "precision",
  },
  backtest: {
    titulo: "Backtest (prueba retrospectiva)",
    definicion: "Comparación día a día entre lo que el modelo habría pronosticado y lo que realmente ocurrió.",
    categoria: "precision",
  },
  embargo: {
    titulo: "Partición con embargo",
    definicion:
      "Se deja un hueco entre los datos de entrenamiento y los de prueba para que el modelo no “vea el futuro” por accidente.",
    categoria: "precision",
  },

  // ── Avisos ──────────────────────────────────────────────
  estado_presa: {
    titulo: "Estado de la presa",
    definicion: "Resumen del aviso más grave: Normal, Atención o Crítico, según los umbrales configurados.",
    categoria: "avisos",
  },
  critico: {
    titulo: "Crítico",
    definicion: "El llenado actual o proyectado está por debajo del umbral crítico, o se espera un descenso fuerte.",
    categoria: "avisos",
  },
  atencion: {
    titulo: "Atención",
    definicion: "Situación que conviene vigilar: llenado bajo o descenso moderado, aún sin llegar a nivel crítico.",
    categoria: "avisos",
  },
  normal: {
    titulo: "Normal",
    definicion: "Ningún umbral de alerta se ha superado.",
    categoria: "avisos",
  },
  informativo: {
    titulo: "Informativo",
    definicion: "Nota que no implica riesgo, por ejemplo datos desactualizados o una tendencia de recuperación.",
    categoria: "avisos",
  },
  umbral_llenado_atencion: {
    titulo: "Llenado de atención",
    definicion: "Si el llenado (actual o proyectado) baja de este porcentaje, se emite un aviso de atención.",
    categoria: "avisos",
  },
  umbral_llenado_critico: {
    titulo: "Llenado crítico",
    definicion: "Si el llenado baja de este porcentaje, el aviso es crítico. Debe ser menor que el de atención.",
    categoria: "avisos",
  },
  umbral_descenso_atencion: {
    titulo: "Descenso de atención",
    definicion: "Caída proyectada (en pp) dentro del horizonte a partir de la cual se avisa con nivel de atención.",
    categoria: "avisos",
  },
  umbral_descenso_critico: {
    titulo: "Descenso crítico",
    definicion: "Caída proyectada (en pp) a partir de la cual el aviso es crítico. Debe ser mayor que la de atención.",
    categoria: "avisos",
  },
  proyectado: {
    titulo: "Llenado proyectado",
    definicion: "Llenado que el modelo estima para el horizonte más lejano disponible (p. ej. dentro de 30 días).",
    categoria: "avisos",
  },
};

/** Clave de glosario para los nombres de modelo que devuelve la API. */
export const TERMINO_MODELO = {
  "Random Forest": "random_forest",
  XGBoost: "xgboost",
  Persistencia: "persistencia",
  "Tendencia 30 días": "tendencia_30d",
  "Regresión lineal (Ridge)": "regresion_lineal",
};

/** Normaliza texto para buscar sin importar mayúsculas ni acentos. */
export const normalizar = (s) =>
  String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
