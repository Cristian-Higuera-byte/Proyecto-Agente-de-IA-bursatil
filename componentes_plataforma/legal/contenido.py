# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.


# -------------------------------------------------------------------------------------------------------
# ---------------------------------- INICIO Piña y Jara contenido .PY -----------------------------------
# -------------------------------------------------------------------------------------------------------

"""Textos de los documentos legales de la plataforma: términos de uso, privacidad y cookies, y aviso de riesgo.

Cada documento es un diccionario con su título, un resumen y una lista de secciones; una sección es (título, [bloques]) y cada bloque es un texto o una lista de
textos (viñetas). Son un BORRADOR redactado a partir de lo que la plataforma hace hoy: mientras `EN_REVISION` sea True, cada página lo avisa. Cuando la empresa los
revise y apruebe, se pone `EN_REVISION = False`; y cada vez que cambie su contenido se sube `VERSION`, para saber qué versión aceptó cada usuario.

Alineación con la operación (V21 de la auditoría): los textos describen lo que la plataforma hace de verdad: las cuatro formas de operar (manual en dos pasos, One-Click, copia y vigilancia),
las comisiones y el cierre de posiciones al detener una copia, los datos que pide el alta, los destinatarios y transferencias y los plazos. Lo que depende de la configuración (operar en
cuenta real) se escribe a partir de `configuracion.OPERAR_EN_CUENTA_REAL`, para que el texto no prometa ni niegue lo que no corresponde. La versión 1.1 reemplaza a la 1.0.
"""
import configuracion

# Versión de los tres documentos (se guarda junto con la aceptación del usuario) y fecha desde la que rigen.
VERSION = "1.1"
VIGENTE_DESDE = "23 de noviembre de 2026"

# True si la configuración permite operar en cuenta real: cambia lo que los textos dicen sobre dinero real (por defecto, solo cuenta demo).
REAL_HABILITADO = bool(configuracion.OPERAR_EN_CUENTA_REAL)

# True mientras los textos no hayan sido revisados por el área legal de la empresa; las páginas muestran entonces un aviso.
EN_REVISION = True

# Datos de la empresa responsable, tomados del convenio de práctica y del sitio de la empresa.
EMPRESA = "Piña y Jara Transportes y Servicios Ltda."
RUT = "76.186.223-5"
DIRECCION = "José Joaquín Prieto 5373, San Miguel, Santiago, Chile"
CORREO = "contacto.pinayjara@gmail.com"

# Frase corta que se repite en el pie de la plataforma y junto al agente.
FRASE_RIESGO = ("P&J no entrega asesoría financiera. El agente puede ejecutar órdenes por ti si lo autorizas"
                + ("; en una cuenta real usa tu dinero y puedes perder capital. " if REAL_HABILITADO else " (hoy, solo en cuenta demo). ")
                + "Operar con CFD conlleva un alto riesgo de pérdida.")


