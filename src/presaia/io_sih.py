"""Lectura de archivos del Sistema de Información Hidrológica (SIH) de CONAGUA.

Formato observado en https://sih.conagua.gob.mx/basedatos/Presas/<CLAVE>.csv
(consultado el 13-oct-2026):

    Comisión Nacional del Agua
    Subdirección General Técnica
    Estación: Valle de Bravo, Méx.
    Clave: VBRMX
    Estado: México
    Municipio: Valle de Bravo

    Estacion,Fecha,Nivel(m),Precipitacion(mm),VolumenAlm(Mm3),ObraToma(m3/s),...
    VBRMX,1977-01-01,1819.24,,,,,,

Particularidades que este módulo resuelve:
  * Encabezado de metadatos de longitud variable antes de la tabla.
  * El ORDEN de las columnas cambia entre presas (p. ej. Nivel antes o después
    de Precipitacion), por eso se mapean por nombre y nunca por posición.
  * Columnas vacías durante décadas y filas finales truncadas.
  * Unidades: Mm3 = millones de m³ = hm³. Se renombra a ``volumen_hm3``.
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Nombre original (normalizado) -> nombre interno, unidad
MAPA_COLUMNAS: dict[str, tuple[str, str]] = {
    "estacion": ("clave", ""),
    "fecha": ("fecha", ""),
    "nivel(m)": ("nivel_m", "m s.n.m."),
    "precipitacion(mm)": ("precip_mm", "mm/día"),
    "volumenalm(mm3)": ("volumen_hm3", "hm³"),
    "obratoma(m3/s)": ("obra_toma_m3s", "m³/s"),
    "vertedor(m3/s)": ("vertedor_m3s", "m³/s"),
    "derrame(m3/s)": ("derrame_m3s", "m³/s"),
    "evaporacion(mm)": ("evap_mm", "mm/día"),
}

COLUMNAS_NUMERICAS = [v[0] for k, v in MAPA_COLUMNAS.items() if k not in ("estacion", "fecha")]


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni espacios: 'Precipitación (mm)' -> 'precipitacion(mm)'."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", "", t).lower()


def _leer_texto(ruta: Path) -> str:
    crudo = ruta.read_bytes()
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return crudo.decode("utf-8", errors="replace")


@dataclass
class SerieSIH:
    """Serie diaria de una presa junto con los metadatos del encabezado."""

    clave: str
    datos: pd.DataFrame
    metadatos: dict[str, str] = field(default_factory=dict)
    ruta: Path | None = None

    @property
    def es_sintetica(self) -> bool:
        return "SINTETICO" in self.metadatos.get("fuente", "").upper()

    @property
    def nombre(self) -> str:
        return self.metadatos.get("estacion", self.clave)


def leer_csv_sih(ruta: str | Path) -> SerieSIH:
    """Lee un CSV del SIH y devuelve una :class:`SerieSIH` con columnas internas.

    El DataFrame resultante tiene índice ``fecha`` (DatetimeIndex, diario, sin
    duplicados) y columnas numéricas en ``COLUMNAS_NUMERICAS`` (las que existan).
    """
    ruta = Path(ruta)
    lineas = _leer_texto(ruta).splitlines()

    # 1) Localizar la línea de encabezado de la tabla
    idx_encabezado = next(
        (i for i, l in enumerate(lineas) if _normalizar(l).startswith("estacion,fecha")),
        None,
    )
    if idx_encabezado is None:
        raise ValueError(f"{ruta.name}: no se encontró el encabezado 'Estacion,Fecha'")

    # 2) Metadatos 'Clave: valor' previos a la tabla
    metadatos: dict[str, str] = {}
    for l in lineas[:idx_encabezado]:
        if ":" in l:
            k, v = l.split(":", 1)
            metadatos[_normalizar(k)] = v.strip()

    # 3) Tabla
    tabla = "\n".join(lineas[idx_encabezado:])
    df = pd.read_csv(io.StringIO(tabla), dtype=str, on_bad_lines="skip")
    renombres, desconocidas = {}, []
    for col in df.columns:
        n = _normalizar(col)
        if n in MAPA_COLUMNAS:
            renombres[col] = MAPA_COLUMNAS[n][0]
        else:
            desconocidas.append(col)
            renombres[col] = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    df = df.rename(columns=renombres)

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", format="%Y-%m-%d")
    df = df.dropna(subset=["fecha"])
    for c in df.columns:
        if c not in ("clave", "fecha"):
            df[c] = pd.to_numeric(df[c], errors="coerce")

    clave = metadatos.get("clave") or (df["clave"].dropna().iloc[0] if len(df) else ruta.stem)
    df = (
        df.drop(columns=["clave"], errors="ignore")
        .sort_values("fecha")
        .drop_duplicates("fecha", keep="last")
        .set_index("fecha")
    )
    for c in COLUMNAS_NUMERICAS:
        if c not in df.columns:
            df[c] = np.nan
    if desconocidas:
        metadatos["columnas_no_reconocidas"] = ", ".join(desconocidas)
    return SerieSIH(clave=str(clave).strip(), datos=df, metadatos=metadatos, ruta=ruta)


def leer_catalogo(ruta: str | Path) -> pd.DataFrame:
    """Lee 0_Catalogo_de_presas.csv y normaliza nombres de columnas."""
    texto = _leer_texto(Path(ruta))
    df = pd.read_csv(io.StringIO(texto), dtype=str)
    mapa = {
        "numero": "numero", "clave": "clave", "nombredelapresa": "nombre",
        "latitud": "latitud", "longitud": "longitud", "altitud": "altitud",
        "estado": "estado", "municipio": "municipio",
        "identificadordelacuencadedisponibilidad": "id_cuenca",
        "cuencadedisponibilidad": "cuenca",
        "numerodelaregionhidrologica": "num_region",
        "regionhidrologica": "region_hidrologica",
    }
    df = df.rename(columns={c: mapa.get(_normalizar(c), _normalizar(c)) for c in df.columns})
    for c in ("latitud", "longitud", "altitud"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["clave"] = df["clave"].str.strip()
    return df


def escribir_csv_sih(serie: pd.DataFrame, ruta: Path, metadatos: dict[str, str], clave: str) -> None:
    """Escribe un DataFrame en el mismo formato del SIH (usado por los datos demo)."""
    nombres_sih = {
        "nivel_m": "Nivel(m)", "precip_mm": "Precipitacion(mm)", "volumen_hm3": "VolumenAlm(Mm3)",
        "obra_toma_m3s": "ObraToma(m3/s)", "vertedor_m3s": "Vertedor(m3/s)",
        "derrame_m3s": "Derrame(m3/s)", "evap_mm": "Evaporacion(mm)",
    }
    salida = serie[[c for c in nombres_sih if c in serie.columns]].copy()
    salida = salida.rename(columns=nombres_sih).round(3)
    salida.insert(0, "Fecha", serie.index.strftime("%Y-%m-%d"))
    salida.insert(0, "Estacion", clave)
    encabezado = "\n".join(f"{k}: {v}" for k, v in metadatos.items())
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(encabezado + "\n\n")
        salida.to_csv(f, index=False)
