import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import traceback
import time
from datetime import datetime
import pandas as pd
from config import GOOGLE_CREDENTIALS

class GoogleSheetsHandler:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        try:
            self.credentials = Credentials.from_service_account_info(
                GOOGLE_CREDENTIALS, 
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.credentials)
            print("✅ Conexión a Google Sheets establecida correctamente")
        except Exception as e:
            print(f"❌ Error al inicializar Google Sheets: {e}")
            raise
            

    def _refresh_credentials(self):
        """Refresca las credenciales si están expiradas"""
        try:
            if self.credentials.expired:
                self.credentials.refresh(Request())
                self.client = gspread.authorize(self.credentials)
                print("🔄 Credenciales refrescadas")
        except Exception as e:
            print(f"⚠️ Error al refrescar credenciales: {e}")
            raise

    def _create_analytics_sheet(self, sheet_id):
        """Crea la hoja de analytics si no existe"""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet("AnalyticasIKUBOT")
                print("✅ Hoja AnalyticasIKUBOT ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title="AnalyticasIKUBOT",
                    rows=1000,
                    cols=10
                )
                
                # Encabezados
                headers = [
                    "Timestamp", "Fecha", "Hora", "Tipo_Interaccion",
                    "Mensaje_Usuario", "Respuesta_Bot", "Session_ID", 
                    "Longitud_Mensaje", "Incidencia", "Estado"
                ]
                worksheet.append_row(headers)
                
                # Formato de encabezados
                worksheet.format('A1:J1', {
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                
                print("✅ Hoja AnalyticasIKUBOT creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"❌ Error al crear hoja AnalyticasIKUBOT: {e}")
            raise

    def _create_dashboard_sheet(self, sheet_id):
        """Crea la hoja de dashboard si no existe"""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet("DashboardIKUBOT")
                print("✅ Hoja DashboardIKUBOT ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title="DashboardIKUBOT",
                    rows=50,
                    cols=20
                )
                
                # Título del dashboard
                worksheet.update('A1', [['Dashboard de Analíticas IkuBot']])
                worksheet.format('A1', {
                    'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.7},
                    'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                worksheet.merge_cells('A1:T1')
                
                print("✅ Hoja DashboardIKUBOT creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"❌ Error al crear hoja DashboardIKUBOT: {e}")
            raise

    def update_dashboard_tables(self, sheet_id):
        """Actualiza las tablas de información en la hoja DashboardIKUBOT"""
        try:
            self._refresh_credentials()
            
            # Obtener datos de analytics
            analytics_sheet = self._create_analytics_sheet(sheet_id)
            dashboard_sheet = self._create_dashboard_sheet(sheet_id)
            
            # Obtener datos
            analytics_data = analytics_sheet.get_all_values()
            if len(analytics_data) <= 1:
                print("⚠️ No hay suficientes datos para actualizar tablas")
                return False
            
            # Limpiar dashboard antes de crear nuevas tablas
            dashboard_sheet.clear()
            
            # Título del dashboard
            dashboard_sheet.update('A1', [[
                'Dashboard de Analíticas IkuBot - Actualizado: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]])

            dashboard_sheet.format('A1', {
                'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.7},
                'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            dashboard_sheet.merge_cells('A1:T1')
            
            # Crear tablas de datos
            self._create_daily_interactions_table(analytics_data, dashboard_sheet)
            self._create_interaction_types_table(analytics_data, dashboard_sheet)
            self._create_hourly_distribution_table(analytics_data, dashboard_sheet)
            self._create_incidents_vs_normal_table(analytics_data, dashboard_sheet)
            self._create_summary_metrics(analytics_data, dashboard_sheet)
            
            print("✅ Tablas actualizadas exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error al actualizar tablas: {e}")
            traceback.print_exc()
            return False

    def _create_daily_interactions_table(self, data, sheet):
        """Crea tabla de interacciones por día"""
        try:
            # Procesar datos
            daily_counts = {}
            for row in data[1:]:  # Saltar encabezados
                if len(row) >= 2:
                    date = row[1]  # Columna Fecha
                    daily_counts[date] = daily_counts.get(date, 0) + 1
            
            # Escribir tabla
            sheet.update('A3', [['Interacciones por Día']])
            sheet.format('A3', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('A4', [['Fecha', 'Interacciones']])
            sheet.format('A4:B4', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            # Datos
            sorted_dates = sorted(daily_counts.items())
            if sorted_dates:
                values = [[date, count] for date, count in sorted_dates]
                sheet.update('A5', values)
            
        except Exception as e:
            print(f"Error en tabla diaria: {e}")

    def _create_interaction_types_table(self, data, sheet):
        """Crea tabla de tipos de interacción"""
        try:
            # Procesar datos
            type_counts = {}
            for row in data[1:]:  # Saltar encabezados
                if len(row) >= 4:
                    interaction_type = row[3]  # Columna Tipo_Interaccion
                    if interaction_type:
                        type_counts[interaction_type] = type_counts.get(interaction_type, 0) + 1
            
            # Escribir tabla
            sheet.update('D3', [['Tipos de Interacción']])
            sheet.format('D3', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('D4', [['Tipo', 'Cantidad']])
            sheet.format('D4:E4', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            # Datos
            if type_counts:
                values = [[tipo, count] for tipo, count in type_counts.items()]
                sheet.update('D5', values)
            
        except Exception as e:
            print(f"Error en tabla de tipos: {e}")

    def _create_hourly_distribution_table(self, data, sheet):
        """Crea tabla de distribución por horas"""
        try:
            # Procesar datos
            hourly_counts = {}
            for row in data[1:]:  # Saltar encabezados
                if len(row) >= 3:
                    time_str = row[2]  # Columna Hora
                    if time_str and ':' in time_str:
                        hour = time_str.split(':')[0]
                        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            # Escribir tabla
            sheet.update('G3', [['Distribución por Horas']])
            sheet.format('G3', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('G4', [['Hora', 'Interacciones']])
            sheet.format('G4:H4', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            # Datos ordenados por hora
            sorted_hours = sorted(hourly_counts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
            if sorted_hours:
                values = [[f"{hour}:00", count] for hour, count in sorted_hours]
                sheet.update('G5', values)
            
        except Exception as e:
            print(f"Error en tabla horaria: {e}")

    def _create_incidents_vs_normal_table(self, data, sheet):
        """Crea tabla de incidencias vs consultas normales"""
        try:
            # Procesar datos
            incident_counts = {'Incidencia': 0, 'Consulta Normal': 0}
            for row in data[1:]:  # Saltar encabezados
                if len(row) >= 9:
                    is_incident = row[8]  # Columna Incidencia
                    if is_incident == 'Sí':
                        incident_counts['Incidencia'] += 1
                    else:
                        incident_counts['Consulta Normal'] += 1
            
            # Escribir tabla
            sheet.update('J3', [['Incidencias vs Consultas']])
            sheet.format('J3', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('J4', [['Tipo', 'Cantidad']])
            sheet.format('J4:K4', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            # Datos
            values = [['Incidencias', incident_counts['Incidencia']], 
                     ['Consultas Normales', incident_counts['Consulta Normal']]]
            sheet.update('J5', values)
            
        except Exception as e:
            print(f"Error en tabla de incidencias: {e}")

    def _create_summary_metrics(self, data, sheet):
        """Crea métricas de resumen"""
        try:
            total_interactions = len(data) - 1  # Excluir encabezados
            unique_sessions = len(set(row[6] for row in data[1:] if len(row) >= 7 and row[6]))
            
            # Calcular longitud promedio de mensajes
            total_length = 0
            count_with_length = 0
            for row in data[1:]:
                if len(row) >= 8 and row[7] and str(row[7]).isdigit():
                    total_length += int(row[7])
                    count_with_length += 1
            
            avg_length = total_length / count_with_length if count_with_length > 0 else 0
            
            # Escribir métricas
            sheet.update('M3', [['Métricas de Resumen']])
            sheet.format('M3', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            metrics = [
                ['Métrica', 'Valor'],
                ['Total Interacciones', total_interactions],
                ['Sesiones Únicas', unique_sessions],
                ['Longitud Promedio Mensaje', f"{avg_length:.1f} caracteres"],
                ['Interacciones por Sesión', f"{total_interactions/unique_sessions:.1f}" if unique_sessions > 0 else "0"]
            ]
            
            sheet.update('M4', metrics)
            sheet.format('M4:N4', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
        except Exception as e:
            print(f"Error en métricas de resumen: {e}")

    def log_interaction(self, sheet_id, interaction_data):
        """Registra una interacción en AnalyticasIKUBOT"""
        try:
            self._refresh_credentials()
            worksheet = self._create_analytics_sheet(sheet_id)
            
            # Preparar datos
            row_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%H:%M:%S"),
                interaction_data.get('tipo_interaccion', ''),
                interaction_data.get('mensaje_usuario', '')[:300],
                interaction_data.get('respuesta_bot', '')[:300],
                interaction_data.get('session_id', ''),
                len(interaction_data.get('mensaje_usuario', '')),
                interaction_data.get('incidencia', 'No'),
                'Activo'
            ]
            
            worksheet.append_row(row_data)
            return True
        except Exception as e:
            print(f"❌ Error al registrar interacción: {e}")
            traceback.print_exc()
            return False

    def add_incident(self, sheet_id, sheet_name, incident_data):
        """Agrega una incidencia a la hoja"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self._refresh_credentials()
                sheet = self.client.open_by_key(sheet_id).worksheet(sheet_name)
                
                row_data = [
                    incident_data.get('fecha', ''),
                    incident_data.get('nombre', ''),
                    incident_data.get('correo', ''),
                    incident_data.get('asunto', ''),
                    incident_data.get('descripcion', ''),
                    'Pendiente'
                ]
                
                sheet.append_row(row_data)
                return True
                    
            except gspread.exceptions.APIError as e:
                print(f"Error de API (intento {retry_count+1}): {e}")
                time.sleep(2 ** retry_count)
                retry_count += 1
            except Exception as e:
                print(f"Error inesperado: {e}")
                traceback.print_exc()
                retry_count += 1
                time.sleep(2 ** retry_count)
        
        print("❌ Fallo después de múltiples intentos")
        return False

    def test_connection(self, sheet_id, sheet_name):
        """Prueba la conexión con Google Sheets"""
        try:
            self._refresh_credentials()
            sheet = self.client.open_by_key(sheet_id).worksheet(sheet_name)
            rows = sheet.get_all_values()
            return f"✅ Conexión exitosa. Filas: {len(rows)}"
        except Exception as e:
            return f"❌ Error de conexión: {str(e)}"

    def get_incident_stats(self, sheet_id, sheet_name):
        """Obtiene estadísticas de incidencias"""
        try:
            self._refresh_credentials()
            sheet = self.client.open_by_key(sheet_id).worksheet(sheet_name)
            records = sheet.get_all_records()
            
            stats = {
                'total': len(records),
                'pendientes': sum(1 for r in records if r.get('Estado', '').lower() == 'pendiente'),
                'resueltas': sum(1 for r in records if r.get('Estado', '').lower() == 'resuelta'),
                'success': True
            }
            
            return stats
        except Exception as e:
            print(f"Error al obtener stats: {e}")
            return {
                'total': 0,
                'pendientes': 0,
                'resueltas': 0,
                'success': False,
                'error': str(e)
            }