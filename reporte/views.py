from django.shortcuts import render
from rest_framework import generics
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .serializers import ComedorListaSerializer, ComedorListaLabelSerializer
from encuesta.models import Encuesta, AlimentoEncuesta
from django.db.models import Count, Sum, F, Q
from django.http import JsonResponse, HttpResponse
from django.db import connection
import csv
from responsable_organizacion.models import ResponsableOrganizacion
from comedor.models import Comedor
from comida.models import Comida

# Create your views here.

# Consultar raciones del ultimo mes ------------------------------------------------------------------------------------
def racionesPorDia(comedor, fecha_inicio, fecha_fin):
	lista = Encuesta.objects.filter(comedor=comedor, fecha__range=(fecha_inicio, fecha_fin))
	lista = lista.values('fecha').annotate(cantidad=Sum(	F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))).order_by('fecha')
	return lista

class RacionesMesViewList(generics.ListAPIView):

	serializer_class = ComedorListaSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor = kwargs['comedor']
		today = date.today()
		td = timedelta(29)
		lista = racionesPorDia(comedor, today-td, today)
		diccionario = {
			'comedor': comedor,
			'lista': list(lista)
		}
		return JsonResponse(diccionario, safe=False)

# Consultar raciones de la ultima semana -------------------------------------------------------------------------------
class RacionesSemanaViewList(generics.ListAPIView):

	serializer_class = ComedorListaSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor = kwargs['comedor']
		today = date.today()
		td = timedelta(6)
		lista = racionesPorDia(comedor, today - td, today)
		diccionario = {
			'comedor': comedor,
			'lista': list(lista)
		}
		return JsonResponse(diccionario, safe=False)

# Consultas de comidas del ultimo mes -----------------------------------------------------------------------------

def getComidaFecha(e):
	return e['comida__nombre'] + ' ' + str(e['encuesta__fecha'].year)+str(e['encuesta__fecha'].month)+str(e['encuesta__fecha'].day)
def getComidaDia(comedor, fecha_inicio, fecha_fin):
	# Obtenemos las comidas únicas por encuesta para evitar duplicar las cantidades
	comidas_unicas = AlimentoEncuesta.objects.filter(
		encuesta__fecha__range=(fecha_inicio, fecha_fin), 
		encuesta__comedor=comedor
	).values('encuesta', 'comida__nombre', 'encuesta__fecha', 'etapa_comida').distinct()
	
	# Agrupamos las comidas por encuesta y etapa_comida para poder dividir las raciones
	from collections import defaultdict
	encuestas_comidas = defaultdict(lambda: defaultdict(list))
	
	for item in comidas_unicas:
		encuesta_id = item['encuesta']
		etapa_comida = item['etapa_comida']
		comida_nombre = item['comida__nombre']
		fecha = item['encuesta__fecha']
		
		# Agrupamos por etapa_comida (ej: todas las "entradas")
		encuestas_comidas[encuesta_id][etapa_comida].append({
			'comida_nombre': comida_nombre,
			'etapa_comida': etapa_comida,
			'fecha': fecha
		})
	
	# Luego creamos una lista de diccionarios con las cantidades correctas
	cantidad_raciones_comida_dias = []
	for encuesta_id, etapas_comida in encuestas_comidas.items():
		encuesta = Encuesta.objects.get(id=encuesta_id)
		total_comensales = encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 + encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
		
		for etapa_comida, comidas in etapas_comida.items():
			# Dividir los comensales entre las comidas de la misma etapa
			# Si hay 2 comensales y 2 entradas: cada entrada = 1 comensal
			comidas_count = len(comidas)
			if comidas_count > 0:
				# Calcular cuántos comensales come cada comida
				comensales_base = total_comensales // comidas_count  # División entera
				comensales_extra = total_comensales % comidas_count   # Resto para distribuir
				
				for i, comida_info in enumerate(comidas):
					# Las primeras 'comensales_extra' comidas reciben un comensal adicional
					raciones_por_comida = comensales_base + (1 if i < comensales_extra else 0)
					
					cantidad_raciones_comida_dias.append({
						'encuesta__fecha': comida_info['fecha'],
						'comida__nombre': comida_info['comida_nombre'],
						'etapa_comida': comida_info['etapa_comida'],
						'cantidad': raciones_por_comida
					})
			else:
				# Si no hay comidas, no agregamos nada
				pass
	
	# Agrupamos por fecha y comida, sumando las cantidades
	agrupado = defaultdict(float)
	for item in cantidad_raciones_comida_dias:
		key = (item['encuesta__fecha'], item['comida__nombre'])
		agrupado[key] += item['cantidad']
	
	# Obtenemos todas las fechas y comidas únicas
	fechas = sorted(set([item['encuesta__fecha'] for item in cantidad_raciones_comida_dias]))
	comidas = set([item['comida__nombre'] for item in cantidad_raciones_comida_dias])
	
	# Creamos la estructura de datos correcta: cada comida tiene un array de datos para cada fecha
	comida_semana = []
	for comida in comidas:
		datos_por_fecha = []
		for fecha in fechas:
			cantidad = agrupado.get((fecha, comida), 0)
			datos_por_fecha.append(round(cantidad, 2))  # Redondeamos a 2 decimales
		
		comida_semana.append({
			'label': comida,
			'data': datos_por_fecha,
		})
	
	return list(comida_semana), list(fechas)
