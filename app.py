import streamlit as st
from google_sheets import GoogleSheetsHandler
from knowledge import UDES_KEYWORDS, INCIDENT_KEYWORDS, get_system_prompt
from datetime import datetime
import re
import hashlib
from utils.api_handler import DeepSeekAPIHandler
from config import GOOGLE_SHEET_ID
import os
import unicodedata

st.set_page_config(
    page_title="IkúBOT - Universidad UDES",
    page_icon="assets/escudo.png",
    layout="centered"
)

@st.cache_resource
def init_handlers(version: str = "v1"):
    return {
        "gsheets": GoogleSheetsHandler(),
        "deepseek": DeepSeekAPIHandler()
    }

## Versión de los handlers para control de caché
HANDLERS_VERSION = "users-v1"
handlers = init_handlers(HANDLERS_VERSION)
SHEET_NAME = "IncidenciasIKUBOT"
USERS_SHEET_NAME = "UsuariosIKUBOT"

## Mensaje formal de consentimiento para tratamiento de datos personales
CONSENT_MESSAGE = (
    "¡Hola! Soy IkúBot, tu asistente virtual de la UDES. Estoy aquí para ayudarte con tus consultas académicas y administrativas.\n\n"
    "Para dar cumplimiento de lo establecido en la Ley 1581 de 2012 y su Decreto Reglamentario 1377 de 2013, sobre la Protección de Datos Personales, "
    "la Universidad de Santander - UDES informa que los datos personales que usted nos proporcione serán incorporados en una base de datos de la cual la UDES es responsable, "
    "con el fin de mantener, desarrollar y gestionar los servicios que ofrecemos.\n\n"
    "Nuestra política de tratamiento de datos personales se encuentra disponible en el sitio web oficial: www.udes.edu.co.\n\n"
    "Para poder continuar con su solicitud, requerimos su consentimiento expreso para el tratamiento de sus datos personales. "
    "Si no está de acuerdo, puede enviarnos sus observaciones o inquietudes al correo electrónico: habeasdata@udes.edu.co.\n\n"
    "¿Acepta nuestra política de protección de datos personales?\n"
    "(Por favor responda únicamente con: Si o No)."
)

# Conjunto ampliado de disparadores para iniciar el flujo de incidencias
INCIDENT_EXTRA_TRIGGERS = (
    "abrir un ticket", "abrir ticket", "reporte un problema", "reportar problema", "tengo un problema",
    "soporte", "ayuda con un error", "fallo", "error en", "no funciona", "no me deja", "presento un inconveniente",
    "crear caso", "crear un caso", "levantar caso", "generar caso", "generar reporte", "reportar incidencia",
    "incidente", "inconveniente"
)

## Elimina etiquetas de procesamiento y espacios innecesarios en la respuesta
def clean_response(response):
    """Limpia etiquetas de thinking y espacios extra"""
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()

## Verifica si la consulta está relacionada con la Universidad UDES
def is_valid_udes_query(user_input):
    """Verifica si la consulta está relacionada con la universidad"""
    return any(keyword in user_input.lower() for keyword in UDES_KEYWORDS)

def _lower_no_accents(text: str) -> str:
    """Convierte a minúsculas y elimina acentos para comparaciones robustas."""
    nfkd = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in nfkd if unicodedata.category(ch) != 'Mn').lower()

