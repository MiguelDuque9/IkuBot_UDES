import streamlit as st
from google_sheets import GoogleSheetsHandler
from prompts import BASE_PROMPT, UDES_KEYWORDS, INCIDENT_KEYWORDS
from datetime import datetime
import re
import hashlib
from utils.api_handler import DeepSeekAPIHandler
from config import GOOGLE_SHEET_ID
import os

# Configuración de la página
st.set_page_config(
    page_title="IkúBOT - Universidad UDES",
    page_icon="assets/escudo.png",  # Escudo agregado
    layout="centered"
)

# Inicializar handlers
@st.cache_resource
def init_handlers(version: str = "v1"):
    return {
        "gsheets": GoogleSheetsHandler(),
        "deepseek": DeepSeekAPIHandler()
    }

# Cambia HANDLERS_VERSION para forzar refresco del caché cuando cambie la lógica de handlers
HANDLERS_VERSION = "users-v1"
handlers = init_handlers(HANDLERS_VERSION)
SHEET_NAME = "IncidenciasIKUBOT"
USERS_SHEET_NAME = "UsuariosIKUBOT"

# Mensaje de autorización de tratamiento de datos personales (consentimiento)
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

# Función para limpiar respuestas
def clean_response(response):
    """Limpia etiquetas de thinking y espacios extra"""
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()

# Función para verificar si es una consulta válida de UDES
def is_valid_udes_query(user_input):
    """Verifica si la consulta está relacionada con la universidad"""
    return any(keyword in user_input.lower() for keyword in UDES_KEYWORDS)

# Función para generar respuestas con la API
def get_ai_response(user_input):
    try:
        response = handlers["deepseek"].generate_response(BASE_PROMPT, user_input)
        
        if not response:
            return "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde."
            
        cleaned_response = clean_response(response)
        
        if not cleaned_response or len(cleaned_response.strip()) < 10:
            return "Lo siento, no pude procesar tu consulta correctamente. ¿Podrías reformular tu pregunta?"
        
        return cleaned_response
        
    except Exception as e:
        st.error(f"Error al conectar con el modelo: {e}")
        return "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde o genera una incidencia."

# Función para validar email
def validate_email(email):
    """Valida formato de email"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

# Función para manejar incidencias
def handle_incident_flow(user_input):
    """Maneja el flujo de creación de incidencias"""
    
    if st.session_state.conversation_flow == "NORMAL":
        if any(trigger in user_input.lower() for trigger in INCIDENT_KEYWORDS):
            st.session_state.conversation_flow = "COLLECTING"
            # Si ya tenemos datos de usuario, saltar a descripción
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
                    f"{primer_nombre}, ya tengo tus datos de contacto. Por favor describe detalladamente tu **problema o consulta**:"
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
    user_response = user_input.lower().strip()
    
    if user_response in ['sí', 'si', 'yes', 'confirmo', 'correcto', 'ok']:
        try:
            result = handlers["gsheets"].add_incident(
                GOOGLE_SHEET_ID, 
                SHEET_NAME, 
                st.session_state.incident_data
            )
            
            if result:
                # No registrar en Analyticas la confirmación de incidencia
                
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
    
    elif user_response in ['no', 'nope', 'incorrecto', 'corregir']:
        st.session_state.conversation_flow = "COLLECTING"
        st.session_state.incident_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "step": "nombre"
        }
        return "Entendido. Vamos a comenzar de nuevo.\n\nPor favor, ingresa tu **nombre completo**:"
    
    else:
        return "Por favor responde **'Sí'** para confirmar o **'No'** para corregir los datos."

# Estado de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]

if "incident_data" not in st.session_state:
    st.session_state.incident_data = {}

if "conversation_flow" not in st.session_state:
    st.session_state.conversation_flow = "NORMAL"

# Estado de consentimiento (PENDING, ACCEPTED, DECLINED)
if "consent_status" not in st.session_state:
    st.session_state.consent_status = "PENDING"

# Perfil de usuario básico tras consentimiento
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "completed": False,
        "step": None,  # nombre -> tipo_usuario -> telefono
        "nombre": "",
        "tipo_usuario": "",
        "telefono": ""
    }

# Mensaje inicial con autorización de datos
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": CONSENT_MESSAGE
    })

# Interfaz principal
col1, col2 = st.columns([1, 8])
with col1:
    st.image("assets/escudo.png", width=80)  # Mostrar escudo arriba
with col2:
    st.title("IkúBot")
st.caption("Asistente virtual - Oficina de atención al estudiante - UDES")

# Indicador de estado
if st.session_state.conversation_flow != "NORMAL":
    st.info(f"📝 Creando incidencia - Paso: {st.session_state.incident_data.get('step', 'confirmación')}")

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
if prompt := st.chat_input("Escribe tu mensaje..."):
    if prompt.strip():
        # Manejo de consentimiento antes de cualquier otra acción
        user_clean = prompt.strip().lower()

        if st.session_state.consent_status != "ACCEPTED":
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                if user_clean in ["si", "sí", "si.", "sí.", "yes"]:
                    st.session_state.consent_status = "ACCEPTED"
                    # Iniciar flujo de perfil
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
            # Preparar criterio de logging (se registrará luego de generar la respuesta)
            prompt_l = prompt.lower()
            is_incident_trigger = any(trigger in prompt_l for trigger in INCIDENT_KEYWORDS)
            starts_words = ("necesito", "quiero", "busco", "como", "cómo", "cuando", "cuándo", "donde", "dónde", "que", "qué", "información", "info", "ayuda")
            has_udes_keyword = any(k in prompt_l for k in UDES_KEYWORDS)
            is_query_like = ("?" in prompt) or has_udes_keyword or prompt_l.startswith(starts_words)
            should_log_query = (
                st.session_state.conversation_flow == "NORMAL"
                and st.session_state.user_profile.get("completed")
                and is_query_like
                and not is_incident_trigger
            )
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                # Si el perfil no se ha completado, recolectarlo antes de continuar
                if st.session_state.consent_status == "ACCEPTED" and not st.session_state.user_profile.get("completed"):
                    step = st.session_state.user_profile.get("step")
                    reply = None

                    if step == "nombre":
                        if len(prompt.strip()) < 3:
                            reply = "Por favor ingresa un nombre válido (mínimo 3 caracteres):"
                        else:
                            st.session_state.user_profile["nombre"] = prompt.strip()
                            # Guardar primer nombre para personalización
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
                            # Guardar en Google Sheets (asegurar método disponible)
                            gs = handlers.get("gsheets")
                            if not hasattr(gs, "add_user_profile"):
                                # Re-inicializar handlers por si hay caché antiguo
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
                    # Personalizar respuestas usando el nombre si está disponible
                    incident_response = handle_incident_flow(prompt)
                    
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
                            response = get_ai_response(prompt)
                            if st.session_state.user_profile.get("completed") and st.session_state.user_profile.get("nombre"):
                                nombre_corto = st.session_state.user_profile.get("primer_nombre", st.session_state.user_profile["nombre"])
                                response = f"{nombre_corto}, " + response
                            st.markdown(response)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response
                            })
                            # Registrar pregunta y respuesta en Analyticas solo para consultas válidas
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

# Sidebar
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
    
    # Botón para actualizar tablas
    if st.button("🔄 Actualizar tablas en Google Sheets"):
        if handlers["gsheets"].update_dashboard_tables(GOOGLE_SHEET_ID):
            st.success("Tablas actualizadas exitosamente")
        else:
            st.error("Error al actualizar tablas")
