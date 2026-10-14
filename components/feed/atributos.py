"""Atributos data-pj-* que los componentes ponen en sus etiquetas para que el feed pinte los números."""


def attrs(simbolo: str, campo: str = "px", **extra) -> str:
    """Atributos data-pj-* listos para meter en una etiqueta HTML."""
    partes = [f'data-pj-s="{simbolo}"', f'data-pj-f="{campo}"']
    for k, v in extra.items():
        partes.append(f'data-pj-{k}="{v}"')
    return " ".join(partes)
