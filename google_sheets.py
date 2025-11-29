import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import traceback
import time
from datetime import datetime, timedelta
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
            print("[OK] Conexión a Google Sheets establecida correctamente")
        except Exception as e:
            print(f"[ERROR] Error al inicializar Google Sheets: {e}")
            raise
            

    def _refresh_credentials(self):
        """Actualiza las credenciales si han expirado para mantener la conexión segura."""
        try:
            if self.credentials.expired:
                self.credentials.refresh(Request())
                self.client = gspread.authorize(self.credentials)
                print("[INFO] Credenciales refrescadas")
        except Exception as e:
            print(f"[WARN] Error al refrescar credenciales: {e}")
            raise

    def _create_analytics_sheet(self, sheet_id):
        """Crea la hoja de AnalyticasIKUBOT si no existe, sin modificar columnas existentes."""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet("AnalyticasIKUBOT")
                print("[OK] Hoja AnalyticasIKUBOT ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title="AnalyticasIKUBOT",
                    rows=1000,
                    cols=7
                )
                
                headers = [
                    "Timestamp", "Fecha", "Hora", "Tipo_Interaccion",
                    "Mensaje_Usuario", "Respuesta_Bot", "Session_ID"
                ]
                worksheet.append_row(headers)
                
                worksheet.format('A1:G1', {
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                
                print("[OK] Hoja AnalyticasIKUBOT creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"[ERROR] Error al crear hoja AnalyticasIKUBOT: {e}")
            raise

    def _create_metrics_sheet(self, sheet_id):
        """Crea la hoja MetricasIKUBOT si no existe."""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet("MetricasIKUBOT")
                print("[OK] Hoja MetricasIKUBOT ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title="MetricasIKUBOT",
                    rows=100,
                    cols=10
                )
                
                # Título principal
                worksheet.update('A1', [['KPIs - IkuBot Analytics']])
                worksheet.format('A1', {
                    'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.7},
                    'textFormat': {'bold': True, 'fontSize': 18, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                worksheet.merge_cells('A1:J1')
                
                print("[OK] Hoja MetricasIKUBOT creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"[ERROR] Error al crear hoja MetricasIKUBOT: {e}")
            raise

    def _create_dashboard_sheet(self, sheet_id):
        """Crea la hoja DashboardIKUBOT si no existe."""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet("DashboardIKUBOT")
                print("[OK] Hoja DashboardIKUBOT ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title="DashboardIKUBOT",
                    rows=50,
                    cols=20
                )
                
                worksheet.update('A1', [['Dashboard de Analíticas IkuBot']])
                worksheet.format('A1', {
                    'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.7},
                    'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                worksheet.merge_cells('A1:T1')
                
                print("[OK] Hoja DashboardIKUBOT creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"[ERROR] Error al crear hoja DashboardIKUBOT: {e}")
            raise

    def _create_users_sheet(self, sheet_id, sheet_name="UsuariosIKUBOT"):
        """Crea la hoja UsuariosIKUBOT si no existe y retorna el worksheet."""
        try:
            spreadsheet = self.client.open_by_key(sheet_id)
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                print(f"[OK] Hoja {sheet_name} ya existe")
                return worksheet
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=10
                )
                headers = [
                    "Timestamp", "Session_ID", "Nombre", "Tipo_Usuario", "Contacto"
                ]
                worksheet.append_row(headers)
                worksheet.format('A1:E1', {
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                })
                print(f"[OK] Hoja {sheet_name} creada exitosamente")
                return worksheet
        except Exception as e:
            print(f"[ERROR] Error al crear hoja {sheet_name}: {e}")
            raise

    def _calculate_kpis(self, analytics_data, users_data, incidents_data):
        """Calcula todos los KPIs necesarios para el dashboard."""
        kpis = {}
        
        # KPIS GENERALES
        kpis['total_interacciones'] = len(analytics_data) - 1  # Excluir encabezado
        kpis['total_usuarios'] = len(users_data) - 1
        kpis['total_incidencias'] = len(incidents_data) - 1
        
        # KPIs de SESIONES
        sessions = set()
        for row in analytics_data[1:]:
            if len(row) >= 7 and row[6]:
                sessions.add(row[6])
        kpis['sesiones_unicas'] = len(sessions)
        kpis['interacciones_por_sesion'] = round(kpis['total_interacciones'] / kpis['sesiones_unicas'], 2) if kpis['sesiones_unicas'] > 0 else 0
        
        # KPIs de TIPOS DE INTERACCIÓN
        tipo_counts = {}
        for row in analytics_data[1:]:
            if len(row) >= 4 and row[3]:
                tipo = row[3].strip()
                tipo_counts[tipo] = tipo_counts.get(tipo, 0) + 1
        
        kpis['incidencias_completadas'] = tipo_counts.get('incidencia_completada', 0)
        kpis['consultas_normales'] = sum(v for k, v in tipo_counts.items() if k != 'incidencia_completada')
        
        # KPIs de INCIDENCIAS
        incidencias_pendientes = 0
        incidencias_resueltas = 0
        for row in incidents_data[1:]:
            if len(row) >= 6:
                estado = row[5].strip().lower()
                if estado == 'pendiente':
                    incidencias_pendientes += 1
                elif estado == 'resuelta':
                    incidencias_resueltas += 1
        
        kpis['incidencias_pendientes'] = incidencias_pendientes
        kpis['incidencias_resueltas'] = incidencias_resueltas
        kpis['tasa_resolucion'] = round((incidencias_resueltas / kpis['total_incidencias'] * 100), 2) if kpis['total_incidencias'] > 0 else 0
        
        # KPIs de TIEMPO (últimos 7 días vs total)
        today = datetime.now()
        last_7_days = today - timedelta(days=7)
        interacciones_7d = 0
        
        for row in analytics_data[1:]:
            if len(row) >= 2 and row[1]:
                try:
                    fecha = datetime.strptime(row[1], "%Y-%m-%d")
                    if fecha >= last_7_days:
                        interacciones_7d += 1
                except:
                    continue
        
        kpis['interacciones_ultimos_7d'] = interacciones_7d
        promedio_diario_7d = round(interacciones_7d / 7, 2)
        kpis['promedio_diario_7d'] = promedio_diario_7d
        
        # KPIs de USUARIOS
        tipos_usuario = {}
        for row in users_data[1:]:
            if len(row) >= 4 and row[3]:
                tipo = row[3].strip()
                tipos_usuario[tipo] = tipos_usuario.get(tipo, 0) + 1
        
        kpis['tipos_usuario'] = tipos_usuario
        
        # KPIs de HORA PICO
        hourly_counts = {}
        for row in analytics_data[1:]:
            if len(row) >= 3 and row[2]:
                try:
                    hora = row[2].split(':')[0]
                    hourly_counts[hora] = hourly_counts.get(hora, 0) + 1
                except:
                    continue
        
        if hourly_counts:
            hora_pico = max(hourly_counts.items(), key=lambda x: x[1])
            kpis['hora_pico'] = f"{hora_pico[0]}:00"
            kpis['interacciones_hora_pico'] = hora_pico[1]
        else:
            kpis['hora_pico'] = "N/A"
            kpis['interacciones_hora_pico'] = 0
        
        # KPI de LONGITUD PROMEDIO DE MENSAJE
        total_length = 0
        count_messages = 0
        for row in analytics_data[1:]:
            if len(row) >= 5 and row[4]:
                total_length += len(row[4])
                count_messages += 1
        
        kpis['longitud_promedio_mensaje'] = round(total_length / count_messages, 0) if count_messages > 0 else 0
        
        return kpis

    def _write_kpis_to_sheet(self, metrics_sheet, kpis):
        """Escribe los KPIs en la hoja MetricasIKUBOT con formato profesional."""
        try:
            # Limpiar la hoja excepto el título
            metrics_sheet.batch_clear(['A3:J100'])
            
            # Actualizar timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metrics_sheet.update('A2', [[f'Última actualización: {timestamp}']])
            metrics_sheet.format('A2', {
                'textFormat': {'italic': True, 'fontSize': 10},
                'horizontalAlignment': 'CENTER'
            })
            metrics_sheet.merge_cells('A2:J2')
            
            current_row = 4
            
            # SECCIÓN 1: KPIs PRINCIPALES
            metrics_sheet.update(f'A{current_row}', [['KPIs PRINCIPALES']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
                'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            metrics_sheet.merge_cells(f'A{current_row}:D{current_row}')
            current_row += 1
            
            # Headers
            metrics_sheet.update(f'A{current_row}', [['KPI', 'Valor', 'Unidad', 'Descripción']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            current_row += 1
            
            # Datos principales
            main_kpis = [
                ['Total Interacciones', kpis['total_interacciones'], 'interacciones', 'Total de interacciones registradas'],
                ['Total Usuarios', kpis['total_usuarios'], 'usuarios', 'Usuarios únicos registrados'],
                ['Sesiones Únicas', kpis['sesiones_unicas'], 'sesiones', 'Sesiones de chat diferentes'],
                ['Interacciones/Sesión', kpis['interacciones_por_sesion'], 'promedio', 'Promedio de mensajes por sesión'],
                ['Total Incidencias', kpis['total_incidencias'], 'incidencias', 'Total de incidencias reportadas'],
            ]
            
            metrics_sheet.update(f'A{current_row}', main_kpis)
            current_row += len(main_kpis) + 2
            
            # SECCIÓN 2: ESTADO DE INCIDENCIAS
            metrics_sheet.update(f'A{current_row}', [['ESTADO DE INCIDENCIAS']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.8, 'green': 0.4, 'blue': 0.2},
                'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            metrics_sheet.merge_cells(f'A{current_row}:D{current_row}')
            current_row += 1
            
            metrics_sheet.update(f'A{current_row}', [['Métrica', 'Valor', 'Porcentaje', 'Estado']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            current_row += 1
            
            incident_kpis = [
                ['Pendientes', kpis['incidencias_pendientes'], f"{round((kpis['incidencias_pendientes']/kpis['total_incidencias']*100) if kpis['total_incidencias'] > 0 else 0, 1)}%", 'Pendiente'],
                ['Resueltas', kpis['incidencias_resueltas'], f"{round((kpis['incidencias_resueltas']/kpis['total_incidencias']*100) if kpis['total_incidencias'] > 0 else 0, 1)}%", 'Resuelta'],
                ['Tasa de Resolución', f"{kpis['tasa_resolucion']}%", '-', 'Seguimiento'],
            ]
            
            metrics_sheet.update(f'A{current_row}', incident_kpis)
            current_row += len(incident_kpis) + 2
            
            # SECCIÓN 3: ACTIVIDAD RECIENTE
            metrics_sheet.update(f'A{current_row}', [['ACTIVIDAD RECIENTE (7 DÍAS)']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.3, 'green': 0.7, 'blue': 0.3},
                'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            metrics_sheet.merge_cells(f'A{current_row}:D{current_row}')
            current_row += 1
            
            metrics_sheet.update(f'A{current_row}', [['Métrica', 'Valor', 'Tipo', 'Tendencia']])
            metrics_sheet.format(f'A{current_row}:D{current_row}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            current_row += 1
            
            activity_kpis = [
                ['Interacciones (7d)', kpis['interacciones_ultimos_7d'], 'total', 'Resumen'],
                ['Promedio Diario (7d)', kpis['promedio_diario_7d'], 'promedio', 'Tendencia'],
                ['Hora Pico', kpis['hora_pico'], 'hora', 'Hora pico'],
                ['Interacciones en Hora Pico', kpis['interacciones_hora_pico'], 'cantidad', 'Volumen'],
            ]
            
            metrics_sheet.update(f'A{current_row}', activity_kpis)
            current_row += len(activity_kpis) + 2
            
            # SECCIÓN 4: TIPOS DE USUARIO
            metrics_sheet.update(f'F{4}', [['DISTRIBUCIÓN DE USUARIOS']])
            metrics_sheet.format(f'F{4}:H{4}', {
                'backgroundColor': {'red': 0.6, 'green': 0.3, 'blue': 0.7},
                'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            metrics_sheet.merge_cells(f'F{4}:H{4}')
            
            metrics_sheet.update(f'F{5}', [['Tipo Usuario', 'Cantidad', 'Porcentaje']])
            metrics_sheet.format(f'F{5}:H{5}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            
            user_type_data = []
            total_users = sum(kpis['tipos_usuario'].values()) if kpis['tipos_usuario'] else 1
            for tipo, count in kpis['tipos_usuario'].items():
                porcentaje = round((count / total_users * 100), 1)
                user_type_data.append([tipo, count, f"{porcentaje}%"])
            
            if user_type_data:
                metrics_sheet.update(f'F{6}', user_type_data)
            
            # SECCIÓN 5: MÉTRICAS DE CALIDAD
            metrics_sheet.update(f'F{12}', [['MÉTRICAS DE CALIDAD']])
            metrics_sheet.format(f'F{12}:H{12}', {
                'backgroundColor': {'red': 0.9, 'green': 0.7, 'blue': 0.2},
                'textFormat': {'bold': True, 'fontSize': 12, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            metrics_sheet.merge_cells(f'F{12}:H{12}')
            
            metrics_sheet.update(f'F{13}', [['Métrica', 'Valor', 'Benchmark']])
            metrics_sheet.format(f'F{13}:H{13}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'bold': True}
            })
            
            quality_kpis = [
                ['Long. Promedio Mensaje', f"{kpis['longitud_promedio_mensaje']} caracteres", '50-200 óptimo'],
                ['Incidencias Completadas', kpis['incidencias_completadas'], '-'],
                ['Consultas Normales', kpis['consultas_normales'], '-'],
            ]
            
            metrics_sheet.update(f'F{14}', quality_kpis)
            
            print("[OK] KPIs escritos exitosamente en MetricasIKUBOT")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error al escribir KPIs: {e}")
            traceback.print_exc()
            return False

    def _get_sheet_data(self, sheet_id):
        """Obtiene y retorna los datos necesarios para calcular los KPIs."""
        try:
            self._refresh_credentials()
            spreadsheet = self.client.open_by_key(sheet_id)

            analytics_sheet = self._create_analytics_sheet(sheet_id)
            analytics_data = analytics_sheet.get_all_values()

            users_sheet = self._create_users_sheet(sheet_id)
            users_data = users_sheet.get_all_values()

            try:
                incidents_sheet = spreadsheet.worksheet("IncidenciasIKUBOT")
                incidents_data = incidents_sheet.get_all_values()
            except:
                incidents_data = [['Fecha', 'Nombre', 'Correo', 'Asunto', 'Descripcion', 'Estado']]

            return analytics_data, users_data, incidents_data

        except Exception as e:
            print(f"[ERROR] Error al obtener los datos de Google Sheets: {e}")
            raise

    def update_metrics_and_dashboard(self, sheet_id):
        """Actualiza la hoja de métricas con KPIs dinámicos y el dashboard."""
        try:
            print("[INFO] Obteniendo datos de las hojas...")
            analytics_data, users_data, incidents_data = self._get_sheet_data(sheet_id)
            
            # Validar que hay datos suficientes
            if len(analytics_data) <= 1:
                print("[WARN] No hay suficientes datos para calcular KPIs")
                return False
            
            # Calcular KPIs
            print("[INFO] Calculando KPIs...")
            kpis = self._calculate_kpis(analytics_data, users_data, incidents_data)
            
            # Escribir KPIs en MetricasIKUBOT
            print("[INFO] Escribiendo KPIs en MetricasIKUBOT...")
            metrics_sheet = self._create_metrics_sheet(sheet_id)
            self._write_kpis_to_sheet(metrics_sheet, kpis)
            
            # Actualizar DashboardIKUBOT
            print("[INFO] Actualizando DashboardIKUBOT...")
            self.update_dashboard_tables(sheet_id, analytics_data, kpis)
            
            print("[OK] Métricas y Dashboard actualizados exitosamente")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error al actualizar métricas: {e}")
            traceback.print_exc()
            return False

    def update_metrics(self, sheet_id):
        """Actualiza únicamente la hoja de métricas sin tocar el dashboard."""
        try:
            print("[INFO] Obteniendo datos de las hojas...")
            analytics_data, users_data, incidents_data = self._get_sheet_data(sheet_id)

            if len(analytics_data) <= 1:
                print("[WARN] No hay suficientes datos para calcular KPIs")
                return False

            print("[INFO] Calculando KPIs...")
            kpis = self._calculate_kpis(analytics_data, users_data, incidents_data)

            print("[INFO] Escribiendo KPIs en MetricasIKUBOT...")
            metrics_sheet = self._create_metrics_sheet(sheet_id)
            self._write_kpis_to_sheet(metrics_sheet, kpis)

            print("[OK] Métricas actualizadas exitosamente")
            return True

        except Exception as e:
            print(f"[ERROR] Error al actualizar métricas: {e}")
            traceback.print_exc()
            return False

    def update_dashboard_tables(self, sheet_id, analytics_data, kpis):
        """Actualiza el dashboard con referencias a los KPIs de MetricasIKUBOT."""
        try:
            dashboard_sheet = self._create_dashboard_sheet(sheet_id)
            
            # Limpiar dashboard
            dashboard_sheet.clear()
            
            # Título
            dashboard_sheet.update('A1', [[
                'Dashboard de Analíticas IkuBot - Actualizado: ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]])
            dashboard_sheet.format('A1', {
                'backgroundColor': {'red': 0.1, 'green': 0.4, 'blue': 0.7},
                'textFormat': {'bold': True, 'fontSize': 16, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            dashboard_sheet.merge_cells('A1:T1')
            
            # Nota sobre gráficos
            dashboard_sheet.update('A3', [['Nota: Para crear gráficos selecciona los datos en MetricasIKUBOT > Insertar > Gráfico']])
            dashboard_sheet.format('A3', {
                'backgroundColor': {'red': 1, 'green': 0.95, 'blue': 0.8},
                'textFormat': {'italic': True}
            })
            dashboard_sheet.merge_cells('A3:T3')
            
            # Crear tablas de resumen
            self._create_daily_interactions_table(analytics_data, dashboard_sheet)
            self._create_interaction_types_table(analytics_data, dashboard_sheet)
            self._create_hourly_distribution_table(analytics_data, dashboard_sheet)
            self._create_incidents_vs_normal_table(analytics_data, dashboard_sheet)
            
            print("[OK] Dashboard actualizado exitosamente")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error al actualizar dashboard: {e}")
            traceback.print_exc()
            return False

    def _create_daily_interactions_table(self, data, sheet):
        """Genera la tabla de interacciones por día en el dashboard."""
        try:
            daily_counts = {}
            for row in data[1:]:
                if len(row) >= 2:
                    date = row[1]
                    daily_counts[date] = daily_counts.get(date, 0) + 1
            
            sheet.update('A5', [['Interacciones por Día']])
            sheet.format('A5', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('A6', [['Fecha', 'Interacciones']])
            sheet.format('A6:B6', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            sorted_dates = sorted(daily_counts.items())
            if sorted_dates:
                values = [[date, count] for date, count in sorted_dates]
                sheet.update('A7', values)
            
        except Exception as e:
            print(f"Error en tabla diaria: {e}")

    def _create_interaction_types_table(self, data, sheet):
        """Genera la tabla de tipos de interacción en el dashboard."""
        try:
            type_counts = {}
            for row in data[1:]:
                if len(row) >= 4:
                    interaction_type = row[3]
                    if interaction_type:
                        type_counts[interaction_type] = type_counts.get(interaction_type, 0) + 1
            
            sheet.update('D5', [['Tipos de Interacción']])
            sheet.format('D5', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('D6', [['Tipo', 'Cantidad']])
            sheet.format('D6:E6', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            if type_counts:
                values = [[tipo, count] for tipo, count in type_counts.items()]
                sheet.update('D7', values)
            
        except Exception as e:
            print(f"Error en tabla de tipos: {e}")

    def _create_hourly_distribution_table(self, data, sheet):
        """Genera la tabla de distribución de interacciones por horas en el dashboard."""
        try:
            hourly_counts = {}
            for row in data[1:]:
                if len(row) >= 3:
                    time_str = row[2]
                    if time_str and ':' in time_str:
                        hour = time_str.split(':')[0]
                        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            sheet.update('G5', [['Distribución por Horas']])
            sheet.format('G5', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('G6', [['Hora', 'Interacciones']])
            sheet.format('G6:H6', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            sorted_hours = sorted(hourly_counts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
            if sorted_hours:
                values = [[f"{hour}:00", count] for hour, count in sorted_hours]
                sheet.update('G7', values)
            
        except Exception as e:
            print(f"Error en tabla horaria: {e}")

    def _create_incidents_vs_normal_table(self, data, sheet):
        """Genera la tabla comparativa entre incidencias y consultas normales en el dashboard."""
        try:
            incident_counts = {'Incidencia': 0, 'Consulta Normal': 0}
            for row in data[1:]:
                if len(row) >= 4:
                    interaction_type = row[3].strip().lower()
                    if interaction_type == 'incidencia_completada':
                        incident_counts['Incidencia'] += 1
                    else:
                        incident_counts['Consulta Normal'] += 1
            
            sheet.update('J5', [['Incidencias vs Consultas']])
            sheet.format('J5', {'textFormat': {'bold': True, 'fontSize': 12}})
            
            sheet.update('J6', [['Tipo', 'Cantidad']])
            sheet.format('J6:K6', {
                'backgroundColor': {'red': 0.8, 'green': 0.9, 'blue': 1},
                'textFormat': {'bold': True}
            })
            
            values = [['Incidencias', incident_counts['Incidencia']], 
                     ['Consultas Normales', incident_counts['Consulta Normal']]]
            sheet.update('J7', values)
            
        except Exception as e:
            print(f"Error en tabla de incidencias: {e}")

    def log_interaction(self, sheet_id, interaction_data):
        """Registra una nueva interacción en la hoja AnalyticasIKUBOT."""
        max_retries = 3
        retry = 0
        while retry < max_retries:
            try:
                self._refresh_credentials()
                worksheet = self._create_analytics_sheet(sheet_id)

                now = datetime.now()
                row_data = [
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    interaction_data.get('tipo_interaccion', ''),
                    interaction_data.get('mensaje_usuario', '')[:300],
                    interaction_data.get('respuesta_bot', '')[:300],
                    interaction_data.get('session_id', ''),
                ]

                worksheet.append_row(row_data)
                return True
            except gspread.exceptions.APIError as e:
                print(f"[WARN] Error de API al registrar interacción (intento {retry+1}): {e}")
                time.sleep(2 ** retry)
                retry += 1
            except Exception as e:
                print(f"[ERROR] Error al registrar interacción: {e}")
                traceback.print_exc()
                time.sleep(2 ** retry)
                retry += 1
        print("[ERROR] No se pudo registrar la interacción después de múltiples intentos")
        return False

    def add_incident(self, sheet_id, sheet_name, incident_data):
        """Agrega una nueva incidencia a la hoja correspondiente."""
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
        
        print("[ERROR] Fallo después de múltiples intentos")
        return False

    def add_user_profile(self, sheet_id, sheet_name, user_profile):
        """Agrega o actualiza el registro de usuario en la hoja UsuariosIKUBOT."""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self._refresh_credentials()
                worksheet = self._create_users_sheet(sheet_id, sheet_name)

                row_data = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_profile.get('session_id', ''),
                    user_profile.get('nombre', ''),
                    user_profile.get('tipo_usuario', ''),
                    user_profile.get('telefono', ''),
                ]

                worksheet.append_row(row_data)
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

        print("[ERROR] Fallo después de múltiples intentos")
        return False

    def test_connection(self, sheet_id, sheet_name):
        """Verifica la conexión con Google Sheets y retorna el estado."""
        try:
            self._refresh_credentials()
            sheet = self.client.open_by_key(sheet_id).worksheet(sheet_name)
            rows = sheet.get_all_values()
            return f"[OK] Conexión exitosa. Filas: {len(rows)}"
        except Exception as e:
            return f"[ERROR] Error de conexión: {str(e)}"

    def get_incident_stats(self, sheet_id, sheet_name):
        """Obtiene estadísticas detalladas de las incidencias registradas."""
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