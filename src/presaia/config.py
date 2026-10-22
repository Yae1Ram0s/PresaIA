"""Carga de configuración desde config.toml.

Todas las rutas se resuelven respecto a la raíz del proyecto, de modo que los
scripts funcionan sin importar desde qué carpeta se ejecuten.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Presa:
    clave: str
    nombre: str
    estado: str
    sistema: str
    capacidad_namo_hm3: float
    latitud: float | None = None
    longitud: float | None = None

    @property
    def etiqueta(self) -> str:
        return f"{self.nombre} ({self.clave})"


class Config:
    """Envoltura ligera sobre el diccionario TOML con accesos tipados."""

    def __init__(self, datos: dict[str, Any], raiz: Path = RAIZ):
        self._d = datos
        self.raiz = raiz

    # --- acceso genérico -------------------------------------------------
    def __getitem__(self, clave: str) -> Any:
        return self._d[clave]

    def get(self, clave: str, defecto: Any = None) -> Any:
        return self._d.get(clave, defecto)

    # --- rutas -------------------------------------------------------------
    def ruta(self, nombre: str) -> Path:
        p = self.raiz / self._d["rutas"][nombre]
        if nombre != "catalogo":
            p.mkdir(parents=True, exist_ok=True)
        return p

    # --- presas ------------------------------------------------------------
    @property
    def presas(self) -> list[Presa]:
        return [Presa(**p) for p in self._d["presas"]]

    def presa(self, clave: str) -> Presa:
        for p in self.presas:
            if p.clave == clave:
                return p
        raise KeyError(f"La presa {clave} no está en config.toml")

    @property
    def semilla(self) -> int:
        return int(self._d["proyecto"]["semilla"])


def cargar_config(ruta: str | Path | None = None) -> Config:
    ruta = Path(ruta) if ruta else RAIZ / "config.toml"
    with open(ruta, "rb") as f:
        datos = tomllib.load(f)
    return Config(datos, raiz=ruta.parent)