class ComidasMesViewList(generics.ListAPIView):

	serializer_class = ComedorListaLabelSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor = kwargs['comedor']
		today = date.today()
		td = timedelta(29)
		lista = getComidaDia(comedor, today-td, today)
		diccionario = {
			'comedor': comedor,
			'labels': lista[1],
			'lista': lista[0]
		}
		return JsonResponse(diccionario, safe=False)

# Consultas de comidas de la ultima semana ----------------------------------------------------------------------------------

class ComidasSemanaViewList(generics.ListAPIView):

	serializer_class = ComedorListaLabelSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor = kwargs['comedor']
		today = date.today()
		td = timedelta(6)
		lista = getComidaDia(comedor, today-td, today)
		diccionario = {
			'comedor': comedor,
			'labels': lista[1],
			'lista': lista[0]
		}
		return JsonResponse(diccionario, safe=False)

# Reportes Nutricionales ------------------------------------------------------------------------------------

def calcular_nutrientes_por_encuesta(encuesta):
	"""Calcula los nutrientes promedio por comensal para una encuesta"""
	alimentos_encuesta = AlimentoEncuesta.objects.filter(encuesta=encuesta)
	total_comensales = encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 + encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
	
	if total_comensales == 0:
		return None
	
	nutrientes_por_comensal = {
		'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
		'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0
	}
	
	for alimento_encuesta in alimentos_encuesta:
		# Obtener la unidad y su equivalencia en gramos
		unidad = alimento_encuesta.unidad
		cantidad_unidades = float(alimento_encuesta.cantidad)
		
		# Convertir a gramos usando la equivalencia de la unidad
		if unidad.equivalencia_gramos:
			cantidad_gramos = cantidad_unidades * float(unidad.equivalencia_gramos)
		else:
			# Si no hay equivalencia en gramos, usar ml y asumir densidad 1g/ml
			cantidad_gramos = cantidad_unidades * float(unidad.equivalencia_ml)
		
		# Obtener nutrientes del alimento (por 100g)
		alimento = alimento_encuesta.alimento
		
		# Calcular nutrientes totales de este alimento
		nutrientes_alimento = {
			'hidratos': (float(alimento.hidratos_carbono) * cantidad_gramos) / 100,
			'proteinas': (float(alimento.proteinas) * cantidad_gramos) / 100,
			'grasasSaturadas': (float(alimento.grasas) * cantidad_gramos) / 100,
			'grasasTotales': (float(alimento.grasas_totales) * cantidad_gramos) / 100,
			'kilocalorias': (float(alimento.energia) * cantidad_gramos) / 100,
			'sodio': (float(alimento.sodio) * cantidad_gramos) / 100
		}
		
		# Sumar a los nutrientes totales
		for nutriente in nutrientes_por_comensal:
			nutrientes_por_comensal[nutriente] += nutrientes_alimento[nutriente]
	
	# Dividir por número de comensales para obtener nutrientes por comensal
	for nutriente in nutrientes_por_comensal:
		nutrientes_por_comensal[nutriente] = nutrientes_por_comensal[nutriente] / total_comensales
	
	return nutrientes_por_comensal

