#!/usr/bin/env python
"""Utilidad de línea de comandos de Django para la API de PresaIA."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "presaia_web.settings")
    from django.core.management import execute_from_command_line
    from django.core.management.commands import runserver

    # Puerto por defecto de runserver (8000 suele estar ocupado); se puede cambiar con PRESAIA_PUERTO.
    runserver.Command.default_port = os.environ.get("PRESAIA_PUERTO", "8010")

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