def _normalize_for_match(text: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin acentos y espacios únicos."""
    t = _lower_no_accents(text or "")
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t

def _is_affirmative(text: str) -> bool:
    """Detecta confirmaciones tipo 'sí' tolerantes a acentos, mayúsculas y signos.
    Acepta variantes comunes: si/sí, yes, ok, vale, correcto, confirmo, claro.
    """
    t = _normalize_for_match(text)
    # Coincide si inicia con alguna palabra afirmativa, permitiendo puntuación luego
    return re.match(r"^(si|yes|ok|vale|correcto|confirmo|claro)(\b|[^a-z0-9])", t) is not None

def _is_negative(text: str) -> bool:
    """Detecta negaciones/cancelaciones tolerantes a acentos y signos."""
    t = _normalize_for_match(text)
    return re.match(r"^(no|nop|nope|incorrecto|corregir|cancelar|cancel|salir)(\b|[^a-z0-9])", t) is not None

## Genera la respuesta del asistente virtual usando la API
def get_ai_response(user_input):
    try:
        # Obtiene dinámicamente el prompt de sistema (base de conocimiento desde Google Doc)
        system_prompt = get_system_prompt()
        response = handlers["deepseek"].generate_response(system_prompt, user_input)
        
        if not response:
            return "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde."
            
        cleaned_response = clean_response(response)
        
        if not cleaned_response or len(cleaned_response.strip()) < 10:
            return "Lo siento, no pude procesar tu consulta correctamente. ¿Podrías reformular tu pregunta?"
        
        return cleaned_response
        
    except Exception as e:
        st.error(f"Error al conectar con el modelo: {e}")
        return "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde o genera una incidencia."

## Valida el formato de correo electrónico
def validate_email(email):
    """Valida formato de email"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

## Gestiona el flujo de creación y registro de incidencias
def handle_incident_flow(user_input):
    """Maneja el flujo de creación de incidencias"""
    
    # Cancelar protocolo en cualquier fase si el usuario lo indica
    user_l = user_input.strip().lower()
    if _is_negative(user_l) and st.session_state.conversation_flow in {"COLLECTING", "CONFIRMING"}:
        st.session_state.conversation_flow = "NORMAL"
        st.session_state.incident_data = {}
        return "Se ha cancelado la generación de incidencia. Hay algo mas en lo que te pueda asistir?."

    if st.session_state.conversation_flow == "NORMAL":
        # Detección robusta de intención de incidencia (acentos y variantes)
        text_cmp = _lower_no_accents(user_input)
        base_hit = any(trigger in text_cmp for trigger in [_lower_no_accents(k) for k in INCIDENT_KEYWORDS])
        extra_hit = any(_lower_no_accents(p) in text_cmp for p in INCIDENT_EXTRA_TRIGGERS)
        if base_hit or extra_hit:
            st.session_state.conversation_flow = "COLLECTING"
            # Si el usuario ya tiene datos registrados, omitir recolección
            if st.session_state.user_profile.get("completed"):
                contacto = st.session_state.user_profile.get("telefono", "")
                nombre_completo = st.session_state.user_profile.get("nombre", "")
                primer_nombre = st.session_state.user_profile.get("primer_nombre", nombre_completo)
                st.session_state.incident_data = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "step": "descripcion",
                    "nombre": nombre_completo,
                    "correo": contacto,
                    "asunto": "Incidencia desde chat"
                }
                return (
                    f"🎫 **Creación de Incidencia**\n\n"
                    f"{primer_nombre}, ya tengo tus datos de contacto. Por favor describe detalladamente tu **problema o consulta**, si ya no deseas generar la incidencia escribe 'cancelar':"
                )
            else:
                st.session_state.incident_data = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "step": "nombre"
                }
                return """🎫 **Creación de Incidencia**

Para registrar tu incidencia y que nuestro equipo pueda contactarte, necesito algunos datos.

Por favor, ingresa tu **nombre completo**:"""
    
    elif st.session_state.conversation_flow == "COLLECTING":
        return collect_incident_data(user_input)
    
    elif st.session_state.conversation_flow == "CONFIRMING":
        return confirm_incident_data(user_input)
    
    return None

def collect_incident_data(user_input):
    """Recolecta datos de la incidencia paso a paso"""
    current_step = st.session_state.incident_data.get("step", "nombre")
    
    if current_step == "nombre":
        if len(user_input.strip()) < 3:
            return "Por favor ingresa un nombre válido (mínimo 3 caracteres):"
        
        st.session_state.incident_data["nombre"] = user_input.strip()
        st.session_state.incident_data["step"] = "correo"
        return "Perfecto. Ahora necesito tu **correo electrónico** (preferiblemente institucional @udes.edu.co):"
    
    elif current_step == "correo":
        if not validate_email(user_input.strip()):
            return "Por favor ingresa un correo electrónico válido (ejemplo: usuario@udes.edu.co):"
        
        st.session_state.incident_data["correo"] = user_input.strip()
        st.session_state.incident_data["step"] = "asunto"
        return "Excelente. Ahora describe brevemente el **asunto** de tu consulta o problema:"
    
    elif current_step == "asunto":
        if len(user_input.strip()) < 5:
            return "Por favor proporciona un asunto más descriptivo (mínimo 5 caracteres):"
        
        st.session_state.incident_data["asunto"] = user_input.strip()
        st.session_state.incident_data["step"] = "descripcion"
        return "Finalmente, describe detalladamente tu **problema o consulta**. Incluye toda la información relevante:"
    
    elif current_step == "descripcion":
        if len(user_input.strip()) < 10:
            return "Por favor proporciona una descripción más detallada de tu problema (mínimo 10 caracteres):"
        
        st.session_state.incident_data["descripcion"] = user_input.strip()
        st.session_state.conversation_flow = "CONFIRMING"
        
    return f"""✍️ **Resumen de tu incidencia:**

**📅 Fecha:** {st.session_state.incident_data['fecha']}
**👤 Nombre:** {st.session_state.incident_data['nombre']}
**📧 Contacto:** {st.session_state.incident_data['correo']}
**📋 Asunto:** {st.session_state.incident_data['asunto']}
**📝 Descripción:** {st.session_state.incident_data['descripcion']}

¿Confirmas que esta información es correcta? 
Responde **'Sí'** para registrar la incidencia o **'No'** para corregir los datos."""
    
    return "Error en el flujo de recolección de datos."