class ReportesNutricionalesMesViewList(generics.ListAPIView):
	"""Reportes nutricionales de los últimos 12 meses"""
	serializer_class = ComedorListaSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor_id = kwargs['comedor']
		
		# Obtener comedor
		try:
			comedor = Comedor.objects.get(id=comedor_id)
		except Comedor.DoesNotExist:
			return JsonResponse({'error': 'Comedor no encontrado'}, status=404)
		
		# Calcular fecha límite (12 meses atrás)
		today = date.today()
		td = relativedelta(months=-11)
		fecha_limite = today + td
		
		# Obtener encuestas de los últimos 12 meses
		encuestas_12_meses = Encuesta.objects.filter(
			comedor=comedor,
			fecha__range=(fecha_limite, today)
		).order_by('-fecha')
		
		# Calcular nutrientes por mes
		nutrientes_por_mes = {}
		for encuesta in encuestas_12_meses:
			mes_key = f"{encuesta.fecha.year}-{encuesta.fecha.month:02d}"
			if mes_key not in nutrientes_por_mes:
				nutrientes_por_mes[mes_key] = {
					'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
					'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0,
					'total_encuestas': 0
				}
			
			nutrientes = calcular_nutrientes_por_encuesta(encuesta)
			if nutrientes:
				for nutriente in nutrientes_por_mes[mes_key]:
					if nutriente in nutrientes:
						nutrientes_por_mes[mes_key][nutriente] += nutrientes[nutriente]
				nutrientes_por_mes[mes_key]['total_encuestas'] += 1
		
		# Calcular promedios por mes
		promedios_mes = []
		for mes, datos in nutrientes_por_mes.items():
			if datos['total_encuestas'] > 0:
				promedio = {
					'mes': mes,
					'hidratos': round(datos['hidratos'] / datos['total_encuestas'], 2),
					'proteinas': round(datos['proteinas'] / datos['total_encuestas'], 2),
					'grasasSaturadas': round(datos['grasasSaturadas'] / datos['total_encuestas'], 2),
					'grasasTotales': round(datos['grasasTotales'] / datos['total_encuestas'], 2),
					'kilocalorias': round(datos['kilocalorias'] / datos['total_encuestas'], 2),
					'sodio': round(datos['sodio'] / datos['total_encuestas'], 2)
				}
				promedios_mes.append(promedio)
		
		# Ordenar por fecha (mes-año)
		promedios_mes.sort(key=lambda x: x['mes'])
		
		diccionario = {
			'comedor': comedor_id,
			'lista': promedios_mes
		}
		return JsonResponse(diccionario, safe=False)

class ReportesNutricionalesSemanaViewList(generics.ListAPIView):
	"""Reportes nutricionales de los últimos 7 días"""
	serializer_class = ComedorListaSerializer
	http_method_names = ['get']

	def get(self, request, *args, **kwargs):
		comedor_id = kwargs['comedor']
		
		# Obtener comedor
		try:
			comedor = Comedor.objects.get(id=comedor_id)
		except Comedor.DoesNotExist:
			return JsonResponse({'error': 'Comedor no encontrado'}, status=404)
		
		# Calcular fecha límite (7 días atrás)
		today = date.today()
		td = timedelta(days=-6)
		fecha_limite = today + td
		
		# Obtener encuestas de los últimos 7 días
		encuestas_7_dias = Encuesta.objects.filter(
			comedor=comedor,
			fecha__range=(fecha_limite, today)
		).order_by('-fecha')
		
		# Calcular nutrientes por día
		nutrientes_por_dia = {}
		for encuesta in encuestas_7_dias:
			dia_key = str(encuesta.fecha)
			if dia_key not in nutrientes_por_dia:
				nutrientes_por_dia[dia_key] = {
					'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
					'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0,
					'total_encuestas': 0
				}
			
			nutrientes = calcular_nutrientes_por_encuesta(encuesta)
			if nutrientes:
				for nutriente in nutrientes_por_dia[dia_key]:
					if nutriente in nutrientes:
						nutrientes_por_dia[dia_key][nutriente] += nutrientes[nutriente]
				nutrientes_por_dia[dia_key]['total_encuestas'] += 1
		
		# Calcular promedios por día
		promedios_dia = []
		for dia, datos in nutrientes_por_dia.items():
			if datos['total_encuestas'] > 0:
				promedio = {
					'dia': dia,
					'hidratos': round(datos['hidratos'] / datos['total_encuestas'], 2),
					'proteinas': round(datos['proteinas'] / datos['total_encuestas'], 2),
					'grasasSaturadas': round(datos['grasasSaturadas'] / datos['total_encuestas'], 2),
					'grasasTotales': round(datos['grasasTotales'] / datos['total_encuestas'], 2),
					'kilocalorias': round(datos['kilocalorias'] / datos['total_encuestas'], 2),
					'sodio': round(datos['sodio'] / datos['total_encuestas'], 2)
				}
				promedios_dia.append(promedio)
		
		# Ordenar por fecha (día)
		promedios_dia.sort(key=lambda x: x['dia'])
		
		diccionario = {
			'comedor': comedor_id,
			'lista': promedios_dia
		}
		return JsonResponse(diccionario, safe=False)


