import streamlit as st
from google_sheets import GoogleSheetsHandler
from prompts import BASE_PROMPT, UDES_KEYWORDS, INCIDENT_KEYWORDS
from datetime import datetime
import re
import hashlib
from utils.api_handler import DeepSeekAPIHandler
from config import GOOGLE_SHEET_ID

# Configuración de la página
st.set_page_config(
    page_title="IkúBOT - UDES",
    page_icon="⚙️",
    layout="centered"
)

# Inicializar handlers
@st.cache_resource
def init_handlers():
    return {
        "gsheets": GoogleSheetsHandler(),
        "deepseek": DeepSeekAPIHandler()
    }

handlers = init_handlers()
SHEET_NAME = "IncidenciasIKUBOT"

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
**📧 Correo:** {st.session_state.incident_data['correo']}
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
                handlers["gsheets"].log_interaction(
                    GOOGLE_SHEET_ID,
                    {
                        'tipo_interaccion': 'incidencia_completada',
                        'mensaje_usuario': 'Registro de incidencia confirmado',
                        'respuesta_bot': 'Incidencia registrada exitosamente',
                        'session_id': st.session_state.session_id,
                        'incidencia': 'Sí',
                        'estado': 'Completada'
                    }
                )
                
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

# Mensaje de bienvenida
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "¡Hola! Soy IkuBot, tu asistente virtual de la UDES 🤖. Estoy aquí para ayudarte con tus consultas académicas y administrativas. ¿En qué puedo asistirte hoy? En caso de que no sea posible resolver tu consulta, por favor genera una incidencia para que te contacten y puedan ayudarte con tu solicitud. Para generar una incidencia solo debes responder con la palabra 'incidencia' y seguir el protocolo establecido."
    })

# Interfaz principal
st.title("🤖 IkuBot")
st.caption("Asistente virtual de la Universidad UDES - Powered by DeepSeek API")

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
        if st.session_state.conversation_flow == "NORMAL":
            handlers["gsheets"].log_interaction(
                GOOGLE_SHEET_ID,
                {
                    'tipo_interaccion': 'mensaje_usuario',
                    'mensaje_usuario': prompt,
                    'session_id': st.session_state.session_id,
                    'incidencia': 'No'
                }
            )
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            incident_response = handle_incident_flow(prompt)
            
            if incident_response is not None:
                st.markdown(incident_response)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": incident_response
                })
            else:
                with st.spinner("Pensando..."):
                    response = get_ai_response(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response
                    })
                    
                    if st.session_state.conversation_flow == "NORMAL":
                        handlers["gsheets"].log_interaction(
                            GOOGLE_SHEET_ID,
                            {
                                'tipo_interaccion': 'respuesta_bot',
                                'respuesta_bot': response,
                                'session_id': st.session_state.session_id,
                                'incidencia': 'No'
                            }
                        )

# Sidebar
# Sidebar
with st.sidebar:
    st.header("ℹ️ Información")
    st.write("**Versión:** API DeepSeek")
    st.write("**ID de Sesión:**", st.session_state.session_id)
    
    if st.session_state.conversation_flow != "NORMAL":
        st.write("**Estado actual:** Creando incidencia")
    
    st.markdown("---")
    st.markdown("**Contacto directo:**")
    st.markdown("📧 soporte@udes.edu.co")
    st.markdown("📞 (607) 651 6500")
    
    # Botón para actualizar tablas
    if st.button("🔄 Actualizar tablas en Google Sheets"):
        if handlers["gsheets"].update_dashboard_tables(GOOGLE_SHEET_ID):
            st.success("Tablas actualizadas exitosamente")
        else:
            st.error("Error al actualizar tablas")