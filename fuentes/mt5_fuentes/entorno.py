"""Carga del .env (configuracion.py o, si no está, python-dotenv) antes de leer cualquier variable de MT5."""
try:
    import configuracion  # noqa: F401
except ImportError:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