def export_detailed_raciones_csv(request):
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="reporte_raciones_detallado.csv"'

	writer = csv.writer(response)
	writer.writerow([
		'Fecha', 'Organizacion', 'Comedor', 'Comida', 'Tipo de Comida',
		'Cantidad Raciones', 'Hidratos (g)', 'Proteina (g)', 'Grasas Saturadas (g)',
		'Grasas Totales (g)', 'Sodio (g)', 'Kilocalorias'
	])

	organizacion_seleccionada = request.GET.get('organizacion')
	comedor_seleccionado = request.GET.get('comedor')
	tipo_organizacion_seleccionada = request.GET.get('tipo_organizacion')

	r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
	if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
		comedores_permitidos = Comedor.objects.all()
	else:
		comedores_permitidos = Comedor.objects.filter(
			Q(responsable_comedor=request.user) |
			Q(organizacion_regional__in=r) |
			Q(organizacion_regional__organizacion_superior__in=r)
		)

	lc = comedores_permitidos

	if comedor_seleccionado:
		lc = comedores_permitidos.filter(id=comedor_seleccionado)
	elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'padre':
		lc = comedores_permitidos.filter(
			Q(organizacion_regional_id=organizacion_seleccionada) |
			Q(organizacion_regional__organizacion_superior_id=organizacion_seleccionada)
		)
	elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'hija':
		lc = comedores_permitidos.filter(organizacion_regional_id=organizacion_seleccionada)

	fecha_inicio_str = request.GET.get('fecha_inicio')
	fecha_fin_str = request.GET.get('fecha_fin')

	if fecha_inicio_str and fecha_fin_str:
		try:
			fecha_inicio = date.fromisoformat(fecha_inicio_str)
			fecha_fin = date.fromisoformat(fecha_fin_str)
			max_fecha_fin_permitida = fecha_inicio + relativedelta(months=3) - timedelta(days=1)
			if fecha_fin > max_fecha_fin_permitida:
				fecha_fin = max_fecha_fin_permitida
			if fecha_inicio > fecha_fin:
				fecha_fin = date.today()
				fecha_inicio = fecha_fin - relativedelta(months=3)
		except ValueError:
			fecha_fin = date.today()
			fecha_inicio = fecha_fin - relativedelta(months=3)
	else:
		fecha_fin = date.today()
		fecha_inicio = fecha_fin - relativedelta(months=3)

	relevant_alimento_encuestas = AlimentoEncuesta.objects.filter(
		encuesta__comedor__in=lc,
		encuesta__fecha__range=(fecha_inicio, fecha_fin)
	).select_related(
		'encuesta', 'encuesta__comedor',
		'encuesta__comedor__organizacion_regional',
		'encuesta__comedor__organizacion_regional__organizacion_superior',
		'comida', 'alimento', 'unidad',
	).order_by('encuesta__fecha', 'encuesta__comedor__nombre', 'comida__nombre')

	grouped_data = {}
	for ae_entry in relevant_alimento_encuestas:
		key = (ae_entry.encuesta.id, ae_entry.comida.id)
		if key not in grouped_data:
			grouped_data[key] = {
				'encuesta': ae_entry.encuesta,
				'comida': ae_entry.comida,
				'ingredientes': [],
			}
		grouped_data[key]['ingredientes'].append(ae_entry)

	comida_ids = {d['comida'].id for d in grouped_data.values()}
	comida_horario_map = {}
	if comida_ids:
		placeholders = ','.join(['%s'] * len(comida_ids))
		with connection.cursor() as cursor:
			cursor.execute(
				f"SELECT cch.comida_id, ch.nombre "
				f"FROM comida_comida_horarios cch "
				f"JOIN comida_horario ch ON ch.id = cch.horario_id "
				f"WHERE cch.comida_id IN ({placeholders})",
				list(comida_ids)
			)
			for comida_id, horario_nombre in cursor.fetchall():
				comida_horario_map[comida_id] = horario_nombre

	for key, data in grouped_data.items():
		encuesta = data['encuesta']
		comida = data['comida']

		total_raciones = (
			encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 +
			encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
		)

		total_hidratos = total_proteina = total_grasas_sat = 0
		total_grasas_tot = total_sodio_mg = total_kcal = 0

		for ae in data['ingredientes']:
			alimento = ae.alimento
			unidad = ae.unidad
			if unidad.equivalencia_gramos:
				cantidad_gramos = float(ae.cantidad) * float(unidad.equivalencia_gramos)
			else:
				cantidad_gramos = float(ae.cantidad) * float(unidad.equivalencia_ml)
			factor = cantidad_gramos / 100
			total_hidratos += float(alimento.hidratos_carbono) * factor
			total_proteina += float(alimento.proteinas) * factor
			total_grasas_sat += float(alimento.grasas) * factor
			total_grasas_tot += float(alimento.grasas_totales) * factor
			total_sodio_mg += float(alimento.sodio) * factor
			total_kcal += float(alimento.energia) * factor

		org = encuesta.comedor.organizacion_regional
		if org and org.es_organizacion_regional and org.organizacion_superior:
			org_nombre = org.organizacion_superior.nombre
		elif org:
			org_nombre = org.nombre
		else:
			org_nombre = ''

		tipo_comida = comida_horario_map.get(comida.id, '-')

		if total_raciones > 0:
			writer.writerow([
				encuesta.fecha.strftime('%d/%m/%Y'),
				org_nombre,
				encuesta.comedor.nombre,
				comida.nombre,
				tipo_comida,
				f"{total_raciones:.0f}",
				f"{total_hidratos / total_raciones:.2f}",
				f"{total_proteina / total_raciones:.2f}",
				f"{total_grasas_sat / total_raciones:.2f}",
				f"{total_grasas_tot / total_raciones:.2f}",
				f"{(total_sodio_mg / 1000) / total_raciones:.2f}",
				f"{total_kcal / total_raciones:.2f}",
			])

	return response


