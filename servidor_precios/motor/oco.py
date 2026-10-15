"""OCO (One-Cancels-the-Other) del motor."""
import MetaTrader5 as mt5  # type: ignore[import-untyped]
from herramientas import almacen_oco
from herramientas.puente_mt5 import eliminar_orden

from ..constantes import CANDADO_MT5


class MixinOco:
    # --- OCO (One-Cancels-the-Other) --------------------------------------
    # Dos órdenes pendientes vinculadas: cuando UNA se ejecuta (pasa a posición),
    # se cancela la otra. MT5 no tiene OCO nativo: la lógica vive aquí (cliente),
    # por eso solo funciona con este proceso vivo. La config la escribe el ticket
    # de órdenes en data/oco.json (otro proceso).
    def _recargar_oco(self):
        m = almacen_oco.mtime()
        if m != self._oco_mtime:
            self._oco = almacen_oco.leer()
            self._oco_mtime = m
            # olvida pares "armados" que ya no existen
            self._oco_armados &= set(self._oco.keys())

    def _paso_oco(self):
        self._recargar_oco()
        if not self._oco:
            return
        with CANDADO_MT5:
            ordenes = mt5.orders_get() or []
            posiciones = mt5.positions_get() or []
        # tickets de órdenes pendientes vivas ahora mismo
        vivos = {int(o.ticket) for o in ordenes if int(o.type) in (2, 3, 4, 5)}
        # tickets que ya son posición (una pendiente al ejecutarse conserva su ticket
        # como identifier de la posición): sirve para distinguir "ejecutada" de "cancelada"
        en_posicion = set()
        for p in posiciones:
            en_posicion.add(int(p.ticket))
            en_posicion.add(int(getattr(p, "identifier", p.ticket)))
        for par_id in list(self._oco.keys()):
            cfg = self._oco[par_id]
            a, b = int(cfg["a"]), int(cfg["b"])
            a_vivo, b_vivo = a in vivos, b in vivos
            if a_vivo and b_vivo:
                self._oco_armados.add(par_id)        # ambas patas confirmadas
                continue
            if not (a_vivo or b_vivo):               # ninguna sigue pendiente: nada que hacer
                self._cerrar_oco(par_id)
                continue
            if par_id not in self._oco_armados:
                # Aún no se vieron las DOS vivas: puede ser la ventana entre colocar la
                # 1.ª y la 2.ª pata. Se espera a confirmarlas antes de actuar (anti-carrera).
                continue
            # Exactamente una pata sigue viva y el par estaba armado -> la otra salió del libro
            vivo = a if a_vivo else b
            ido = b if a_vivo else a
            if ido in en_posicion:                   # la otra SE EJECUTÓ -> cancela la sobrante (OCO)
                with CANDADO_MT5:
                    eliminar_orden(vivo)
            # si no está en posición, fue cancelada a mano: solo se rompe el vínculo
            self._cerrar_oco(par_id)

    def _cerrar_oco(self, par_id):
        almacen_oco.quitar_par(par_id)
        self._oco.pop(par_id, None)
        self._oco_mtime = almacen_oco.mtime()
        self._oco_armados.discard(par_id)