def confirm_incident_data(user_input):
    """Confirma y registra la incidencia"""
    user_response = user_input.strip()
    
    if _is_affirmative(user_response):
        try:
            result = handlers["gsheets"].add_incident(
                GOOGLE_SHEET_ID, 
                SHEET_NAME, 
                st.session_state.incident_data
            )
            
            if result:
                # Evita registrar la confirmación de incidencia en Analyticas
                
                st.session_state.conversation_flow = "NORMAL"
                st.session_state.incident_data = {}
                
                st.balloons()
                
                return """✅ **¡Incidencia registrada exitosamente!**

📧 Te contactaremos pronto al correo proporcionado.
🎫 Tu solicitud está siendo procesada por nuestro equipo.

¿Hay algo más en lo que pueda ayudarte?"""
            else:
                return """⚠️ **Error al registrar la incidencia**

Por favor intenta nuevamente en unos minutos. Si el problema persiste, contacta directamente con soporte técnico."""
                
        except Exception as e:
            st.error(f"Error técnico: {str(e)}")
            return f"⚠️ **Error técnico:** {str(e)}\n\nPor favor intenta más tarde."
    
    elif _is_negative(user_response):
        st.session_state.conversation_flow = "COLLECTING"
        st.session_state.incident_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "step": "nombre"
        }
        return (
            "Entendido. Si deseas cancelar por completo, escribe 'cancelar'.\n\n"
            "De lo contrario, vamos a comenzar de nuevo. Por favor, ingresa tu **nombre completo**:"
        )
    elif re.match(r"^(cancelar|cancel|salir)(\b|[^a-z0-9])", _normalize_for_match(user_response)):
        st.session_state.conversation_flow = "NORMAL"
        st.session_state.incident_data = {}
        return "Se ha cancelado la generación de incidencia. ¿Deseas hacer otra consulta?"
    
    else:
        return "Por favor responde **'Sí'** para confirmar o **'No'** para corregir los datos."

## Inicializa el estado de la sesión para el chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]

if "incident_data" not in st.session_state:
    st.session_state.incident_data = {}

if "conversation_flow" not in st.session_state:
    st.session_state.conversation_flow = "NORMAL"

## Estado del consentimiento del usuario (PENDING, ACCEPTED, DECLINED)
if "consent_status" not in st.session_state:
    st.session_state.consent_status = "PENDING"

## Perfil básico del usuario tras aceptar el consentimiento
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "completed": False,
    "step": None,  # Secuencia: nombre -> tipo_usuario -> telefono
        "nombre": "",
        "tipo_usuario": "",
        "telefono": ""
    }

## Mensaje inicial que solicita autorización de tratamiento de datos
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": CONSENT_MESSAGE
    })

## Construcción de la interfaz principal de usuario
col1, col2 = st.columns([1, 8])
with col1:
    st.image("assets/escudo.png", width=80)  # Muestra el escudo institucional
with col2:
    st.title("IkúBot")
st.caption("Asistente virtual - Oficina de atención al estudiante - UDES")

## Muestra el estado actual del flujo de conversación
if st.session_state.conversation_flow != "NORMAL":
    st.info(f"📝 Creando incidencia - Paso: {st.session_state.incident_data.get('step', 'confirmación')}")

## Presenta el historial de mensajes en el chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

