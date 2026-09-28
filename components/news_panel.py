from types import ModuleType
from typing import Optional
import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st

def renderizar_panel_noticias(main: Optional[ModuleType]):
    st.markdown("""
        <div style='background-color: #161b22; padding: 12px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 12px;'>
            <p style='margin:0; font-weight:bold; font-size:20px;'>🤖 Agente Piña y Jara</p>
            <p style='margin:0; font-size:12px; color:#8b949e;'>Modo de Análisis Inteligente</p>
            <hr style='border-color:#30363d; margin:8px 0;'>
            <p style='margin:0; font-size:13px; color:#3fb950; font-weight:bold;'>● Sistema Activo y Sincronizado</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📰 NOTICIAS GLOBALES EN VIVO")
    st.caption("Últimas 5 actualizaciones del mercado en tiempo real")

    @st.dialog("📰 Análisis y Resumen Ampliado del Agente", width="large")
    def mostrar_modal_resumen_noticia(noti):
        st.markdown(f"<h2 style='font-size: 26px; color: #ffffff;'>{noti['title']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 15px;'><b>Fuente oficial:</b> <code>{noti['publisher']}</code></p>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("<h3 style='font-size: 22px; color: #58a6ff;'>📝 Síntesis Financiera</h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 16px; line-height: 1.6;'>{noti['resumen_agente']}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"🔗 **[Explorar noticia completa en la fuente oficial]({noti['link']})**")
        st.markdown("")
        if st.button("Cerrar"):
            st.rerun()

    lista_noticias_en_vivo = []
    
    # Intento 1: Obtener noticias dinámicas mediante RSS financiero global (Yahoo Finance RSS)
    try:
        url_rss = "https://finance.yahoo.com/news/rssindex"
        req = urllib.request.Request(
            url_rss, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')[:5]
            
            for item in items:
                titulo = item.findtext('title') or 'Reporte de Mercado'
                link = item.findtext('link') or '#'
                descripcion = item.findtext('description') or 'Sin descripción adicional.'
                publisher = "Yahoo Finance / Reuters"
                
                # Procesamiento mediante el agente de Piña y Jara
                resumen_agente = ""
                if main is not None and hasattr(main, "chat_agente"):
                    try:
                        prompt_ampliado = (
                            f"Actúa como analista financiero experto. Analiza la siguiente noticia titulada '{titulo}' "
                            f"cuyo contenido es: '{descripcion}'. "
                            "Por favor, redacta un análisis estructurado de un MÁXIMO de 3 párrafos en español profesional."
                        )
                        resp_rapida, _ = main.chat_agente(prompt_ampliado, historial=[{"role": "system", "content": "Eres un analista financiero bilingüe detallado."}])
                        resumen_agente = resp_rapida
                    except Exception:
                        pass

                if not resumen_agente:
                    resumen_agente = str(descripcion or "Sin descripción adicional.")

                lista_noticias_en_vivo.append({
                    "title": titulo,
                    "publisher": publisher,
                    "link": link,
                    "resumen_agente": resumen_agente
                })
    except Exception:
        pass

    # Intento 2 (Fallback robusto): Si el RSS falla, consultamos yfinance directamente
    if len(lista_noticias_en_vivo) < 5:
        try:
            import yfinance as yf  # type: ignore[import-untyped]
            ticker_obj = yf.Ticker("SPY")
            noticias_yf = ticker_obj.news
            if noticias_yf:
                for item in noticias_yf[:5]:
                    if not isinstance(item, dict):
                        continue

                    content_value = item.get('content', item)
                    content_dict = content_value if isinstance(content_value, dict) else item
                    titulo = content_dict.get('title', item.get('title', 'Reporte de Mercado'))
                    publisher = "Bloomberg / Reuters"
                    if 'provider' in content_dict and isinstance(content_dict['provider'], dict):
                        publisher = content_dict['provider'].get('displayName', 'Mercado Financiero')
                    
                    link = "#"
                    if 'clickThroughUrl' in content_dict and isinstance(content_dict['clickThroughUrl'], dict):
                        link = content_dict['clickThroughUrl'].get('url', '#')
                    elif 'link' in item:
                        link = item.get('link', '#')

                    summary = content_dict.get('summary', item.get('summary', 'Sin descripción adicional.'))
                    
                    resumen_agente = summary
                    if main is not None and hasattr(main, "chat_agente"):
                        try:
                            prompt_ampliado = f"Analiza como experto financiero esta noticia: '{titulo}' - '{summary}'. Máximo 3 párrafos en español."
                            resp_rapida, _ = main.chat_agente(prompt_ampliado, historial=[])
                            resumen_agente = resp_rapida
                        except Exception:
                            pass

                    lista_noticias_en_vivo.append({
                        "title": titulo,
                        "publisher": publisher,
                        "link": link,
                        "resumen_agente": resumen_agente
                    })
        except Exception:
            pass

    # Renderizar las 5 noticias obtenidas dinámicamente en la interfaz
    for i, noti in enumerate(lista_noticias_en_vivo[:5]):
        st.markdown(f"""
            <div style='background-color: #161b22; padding: 12px 14px; border-radius: 6px; border: 1px solid #30363d; margin-bottom: 8px;'>
                <p style='font-weight: 600; font-size: 13px; color: #ffffff; margin-bottom: 6px;'>{noti['title']}</p>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span style='font-size: 11px; color: #8b949e;'>{noti['publisher']}</span>
                    <a href='{noti['link']}' target='_blank' style='font-size: 12px; color: #58a6ff; text-decoration: none; font-weight: bold;'>Ver fuente ↗</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"📖 Ver resumen #{i+1}", key=f"btn_resumen_link_{i}", use_container_width=True):
            mostrar_modal_resumen_noticia(noti)