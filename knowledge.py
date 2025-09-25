"""Gestión de la base de conocimiento dinámica para IkúBot.

Este módulo reemplaza al antiguo `prompts.py`. La base de conocimiento ya NO se almacena
embebida en el código fuente; ahora se obtiene dinámicamente desde un documento de Google Docs.

Si la descarga del documento falla, se aplica un fallback mínimo para que el bot continúe
operando sin exponer grandes bloques de texto estático.
"""

from __future__ import annotations

import streamlit as st
import requests
from typing import Optional
from config import KNOWLEDGE_DOC_ID

# ID del documento de Google Docs que contiene la base institucional (puede venir de secrets/env)
GOOGLE_DOC_ID = KNOWLEDGE_DOC_ID or "1_jHGJEXtj_20bQGRU4mqNkf_d8dOAqa142d5Wi6hzCw"

# Endpoint export (texto plano) de Google Docs
DOC_EXPORT_URL = f"https://docs.google.com/document/d/{GOOGLE_DOC_ID}/export?format=txt"

# Prompt de resumen de incidencia (mantenido igual que antes)
INCIDENT_PROMPT = """
🎫 **Resumen de tu incidencia:**

**📅 Fecha:** {fecha}
**👤 Nombre:** {nombre}
**📧 Correo:** {correo}
**📋 Asunto:** {asunto}
**📝 Descripción:** {descripcion}

¿Confirmas que esta información es correcta?
Responde 'Sí' para registrar la incidencia o 'No' para corregir los datos.
"""

RESTRICTED_RESPONSE = """
Lo siento, como asistente virtual de la Universidad UDES, solo puedo responder consultas relacionadas con la universidad, sus instalaciones, servicios académicos y trámites administrativos.

Si tienes alguna pregunta sobre ubicaciones, horarios, procesos académicos o servicios de la UDES, con gusto te puedo ayudar.
"""

SYSTEM_CONFIG = {
    "model_instructions": {
        "temperature": 0.1,
        "max_tokens": 500,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    },
    "validation_rules": {
        "force_spanish": True,
        "restrict_domain": True,
        "require_closure": True,
        "validate_keywords": True
    },
    "response_patterns": {
        "valid_query": "informative_response_with_closure",
        "invalid_query": "restricted_response",
        "missing_info": "incident_suggestion_with_closure",
        "incident_request": "incident_creation_process"
    }
}

# Palabras clave de dominio UDES
UDES_KEYWORDS = [
    'universidad', 'udes', 'certificado', 'matrícula', 'matricula', 'inscripción', 'inscripcion',
    'programa', 'carrera', 'horario', 'edificio', 'aula', 'biblioteca', 'registro', 'académico', 'academico',
    'notas', 'génesis', 'genesis', 'descuento', 'beca', 'bienestar', 'trámite', 'tramite',
    'solicitud', 'devolución', 'devolucion', 'congelación', 'congelacion', 'pqrsf', 'homologación', 'homologacion',
    'cupo', 'semestre', 'profesor', 'director', 'coordinador', 'campus', 'bucaramanga', 'cúcuta', 'cucuta',
    'valledupar', 'sede', 'estudiante', 'alumno', 'pregrado', 'posgrado', 'maestría', 'maestria',
    'especialización', 'especializacion', 'doctorado', 'virtual', 'presencial', 'semipresencial'
]

# Palabras clave para disparar flujo de incidencias
INCIDENT_KEYWORDS = [
    'incidencia', 'problema', 'error', 'falla', 'ayuda', 'contacto', 'soporte', 'asistencia',
    'reporte', 'ticket', 'solicitud especial', 'caso', 'consulta personalizada'
]

FALLBACK_KNOWLEDGE = (
    "Información institucional temporal no disponible. Si tu consulta es sobre trámites, devoluciones, "
    "descuentos, matrículas, calendario académico o soporte estudiantil UDES, responde con los detalles "
    "y te ayudaré con lo que tengo disponible. Si no puedo resolverlo, puedo generar una incidencia."
)


@st.cache_data(show_spinner=False, ttl=60 * 30)  # Cache por 30 minutos
def fetch_knowledge_text(doc_url: str = DOC_EXPORT_URL) -> str:
    """Descarga el contenido de conocimiento institucional desde Google Docs.

    Returns:
        str: Texto plano del documento o fallback si falla.
    """
    try:
        resp = requests.get(doc_url, timeout=15)
        if resp.status_code == 200 and resp.text.strip():
            # Limitar tamaño extremo para evitar prompts gigantes (p.ej. > 40k chars)
            text = resp.text.strip()
            if len(text) > 40000:
                text = text[:40000] + "\n...[contenido truncado]"  # Seguridad contra prompts excesivos
            return text
    except Exception:
        pass
    return FALLBACK_KNOWLEDGE


def build_system_prompt(knowledge_text: Optional[str] = None) -> str:
    """Construye el prompt de sistema dinámicamente.

    Inserta reglas, base de conocimiento descargada y aclaraciones operativas.
    """
    if knowledge_text is None:
        knowledge_text = fetch_knowledge_text()

    rules = (
        "Eres 'IkuBot', el asistente virtual oficial de la Universidad de Santander (UDES).\n\n"
        "REGLAS CRÍTICAS:\n"
        "1. Responde SOLO en español.\n"
        "2. Limita tus respuestas a temas institucionales UDES (servicios, trámites, procesos académicos y administrativos).\n"
        "3. Usa únicamente la información de la base de conocimiento proporcionada a continuación. No inventes datos.\n"
        "4. Si la pregunta es relevante pero la información exacta no aparece, sugiere generar una incidencia.\n"
        "5. Si la pregunta NO es de UDES, responde con el mensaje de restricción.\n"
        "6. Tono profesional, amable y conciso. Emojis solo si aportan.\n"
        "7. Finaliza cada respuesta con: '¿Hay algo más en lo que pueda ayudarte? 😊'\n"
    )

    keyword_section = (
        "PALABRAS CLAVE UDES:\n" + ", ".join(UDES_KEYWORDS) + "\n\n"
        "PALABRAS CLAVE INCIDENCIA:\n" + ", ".join(INCIDENT_KEYWORDS) + "\n"
    )

    algo_section = (
        "ALGORITMO DE RESPUESTA:\n"
        "1. Si no hay palabras clave UDES → mensaje de restricción.\n"
        "2. Si hay palabras clave y la info está en conocimiento → responder literal + cierre.\n"
        "3. Si hay palabras clave pero no está la info → sugerir incidencia + cierre.\n"
        "4. Si se detectan palabras clave de incidencia → iniciar flujo de creación de incidencia (NO lo ejecutes tú, solo responde breve si aplica).\n"
    )

    knowledge_section = (
        "BASE DE CONOCIMIENTO (texto dinámico desde Google Docs)\n" + knowledge_text + "\n"
    )

    return rules + "\n" + keyword_section + "\n" + algo_section + "\n" + knowledge_section


def get_system_prompt() -> str:
    """API pública para obtener el prompt completo listo para inyectar en el modelo."""
    return build_system_prompt()

__all__ = [
    "GOOGLE_DOC_ID",
    "INCIDENT_PROMPT",
    "RESTRICTED_RESPONSE",
    "SYSTEM_CONFIG",
    "UDES_KEYWORDS",
    "INCIDENT_KEYWORDS",
    "get_system_prompt",
    "fetch_knowledge_text"
]
