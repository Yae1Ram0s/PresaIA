export const ETIQUETA = { critico: "Crítico", atencion: "Atención", informativo: "Informativo", normal: "Normal" };
export const ICONO = { critico: "alerta", atencion: "alerta", informativo: "info", normal: "normal" };

const nf = (dec) => new Intl.NumberFormat("es-MX", { minimumFractionDigits: dec, maximumFractionDigits: dec });

export const num = (x, dec = 1) => (x == null ? "s/d" : nf(dec).format(x));
export const pct = (x, dec = 1) => (x == null ? "s/d" : `${nf(dec).format(x)} %`);
export const pp = (x, dec = 1) => (x == null ? "s/d" : `${x >= 0 ? "+" : ""}${nf(dec).format(x)} pp`);

export function fecha(iso) {
  if (!iso) return "s/d";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export const fechaCorta = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(2, 4)}` : "");

// Colores de serie compartidos por las gráficas (definidos en estilos.css)
export const COLORES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)", "var(--serie-4)", "var(--serie-5)"];