TERMINOS = {
    "titulo": "Términos de uso",
    "resumen": "Reglas para usar P&J Finance: qué es la plataforma, qué no es y qué se espera de ti.",
    "secciones": [
        ("1. Quiénes somos", [
            f"P&J Finance es una plataforma web de análisis y práctica de trading operada por {EMPRESA}, RUT {RUT}, con domicilio en {DIRECCION}. "
            f"Puedes escribirnos a {CORREO}.",
        ]),
        ("2. Qué es y qué no es la plataforma", [
            "La plataforma ofrece herramientas para ver precios, gráficos y noticias, preparar órdenes, llevar un diario de operaciones y consultar a un agente de "
            "inteligencia artificial. Está en etapa de pruebas: puede tener errores, interrupciones o cambios sin aviso previo.",
            ["No somos una corredora de bolsa ni un bróker: las órdenes se envían al bróker donde tienes tu cuenta (hoy, Capital.com) y tu contrato es con él.",
             "No entregamos asesoría financiera ni recomendaciones de inversión personalizadas.",
             "No recibimos ni administramos dinero tuyo para operar. La billetera, los planes y las comisiones que ves en la plataforma son de demostración (saldo virtual) y no mueven dinero real."],
        ]),
        ("3. Tu cuenta", [
            ["Debes ser mayor de 18 años y entregar datos verdaderos: el registro pide tus nombres, apellidos y fecha de nacimiento para comprobar la mayoría de edad.",
             "Debes confirmar tu correo electrónico para activar la cuenta.",
             "Eres responsable de mantener en reserva tu contraseña y de lo que se haga con tu cuenta. Si crees que alguien la usó, cambia la contraseña y avísanos.",
             "Una cuenta es de una sola persona."],
        ]),
        ("4. Conexión con tu bróker", [
            "Para operar conectas tu cuenta del bróker con tus credenciales de la API. Las guardamos cifradas y solo se usan para ejecutar lo que tú pides o confirmas. "
            "Puedes desconectar tu cuenta cuando quieras. Mientras la cuenta conectada sea demo, las operaciones no usan dinero real. "
            + ("Si conectas una cuenta real, las operaciones que ordenes o confirmes usan tu dinero y son de tu exclusiva responsabilidad."
               if REAL_HABILITADO else
               "Hoy la plataforma no opera con cuentas reales: la operación con dinero real no está habilitada y, cuando se habilite, se avisará antes y te pediremos aceptar las condiciones que correspondan."),
        ]),
        ("5. Agente de inteligencia artificial", [
            "El agente responde de forma automática con datos de mercado y de tu cuenta. Puede equivocarse, estar incompleto o basarse en datos con retraso. "
            "Sus respuestas son informativas y no son asesoría financiera.",
            "El agente propone órdenes. Una orden propuesta no se envía al bróker hasta que tú la confirmas, y vence a los pocos minutos. Antes de confirmar, revisa el "
            "instrumento, el lado, el volumen y los niveles de stop loss y take profit.",
            "Además puedes autorizar «vigilancias»: reglas con las que el agente analiza el mercado por su cuenta y abre y cierra posiciones sin pedirte confirmación en cada orden, "
            "aunque no estés mirando la pantalla, dentro de los límites de riesgo que definas. Mientras una vigilancia esté activa, eres responsable de lo que opere; puedes detenerla "
            "cuando quieras. Hoy esas operaciones se ejecutan solo en tu cuenta demo"
            + ("; si en el futuro se habilitaran con cuenta real, usarían tu dinero y se te avisaría antes." if not REAL_HABILITADO else ", y con una cuenta real usarían tu dinero."),
        ]),
        ("6. Formas de operar y qué pasa en cada una", [
            ["Manual, en dos pasos (la forma estándar): preparas la orden (ticket, menú del gráfico o arrastre de una línea) y la confirmas de forma explícita. No se envía al bróker hasta completar los dos pasos.",
             "One-Click Trading (opcional, tú lo activas): la orden se envía al bróker de inmediato, en un solo paso y sin pedir confirmación, al pulsar «Colocar orden», al elegir un tipo de orden pendiente "
             "en el menú del gráfico, o al arrastrar o quitar niveles de Take Profit y Stop Loss o cancelar una orden pendiente desde el gráfico. Un clic o un arrastre involuntario envía la orden. "
             "Se activa con una aceptación aparte y puedes desactivarlo cuando quieras.",
             "Propuestas del agente: el agente prepara la orden y tú la confirmas; no se envía antes.",
             "Vigilancia automática (opcional, con autorización aparte): el agente abre y cierra posiciones por su cuenta, sin pedirte confirmación en cada orden. Hoy las vigilancias se ejecutan solo en tu cuenta demo.",
             "Copy trading (opcional): las operaciones de una estrategia que eliges se replican de forma automática en tu cuenta."
             + (" Se opera en la cuenta (demo o real) configurada, con el tamaño que elijas; en una cuenta real se usa dinero real." if REAL_HABILITADO else " Hoy solo en tu cuenta demo."),
             "En todas, el envío al bróker, el precio de ejecución, el deslizamiento (slippage), los márgenes y las comisiones o costos del bróker (como el spread o el financiamiento nocturno) los define tu bróker y se rigen por tu contrato con él."],
        ]),
        ("7. Copy trading: comisiones, detención y posiciones abiertas", [
            ["Copiar una estrategia no garantiza resultados: puede haber diferencias de precio, retrasos y operaciones que no se puedan copiar, y el rendimiento pasado de un gestor no asegura el futuro. No controlamos las decisiones del gestor de la estrategia.",
             "Comisión de rendimiento: la estrategia define un porcentaje que se aplica solo a la ganancia nueva de tu copia (sobre la marca de agua anterior, así no se cobra dos veces lo mismo). Se liquida cada cierto número de días y "
             "al detener la copia, y se paga con tu billetera virtual. Si no tienes saldo, la comisión queda pendiente y la copia se pausa hasta que se pueda cobrar.",
             "Pausar una copia detiene las nuevas operaciones; las posiciones ya abiertas siguen abiertas y las gestionas tú.",
             "Detener una copia: al detenerla eliges si el sistema cierra también las posiciones que esa copia tiene abiertas o si las deja abiertas. Si eliges cerrarlas y alguna no se puede cerrar (por ejemplo, "
             "por una falla del bróker o porque el mercado está cerrado), la copia queda «con cierre pendiente», se reintenta y se te avisa; mientras tanto esa posición sigue expuesta al mercado y debes cerrarla tú en tu cuenta si no se cierra sola.",
             "Los límites que fijes (take profit y stop loss de la copia, importe) ayudan a acotar el riesgo, pero no lo eliminan."],
        ]),
        ("8. Uso permitido", [
            ["No uses la plataforma para fines ilegales ni para operar en nombre de otras personas sin su autorización.",
             "No intentes acceder a cuentas ni a datos de otros usuarios, ni sobrecargar o vulnerar el servicio.",
             "No copies ni revendas la plataforma, su diseño ni su código."],
        ]),
        ("9. Planes y pagos", [
            "Hoy no se cobra por el uso de la plataforma. Si en el futuro hubiera planes de pago, se informarán sus precios y condiciones antes de cobrar cualquier monto.",
        ]),
        ("10. Disponibilidad y datos de terceros", [
            "No garantizamos que la plataforma funcione sin interrupciones. Los precios, noticias y demás datos vienen de terceros (el bróker, Yahoo Finance, Investing.com y otros) "
            "y pueden tener retraso, errores o no estar disponibles.",
        ]),
        ("11. Limitación de responsabilidad", [
            "En la medida que la ley lo permita, no respondemos por pérdidas de dinero ni por daños derivados de operaciones, de decisiones que tomes con la información de la "
            "plataforma, de fallas de internet o de terceros, ni de interrupciones del servicio. Operar es una decisión y un riesgo tuyos.",
        ]),
        ("12. Propiedad intelectual", [
            f"La plataforma, su diseño, textos y código pertenecen a {EMPRESA} Tus datos siguen siendo tuyos.",
        ]),
        ("13. Cambios y ley aplicable", [
            "Podemos actualizar estos términos; la versión vigente y su fecha se muestran siempre en esta página, y te pediremos aceptarlos de nuevo si el cambio es importante. "
            "Se rigen por las leyes de Chile.",
        ]),
    ],
}