def export_ingredients_csv(request):
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="reporte_alimentos.csv"'

	writer = csv.writer(response)

	organizacion_seleccionada = request.GET.get('organizacion')
	comedor_seleccionado = request.GET.get('comedor')
	tipo_organizacion_seleccionada = request.GET.get('tipo_organizacion')

	r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
	if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
		comedores_permitidos = Comedor.objects.all()
	else:
		comedores_permitidos = Comedor.objects.filter(
			Q(responsable_comedor=request.user) |
			Q(organizacion_regional__in=r) |
			Q(organizacion_regional__organizacion_superior__in=r)
		)

	lc = comedores_permitidos

	if comedor_seleccionado:
		lc = comedores_permitidos.filter(id=comedor_seleccionado)
	elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'padre':
		lc = comedores_permitidos.filter(
			Q(organizacion_regional_id=organizacion_seleccionada) |
			Q(organizacion_regional__organizacion_superior_id=organizacion_seleccionada)
		)
	elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'hija':
		lc = comedores_permitidos.filter(organizacion_regional_id=organizacion_seleccionada)

	fecha_inicio_str = request.GET.get('fecha_inicio')
	fecha_fin_str = request.GET.get('fecha_fin')

	if fecha_inicio_str and fecha_fin_str:
		try:
			fecha_inicio = date.fromisoformat(fecha_inicio_str)
			fecha_fin = date.fromisoformat(fecha_fin_str)
			max_fecha_fin_permitida = fecha_inicio + relativedelta(months=3) - timedelta(days=1)
			if fecha_fin > max_fecha_fin_permitida:
				fecha_fin = max_fecha_fin_permitida
			if fecha_inicio > fecha_fin:
				fecha_fin = date.today()
				fecha_inicio = fecha_fin - relativedelta(months=3)
		except ValueError:
			fecha_fin = date.today()
			fecha_inicio = fecha_fin - relativedelta(months=3)
	else:
		fecha_fin = date.today()
		fecha_inicio = fecha_fin - relativedelta(months=3)

	relevant_alimento_encuestas = AlimentoEncuesta.objects.filter(
		encuesta__comedor__in=lc,
		encuesta__fecha__range=(fecha_inicio, fecha_fin)
	).select_related(
		'encuesta', 'encuesta__comedor',
		'encuesta__comedor__organizacion_regional',
		'encuesta__comedor__organizacion_regional__organizacion_superior',
		'comida', 'alimento', 'unidad',
	).order_by('encuesta__fecha', 'encuesta__comedor__nombre', 'comida__nombre')

	grouped_data = {}
	for ae_entry in relevant_alimento_encuestas:
		key = (ae_entry.encuesta.id, ae_entry.comida.id)
		if key not in grouped_data:
			grouped_data[key] = {
				'encuesta': ae_entry.encuesta,
				'comida': ae_entry.comida,
				'ingredientes': [],
			}
		grouped_data[key]['ingredientes'].append(ae_entry)

	alimento_info = {}
	for data in grouped_data.values():
		for ae in data['ingredientes']:
			aid = ae.alimento.id
			if aid not in alimento_info:
				unit = 'l' if ae.unidad.equivalencia_ml else 'kg'
				alimento_info[aid] = {'nombre': ae.alimento.nombre, 'unit': unit}
	alimentos_ordered = sorted(alimento_info.items(), key=lambda x: x[1]['nombre'])

	comida_ids = {d['comida'].id for d in grouped_data.values()}
	comida_horario_map = {}
	if comida_ids:
		placeholders = ','.join(['%s'] * len(comida_ids))
		with connection.cursor() as cursor:
			cursor.execute(
				f"SELECT cch.comida_id, ch.nombre "
				f"FROM comida_comida_horarios cch "
				f"JOIN comida_horario ch ON ch.id = cch.horario_id "
				f"WHERE cch.comida_id IN ({placeholders})",
				list(comida_ids)
			)
			for comida_id, horario_nombre in cursor.fetchall():
				comida_horario_map[comida_id] = horario_nombre

	fixed_headers = ['Fecha', 'Organizacion', 'Comedor', 'Comida', 'Tipo de Comida', 'Cantidad Raciones']
	alimento_headers = [f"{info['nombre']} ({info['unit']})" for _, info in alimentos_ordered]
	writer.writerow(fixed_headers + alimento_headers)

	for key, data in grouped_data.items():
		encuesta = data['encuesta']
		comida = data['comida']

		total_raciones = (
			encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 +
			encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
		)

		alimento_kg = {}
		for ae in data['ingredientes']:
			unidad = ae.unidad
			if unidad.equivalencia_gramos:
				cantidad_kg = float(ae.cantidad) * float(unidad.equivalencia_gramos) / 1000
			else:
				cantidad_kg = float(ae.cantidad) * float(unidad.equivalencia_ml) / 1000
			alimento_kg[ae.alimento.id] = cantidad_kg

		org = encuesta.comedor.organizacion_regional
		if org and org.es_organizacion_regional and org.organizacion_superior:
			org_nombre = org.organizacion_superior.nombre
		elif org:
			org_nombre = org.nombre
		else:
			org_nombre = ''

		tipo_comida = comida_horario_map.get(comida.id, '-')

		row = [
			encuesta.fecha.strftime('%d/%m/%Y'),
			org_nombre,
			encuesta.comedor.nombre,
			comida.nombre,
			tipo_comida,
			f"{total_raciones:.0f}",
		]
		for alimento_id, _ in alimentos_ordered:
			val = alimento_kg.get(alimento_id)
			row.append(f"{val:.3f}" if val is not None else '')
		writer.writerow(row)

	return response
