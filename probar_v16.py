"""Prueba TEMPORAL de V16 con peticiones reales desde el servidor (se borra despues de usarla)."""
import os, sys, time
from urllib.parse import quote
sys.path.insert(0, os.getcwd())
from herramientas import descarga_segura as ds
from componentes_plataforma.noticias import rss
def t(nombre, f):
    t0 = time.time()
    try:
        r = f(); print(f"{nombre}: OK {r} ({time.time()-t0:.1f}s)")
    except ds.DescargaRechazada as e:
        print(f"{nombre}: RECHAZADA -> {e}")
    except Exception as e:
        print(f"{nombre}: ERROR {type(e).__name__} {str(e)[:60]}")
cab = {"User-Agent": rss._AGENTE}
def feed():
    r = ds.abrir("https://es.investing.com/rss/news_25.rss", cabeceras=cab, max_bytes=3000000)
    n = rss._parsear(r.cuerpo, {"nombre": "x", "idioma": "ES"})
    return (r.estado, len(r.cuerpo), f"{len(n)} noticias")
t("1 feed real (https)", feed)
t("2 articulo real (http->https)", lambda: ds.abrir("http://www.example.com/", cabeceras=cab).estado)
for u in ["http://127.0.0.1:28501/", "http://127.0.0.1:28000/t/demo/salud", "http://localhost:28501/", "http://169.254.169.254/latest/meta-data/", "http://[::1]:28501/", "http://10.0.0.1/", "http://2130706433:28501/"]:
    t("3 directo " + u[7:40], lambda u=u: ds.abrir(u).estado)
def redir(host, d):
    r = ds.abrir(f"https://{host}/redirect-to?url=" + quote(d, safe=""), espera=8, cabeceras=cab)
    return (r.estado, r.url_final[:60])
for dest in ["http://127.0.0.1:28501/", "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/"]:
    t("4 redireccion real httpbingo -> " + dest[7:36], lambda d=dest: redir("httpbingo.org", d))
t("5 redireccion real httpbingo -> example.com (permitida)", lambda: redir("httpbingo.org", "http://www.example.com/"))
t("6 salto real publico->publico http://github.com/", lambda: (lambda r: (r.estado, r.url_final))(ds.abrir("http://github.com/", cabeceras=cab)))