PRIVACIDAD = {
    "titulo": "Privacidad y cookies",
    "resumen": "Qué datos guardamos, para qué, con quién los compartimos y qué cookies usa la plataforma.",
    "secciones": [
        ("1. Responsable", [
            f"El responsable del tratamiento de tus datos es {EMPRESA}, RUT {RUT}, {DIRECCION}. Contacto: {CORREO}.",
        ]),
        ("2. Qué datos guardamos", [
            ["Cuenta y registro (obligatorios): tus nombres y apellidos, tu fecha de nacimiento (para comprobar que eres mayor de edad), tu correo y un resumen irreversible (hash) de tu contraseña; nunca la contraseña misma. "
             "Si entras con Google, recibimos de Google tu nombre y tu correo verificado.",
             "Verificación y recuperación: enlaces de un solo uso, de los que guardamos solo su hash.",
             "Perfil (opcional): datos adicionales de contacto y de inversor que decidas completar en «Mi perfil».",
             "Conexión con el bróker: el correo, la clave y la contraseña de la API de tu cuenta, guardados cifrados.",
             "Actividad: órdenes, posiciones, historial y diario de operaciones, límites de riesgo, favoritos y listas de activos.",
             "Conversaciones con el agente y las propuestas de órdenes que genera.",
             "Sesiones abiertas: un identificador aleatorio (guardamos solo su hash), el resumen del navegador y las fechas de uso.",
             "Aceptaciones legales: qué documentos aceptaste, en qué versión y cuándo, para acreditar tu consentimiento.",
             "Copy trading y billetera virtual: tus copias, su resultado, las comisiones y los movimientos de tu saldo virtual.",
             "Registros técnicos: el servidor y el proveedor de hosting registran datos como la dirección IP y la hora de cada visita, por seguridad y funcionamiento."],
        ]),
        ("3. Para qué los usamos", [
            ["Darte acceso a la plataforma y ejecutar lo que pides o confirmas.",
             "Enviarte correos del servicio: confirmación de correo y recuperación de contraseña.",
             "Cuidar la seguridad del servicio y resolver fallas.",
             "Mejorar la plataforma, por ejemplo midiendo su rendimiento. No usamos tus datos para publicidad ni los vendemos."],
        ]),
        ("4. Con quién los compartimos", [
            ["Tu bróker (hoy, Capital.com): recibe las órdenes y consultas que se hacen con las credenciales de tu cuenta.",
             "DeepSeek, proveedor del modelo de inteligencia artificial: recibe los mensajes que escribes al agente y los datos de mercado y de tu cuenta que el agente consulta "
             "para responderte. Es un proveedor externo, que puede procesar la información fuera de Chile.",
             "El proveedor de hosting y de correo de la empresa, que aloja la plataforma, la base de datos y envía los correos.",
             "Google: el control anti-bots (reCAPTCHA) en el registro, el inicio de sesión y otros formularios recibe la dirección IP y datos del navegador para distinguir personas de programas; y, si eliges entrar con Google, "
             "Google identifica tu sesión con su servicio.",
             "Fuentes de datos de mercado (Yahoo Finance, Investing.com, entre otras): reciben consultas de instrumentos, no tus datos personales.",
             "Otros usuarios: si publicas una estrategia de copy trading, quienes la copian ven su nombre, su descripción y su rendimiento."],
            "Transferencias fuera de Chile: DeepSeek, Google, tu bróker y los proveedores de datos pueden tratar información en otros países, con las condiciones de privacidad de cada uno. "
            "No vendemos tus datos ni los usamos para publicidad.",
            "Fuera de esos casos solo entregaremos tus datos si una autoridad competente lo exige conforme a la ley.",
        ]),
        ("5. Cookies y datos en tu navegador", [
            "La plataforma usa solo lo necesario para funcionar. No usa cookies de publicidad ni de seguimiento de terceros, y desactivamos la telemetría de uso del programa con que está hecha.",
            ["Cookie «pj_sesion» (propia, necesaria): mantiene tu sesión abierta hasta 30 días, aunque cierres el navegador, y en hasta 5 dispositivos a la vez. Contiene un identificador "
             "aleatorio. Se borra al cerrar sesión; también puedes borrarla desde tu navegador.",
             "Identificador de sesión en la dirección (parámetro «s»): identifica la pestaña abierta. No compartas ni publiques enlaces de la plataforma que lo contengan.",
             "Preferencias de la interfaz: el navegador puede guardar ajustes como el tema o la disposición de los paneles."],
        ]),
        ("6. Cuánto tiempo los guardamos", [
            ["Cuenta, perfil, actividad, conversaciones con el agente y copias: mientras tu cuenta esté activa.",
             "Sesiones abiertas (cookie «pj_sesion»): hasta 30 días desde su último uso; al cerrar sesión se borran. Los enlaces de verificación y de recuperación de contraseña son de un solo uso y vencen.",
             "Registros técnicos del servidor: el tiempo que el proveedor de hosting los conserve para seguridad y funcionamiento.",
             "Aceptaciones legales: se conservan para acreditar tu consentimiento aunque cambies de versión."],
            "Si quieres que eliminemos tu cuenta y tus datos, escríbenos "
            f"a {CORREO}: borramos lo que no debamos conservar por ley o para acreditar tus aceptaciones y las operaciones con el bróker que requieran respaldo.",
        ]),
        ("7. Seguridad", [
            "Las contraseñas se guardan con un hash irreversible y las claves de tu bróker, cifradas. Aun así, ninguna medida es absoluta: elige una contraseña fuerte, "
            "no la repitas en otros sitios y cierra sesión en los equipos que no sean tuyos.",
        ]),
        ("8. Tus derechos", [
            f"Puedes pedirnos acceder a tus datos, corregirlos, eliminarlos, bloquearlos u oponerte a su tratamiento, conforme a la legislación chilena de protección de datos personales, escribiendo a {CORREO}. "
            "Respondemos por ese mismo medio. Si no estás conforme con la respuesta, puedes acudir a la autoridad que corresponda.",
        ]),
        ("9. Cambios", [
            "Si cambiamos esta política, publicaremos aquí la nueva versión con su fecha.",
        ]),
    ],
}


