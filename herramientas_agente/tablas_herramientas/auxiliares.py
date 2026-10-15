"""Funciones y constantes auxiliares de las herramientas (sin registrar nada)."""
from __future__ import annotations

import os


OUTPUT_DIR = os.path.join("static", "reportes")


os.makedirs(OUTPUT_DIR, exist_ok=True)
