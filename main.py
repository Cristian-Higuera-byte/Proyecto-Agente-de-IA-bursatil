"""Chat por terminal para probar el agente.   Ejecutar:  python main.py"""
import config
from core.agente import Agente  # type: ignore[import-untyped]
from core.llm import ErrorLLM  # type: ignore[import-untyped]

AYUDA = "Comandos: /reset (nueva conversación), /perfil <nombre>, /pensar (ver/ocultar razonamiento), /salir"


def main() -> None:
    try:
        agente = Agente(usuario_id="local")
    except RuntimeError as e:
        print(e)
        return

    mostrar_razonamiento = False
    print("Agente bursátil listo.")
    print("Memoria:", f"activa (chat {str(agente.memoria.chat_id)[:8]})" if agente.memoria else "DESACTIVADA")
    print(AYUDA)

    while True:
        try:
            entrada = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not entrada:
            continue

        if entrada == "/salir":
            break
        if entrada == "/reset":
            agente.reiniciar()
            print("Conversación reiniciada.")
            continue
        if entrada == "/pensar":
            mostrar_razonamiento = not mostrar_razonamiento
            print(f"Razonamiento visible: {mostrar_razonamiento}")
            continue
        if entrada.startswith("/perfil"):
            partes = entrada.split()
            if len(partes) == 2 and partes[1] in config.PERFILES:
                agente.perfil = partes[1]
                print(f"Perfil activo: {partes[1]}")
            else:
                print("Perfiles disponibles:", ", ".join(config.PERFILES))
            continue

        print("\nAgente: ", end="", flush=True)
        try:
            for ev in agente.responder_stream(entrada):
                if ev.tipo == "texto":
                    print(ev.texto, end="", flush=True)
                elif ev.tipo == "razonamiento" and mostrar_razonamiento:
                    print(ev.texto, end="", flush=True)
                elif ev.tipo == "herramienta":
                    print(f"\n  [herramienta] {ev.texto}({ev.datos})", flush=True)
                elif ev.tipo == "fin":
                    d = ev.datos
                    print(f"\n  [{d['tokens_entrada']} entrada / {d['tokens_salida']} salida | perfil: {d['perfil']}]")
        except ErrorLLM as e:
            print(f"\n[Error] {e}")


if __name__ == "__main__":
    main()