RIESGO = {
    "titulo": "Aviso de riesgo",
    "resumen": "Operar con CFD tiene un alto riesgo de pérdida; la plataforma y su agente no son asesoría financiera.",
    "secciones": [
        ("1. Riesgo de pérdida", [
            ["Operar con derivados como los CFD y con apalancamiento conlleva un alto riesgo de perder dinero con rapidez. Puedes perder parte o todo el capital que uses.",
             "No es adecuado para todas las personas. Opera solo con dinero que puedas permitirte perder y entiende cómo funciona cada producto antes de usarlo."],
        ]),
        ("2. La plataforma no es asesoría financiera", [
            "La información, los gráficos, los análisis y las respuestas del agente son herramientas de apoyo, de carácter informativo. No consideran tu situación financiera ni tus "
            "objetivos, y no constituyen asesoría ni una recomendación de comprar o vender. La decisión de operar es siempre tuya. Si tienes dudas, consulta a un asesor autorizado.",
        ]),
        ("3. El agente de inteligencia artificial puede equivocarse", [
            "El agente puede dar información incorrecta, incompleta o desactualizada. Verifica los datos y revisa con cuidado cada orden que te proponga antes de confirmarla. "
            "Si autorizas una vigilancia automática, el agente abre y cierra posiciones por su cuenta sin pedirte confirmación en cada orden: puede equivocarse, operar en un mal momento "
            "o fallar por problemas técnicos, y las pérdidas son tuyas. Revisa sus operaciones y detenla si no se comporta como esperas.",
        ]),
        ("4. Riesgos propios de cada forma de operar", [
            ["Manual: antes de confirmar revisa instrumento, lado, volumen, Stop Loss y Take Profit.",
             "One-Click Trading: la orden sale al instante y sin confirmación; un clic o un arrastre por error envía una operación y, una vez enviada, se ejecuta según el mercado.",
             "Copy trading: replica a otro gestor sin que tú decidas cada operación; puede tener retrasos, diferencias de precio, operaciones no copiadas y comisión de rendimiento sobre tus ganancias. Al detenerla, las posiciones abiertas pueden quedar abiertas o con cierre pendiente.",
             "Vigilancia automática: opera sin pedirte confirmación en cada orden y dentro de los límites que definiste."],
        ]),
        ("5. Riesgo de mercado y fallas del servicio", [
            "Son dos riesgos distintos. El riesgo de mercado es el de perder por el movimiento de los precios. El riesgo de falla del servicio es el de que la plataforma, tu conexión, el bróker o un proveedor fallen: "
            "una orden puede no enviarse, enviarse tarde o con un resultado incierto, una posición puede no cerrarse a tiempo, o un dato puede llegar con retraso. Revisa tu cuenta en el bróker ante cualquier duda.",
        ]),
        ("6. Cuenta demo y cuenta real", [
            ("Si operas en una cuenta real, las órdenes que se ejecuten, tanto las que confirmes como las de una copia que hayas activado, usan tu dinero y las pérdidas son reales."
             if REAL_HABILITADO else
             "Hoy la plataforma opera solo con cuenta demo: ni las órdenes, ni las vigilancias, ni las copias usan dinero real. Si se habilitara la cuenta real, se avisará antes y las pérdidas serían reales."),
            "El resultado en una cuenta demo no garantiza el mismo resultado en una cuenta real: en la realidad influyen el deslizamiento de precios, la liquidez y la velocidad de ejecución. "
            "Los resultados pasados no aseguran resultados futuros.",
        ]),
        ("7. Límites de las protecciones", [
            "Un stop loss no garantiza que la orden se cierre al precio indicado: en mercados con saltos o poca liquidez puede ejecutarse a un precio peor. "
            "Los límites de riesgo de la plataforma ayudan a controlar el riesgo, pero no lo eliminan.",
        ]),
        ("8. Datos de terceros", [
            "Los precios y las noticias vienen de terceros y pueden tener retraso o errores. Antes de operar, comprueba el precio en tu bróker.",
        ]),
    ],
}


# Documentos por la clave que se usa en la dirección (?legal=terminos|privacidad|riesgo).
DOCUMENTOS = {"terminos": TERMINOS, "privacidad": PRIVACIDAD, "riesgo": RIESGO}


# -------------------------------------------------------------------------------------------------------
# ----------------------------------- FIN Piña y Jara contenido .PY -------------------------------------
# -------------------------------------------------------------------------------------------------------

# Sitio Web Creado por Piña y Jara Transportes y Servicios Ltda.
# Dirección: José Joaquín Prieto #5373 -
# San Miguel - Santiago - Chile
# contacto.pinayjara@gmail.com
# https://www.pinayjara.cl
# Creado, Programado y Diseñado por Piña y Jara
# Transportes y Servicios Ltda.