## Entrada de mensajes por parte del usuario
if prompt := st.chat_input("Escribe tu mensaje..."):
    if prompt.strip():
        # Controla el consentimiento antes de procesar cualquier acción
        user_clean = prompt.strip().lower()
        # Normaliza el texto (corrige ortografía) sin alterar intención, para mejorar detección
        try:
            normalized = handlers["deepseek"].normalize_text(prompt) or prompt
        except Exception:
            normalized = prompt
        normalized_l = normalized.lower()

        if st.session_state.consent_status != "ACCEPTED":
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if user_clean in ["si", "sí", "si.", "sí.", "yes"]:
                    st.session_state.consent_status = "ACCEPTED"
                    # Inicia el flujo de recolección de perfil de usuario
                    st.session_state.user_profile.update({
                        "completed": False,
                        "step": "nombre",
                        "nombre": "",
                        "tipo_usuario": "",
                        "telefono": ""
                    })
                    welcome = (
                        "Gracias por aceptar nuestra política de protección de datos personales.\n\n"
                        "Para brindarte una atención más personalizada, primero necesito algunos datos.\n\n"
                        "Por favor, indícame tu nombre completo:"
                    )
                    st.markdown(welcome)
                    st.session_state.messages.append({"role": "assistant", "content": welcome})
                elif user_clean in ["no", "no.", "nop", "nope"]:
                    st.session_state.consent_status = "DECLINED"
                    decline_msg = (
                        "Entendido. Sin su autorización no podemos continuar con la atención por este medio.\n\n"
                        "Puede comunicarse directamente con la Oficina de Atención al Estudiante para recibir asistencia:\n\n"
                        "• Correo: sec.atencionestudiante@udes.edu.co\n"
                        "• Teléfono: (607) 651 6500\n\n"
                        "Si cambia de opinión, puede escribir 'Si' para aceptar la política y continuar."
                    )
                    st.markdown(decline_msg)
                    st.session_state.messages.append({"role": "assistant", "content": decline_msg})
                else:
                    ask_again = "Por favor responde únicamente con: 'Si' o 'No' para continuar."
                    st.markdown(ask_again)
                    st.session_state.messages.append({"role": "assistant", "content": ask_again})
        else:
            # Prepara los datos para registro en Analyticas tras generar la respuesta
            prompt_l = normalized_l
            # Detecta si el mensaje actual intenta iniciar el flujo de incidencias (base + extras)
            incident_bases = [_lower_no_accents(k) for k in INCIDENT_KEYWORDS]
            incident_extras = [_lower_no_accents(k) for k in INCIDENT_EXTRA_TRIGGERS]
            lowered = _lower_no_accents(prompt_l)
            is_incident_trigger = any(trigger in lowered for trigger in incident_bases + incident_extras)
            # Registra TODAS las consultas del usuario en flujo normal, con perfil completo,
            # excluyendo cualquier mensaje que dispare/incurra en el flujo de incidencias.
            # Nota: Quedan excluidos de forma natural los mensajes del protocolo de tratamiento
            # de datos (antes de aceptar y durante la recolección del perfil) y las incidencias.
            should_log_query = (
                st.session_state.conversation_flow == "NORMAL"
                and st.session_state.user_profile.get("completed")
                and not is_incident_trigger
            )
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                # Si el perfil no está completo, solicita los datos antes de continuar
                if st.session_state.consent_status == "ACCEPTED" and not st.session_state.user_profile.get("completed"):
                    step = st.session_state.user_profile.get("step")
                    reply = None

                    if step == "nombre":
                        if len(prompt.strip()) < 3:
                            reply = "Por favor ingresa un nombre válido (mínimo 3 caracteres):"
                        else:
                            st.session_state.user_profile["nombre"] = prompt.strip()
                            # Extrae y guarda el primer nombre para personalización
                            parts = re.split(r"\s+", st.session_state.user_profile["nombre"].strip())
                            st.session_state.user_profile["primer_nombre"] = parts[0] if parts else st.session_state.user_profile["nombre"]
                            st.session_state.user_profile["step"] = "tipo_usuario"
                            reply = (
                                f"Gracias, {st.session_state.user_profile['primer_nombre']}. ¿Eres estudiante UDES o una persona externa? "
                                "Responde con 'estudiante' o 'externo'."
                            )
                    elif step == "tipo_usuario":
                        tipo = prompt.strip().lower()
                        if tipo in ["estudiante", "externo", "estudiante udes", "persona externa"]:
                            st.session_state.user_profile["tipo_usuario"] = "estudiante" if "estudiante" in tipo else "externo"
                            st.session_state.user_profile["step"] = "telefono"
                            reply = "Perfecto. Ahora, por favor comparte un correo electrónico o un número de teléfono/celular de contacto:"
                        else:
                            reply = "Por favor responde únicamente con 'estudiante' o 'externo'."
                    elif step == "telefono":
                        contact = prompt.strip()
                        if validate_email(contact):
                            st.session_state.user_profile["telefono"] = contact
                            valid_contact = True
                        else:
                            phone = re.sub(r"[^0-9+ ]", "", contact)
                            valid_contact = len(re.sub(r"\D", "", phone)) >= 7
                            if valid_contact:
                                st.session_state.user_profile["telefono"] = phone.strip()

                        if not valid_contact:
                            reply = "El contacto parece inválido. Ingresa un correo electrónico válido o un teléfono/celular válido (mínimo 7 dígitos):"
                        else:
                            st.session_state.user_profile["completed"] = True
                            st.session_state.user_profile["step"] = None
                            # Registra el perfil en Google Sheets si el método está disponible
                            gs = handlers.get("gsheets")
                            if not hasattr(gs, "add_user_profile"):
                                # Re-inicializa los handlers si hay caché desactualizado
                                st.cache_resource.clear()
                                handlers.update(init_handlers(HANDLERS_VERSION))
                                gs = handlers.get("gsheets")
                            try:
                                gs.add_user_profile(
                                    GOOGLE_SHEET_ID,
                                    USERS_SHEET_NAME,
                                    {
                                        'session_id': st.session_state.session_id,
                                        'nombre': st.session_state.user_profile['nombre'],
                                        'tipo_usuario': st.session_state.user_profile['tipo_usuario'],
                                        'telefono': st.session_state.user_profile['telefono']
                                    }
                                )
                            except Exception as e:
                                st.warning(f"No se pudo registrar el perfil en Google Sheets: {e}")
                            reply = (
                                f"¡Gracias, {st.session_state.user_profile.get('primer_nombre', st.session_state.user_profile['nombre'])}! Datos registrados.\n\n"
                                "¿En qué puedo asistirte hoy? Si no es posible resolver tu consulta, recuerda que puedes generar una incidencia escribiendo 'incidencia'.\n\n"
                                "Horario de atención (Oficina de Atención al Estudiante):\n"
                                "- Lunes a jueves: 8:00 a.m. – 12:00 m. y 2:00 p.m. – 7:00 p.m.\n"
                                "- Viernes: 8:00 a.m. – 12:00 m. y 2:00 p.m. – 6:00 p.m.\n\n"
                                "Serás contactado por la Oficina de Atención al Estudiante lo antes posible en días hábiles."
                            )

                    if reply is None:
                        reply = "Para continuar, por favor proporciona la información solicitada."
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    # Personaliza las respuestas usando el nombre del usuario si está disponible
                    # Permite cancelación global con texto normalizado
                    incident_response = handle_incident_flow(normalized)
                    
                    if incident_response is not None:
                        personalized = incident_response
                        if st.session_state.user_profile.get("completed") and st.session_state.user_profile.get("nombre"):
                            nombre_corto = st.session_state.user_profile.get("primer_nombre", st.session_state.user_profile["nombre"])
                            personalized = personalized.replace("¿Hay algo más en lo que pueda ayudarte?", f"{nombre_corto}, ¿hay algo más en lo que pueda ayudarte?")
                        st.markdown(personalized)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": personalized
                        })
                    else:
                        with st.spinner("Pensando..."):
                            response = get_ai_response(normalized)
                            if st.session_state.user_profile.get("completed") and st.session_state.user_profile.get("nombre"):
                                nombre_corto = st.session_state.user_profile.get("primer_nombre", st.session_state.user_profile["nombre"])
                                response = f"{nombre_corto}, " + response
                            st.markdown(response)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response
                            })
                            # Registra la interacción en Analyticas solo si la consulta es válida
                            if should_log_query:
                                handlers["gsheets"].log_interaction(
                                    GOOGLE_SHEET_ID,
                                    {
                                        'tipo_interaccion': 'pregunta_respuesta',
                                        'mensaje_usuario': prompt,
                                        'respuesta_bot': response,
                                        'session_id': st.session_state.session_id,
                                    }
                                )

## Barra lateral con información institucional y opciones
with st.sidebar:
    st.image("assets/udeslarge.png", width=350)
    st.header("ℹ️ Información")
    st.write("IkúBot es un asistente virtual inteligente desarrollado para la Oficina de Atención al estudiante de la Universidad de Santander UDES, diseñado para resolver consultas académico-administrativas de manera rápida y precisa")
    
    if st.session_state.conversation_flow != "NORMAL":
        st.write("**Estado actual:** Creando incidencia")
    
    st.markdown("---")
    st.markdown("**Contacto directo:**")
    st.markdown("📧 sec.atencionestudiante@udes.edu.co")
    st.markdown("📞 (607) 651 6500")
    
    # Botón para actualizar únicamente la hoja de métricas (dashboard no se usa)
    if st.button("🔄 Actualizar tablas en Google Sheets"):
        if handlers["gsheets"].update_metrics(GOOGLE_SHEET_ID):
            st.success("Métricas actualizadas correctamente")
        else:
            st.error("Error al actualizar métricas")
