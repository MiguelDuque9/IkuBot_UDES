# IkuBot UDES

Asistente virtual con Streamlit y registro de analíticas en Google Sheets.

## Cambios recientes

- Se ajustó el registro en `AnalyticasIKUBOT` para guardar todas las consultas del usuario mientras:
  - El consentimiento de datos ya fue aceptado y el perfil básico está completado.
  - El flujo de conversación está en estado `NORMAL` (no en creación/confirmación de incidencias).
  - No se trate de mensajes que disparen el flujo de incidencias (palabras clave base y extendidas).
- Se agregó reintento con backoff exponencial al método `log_interaction` para reducir fallos intermitentes de la API de Google.

## Exclusiones del registro

No se registran en `AnalyticasIKUBOT`:
- Mensajes del protocolo de consentimiento/tratamiento de datos (antes de aceptar y durante la recolección de perfil).
- Mensajes del flujo de incidencias (`COLLECTING` y `CONFIRMING`).
- Mensajes que detonan el flujo de incidencias (palabras clave base y extendidas).

## Ejecutar la app

Requisitos: Python 3.10+, dependencias del archivo `requirements.txt` y variables/credenciales en `config.py`.

```powershell
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar app
streamlit run app.py
```

## Verificación rápida

1. Inicie la app y acepte el consentimiento.
2. Complete nombre, tipo de usuario y contacto.
3. En el chat, envíe 3-4 preguntas normales (no incidentes) y verifique que todas se registren en la hoja `AnalyticasIKUBOT`.
4. Escriba un texto que dispare una incidencia (p. ej. "tengo un problema"), avance un paso y confirme que esos mensajes no se registran.
5. Tras volver a `NORMAL`, envíe otra consulta y verifique que se registre nuevamente.

## Notas

- El ID de hoja se toma de `config.GOOGLE_SHEET_ID` y las credenciales del servicio de `config.GOOGLE_CREDENTIALS`.
- En caso de errores intermitentes con Google Sheets, el sistema reintenta hasta 3 veces con backoff exponencial.
