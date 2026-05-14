from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import chain

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum, F, Q
from .models import ReporteNutricional, ReportesGenerales, ReportesRaciones, ReportesNutricionales
from django.contrib import admin
from comedor.models import Comedor
from encuesta.models import Encuesta, AlimentoEncuesta
from comida.models import Comida
from responsable_organizacion.models import ResponsableOrganizacion


class ReportesGeneralesAdmin(admin.ModelAdmin):

	change_list_template = 'reportes_generales.html'

	def changelist_view(self, request, extra_context=None):

		response = super().changelist_view(
			request,
			extra_context=extra_context,
		)

		r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
		if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
			lc = Comedor.objects.all()
		else:
			lc = Comedor.objects.filter(
				Q(responsable_comedor=request.user) |
				Q(organizacion_regional__in=r) |
				Q(organizacion_regional__organizacion_superior__in=r)
			)

		# Comedores por provincia
		comedores_qs = lc.values('provincia__nombre').annotate(dcount=Count('provincia__nombre')).order_by()
		comedores = list(comedores_qs)
		response.context_data['comedores_provincia'] = comedores

		# Listado de provincias
		response.context_data['provincias'] = comedores_qs.values('provincia__nombre')

		# Listado de departamentos

		comedores = lc.values('provincia__nombre', 'departamento__nombre').annotate(dcount=Count('departamento__nombre')).order_by()
		comedores = list(comedores)
		response.context_data['comedores_departamento'] = comedores

		# Listado de gobiernos_locales

		comedores = lc.values('provincia__nombre', 'departamento__nombre', 'gobierno_local__nombre').annotate(dcount=Count('gobierno_local__nombre')).order_by()
		comedores = list(comedores)
		response.context_data['comedores_gobierno_local'] = comedores

		# Listado de gobiernos_locales

		comedores = lc.values('provincia__nombre', 'departamento__nombre', 'gobierno_local__nombre', 'localidad__nombre').annotate(dcount=Count('localidad__nombre')).order_by()
		comedores = list(comedores)
		response.context_data['comedores_localidad'] = comedores

		# Comedores por organizacion

		comedores_qs_or = lc.filter(organizacion_regional__es_organizacion_regional=True).values('organizacion_regional__organizacion_superior__nombre').values_list('organizacion_regional__organizacion_superior__nombre', flat=True)
		comedores_qs_o = lc.filter(organizacion_regional__es_organizacion_regional=False).values('organizacion_regional__nombre').values_list('organizacion_regional__nombre', flat=True)
		comedores = list(comedores_qs_or) + list(comedores_qs_o)
		comedores = dict(Counter(comedores))

		c = []
		for a in comedores:
			c.append({
				'organizacion': a,
				'dcount': comedores[a],
			})

		response.context_data['comedores_organizacion'] = c

		# Listado de organizaciones

		comedores = lc.filter(organizacion_regional__es_organizacion_regional=True).values('organizacion_regional__organizacion_superior__nombre').values_list('organizacion_regional__organizacion_superior__nombre', flat=True)
		comedores = list(set(comedores))
		response.context_data['comedores_organizaciones'] = comedores

		# Listado de organizaciones regionales

		comedores = lc.filter(organizacion_regional__es_organizacion_regional=True).values('organizacion_regional__organizacion_superior__nombre', 'organizacion_regional__nombre').annotate(dcount=Count('organizacion_regional__nombre')).order_by()
		comedores = list(comedores)
		response.context_data['comedores_organizacion_regional'] = comedores

		return response


class ReportesRacionesAdmin(admin.ModelAdmin):

	change_list_template = 'reportes_raciones.html'

	def getMesAñoComida(self, e):
		mes = e['mes']
		if mes < 10:
			mes = '0' + str(mes)
		else:
			mes = str(mes)
		return str(e['año']) + ' ' + mes + ' ' + e['comida']

	def getAñoMes(self, e):
		e = e.split('/')
		mes = e[0]
		if int(mes) < 10:
			mes = '0' + str(mes)
		else:
			mes = str(mes)
		return e[1] + ' ' + mes

	def getComidaMesAño(self, e):
		mes = e['encuesta__fecha__month']
		if mes < 10:
			mes = '0' + str(mes)
		else:
			mes = str(mes)
		return e['comida__nombre'] + ' ' + str(e['encuesta__fecha__year']) + ' ' + mes

	def getFechaComida(self, e):
		return str(e['fecha'].year)+str(e['fecha'].month)+str(e['fecha'].day) + ' ' + e['comida']

	def getComidaFecha(self, e):
		return e['comida__nombre'] + ' ' + str(e['encuesta__fecha'].year)+str(e['encuesta__fecha'].month)+str(e['encuesta__fecha'].day)

	def changelist_view(self, request, extra_context=None):

		organizacion_seleccionada = request.GET.get('organizacion')
		comedor_seleccionado = request.GET.get('comedor')
		tipo_organizacion_seleccionada = request.GET.get('tipo_organizacion')
		get_original = request.GET.copy()
		get_limpio = request.GET.copy()

		for key in ['organizacion', 'comedor', 'tipo_organizacion']:
			if key in get_limpio:
				del get_limpio[key]

		request.GET = get_limpio
		response = super().changelist_view(request, extra_context=extra_context)
		request.GET = get_original

		if not hasattr(response, 'context_data'):
			return response

		r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
		if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
			lc = Comedor.objects.all()
		else:
			lc = Comedor.objects.filter(
				Q(responsable_comedor=request.user) |
				Q(organizacion_regional__in=r) |
				Q(organizacion_regional__organizacion_superior__in=r)
			)
		comedores_permitidos = lc

		organizaciones_dict = {}
		comedores_por_organizacion = []

		for comedor in comedores_permitidos.select_related(
				'organizacion_regional',
				'organizacion_regional__organizacion_superior'
		):
			org_hija = comedor.organizacion_regional
			if not org_hija:
				continue
			org_padre = org_hija.organizacion_superior

			if org_hija.es_organizacion_regional and org_padre:
				organizaciones_dict[org_padre.id] = {'id': org_padre.id, 'nombre': org_padre.nombre, 'tipo': 'padre', 'padre_id': ''}
				organizaciones_dict[org_hija.id] = {'id': org_hija.id, 'nombre': org_hija.nombre, 'tipo': 'hija', 'padre_id': org_padre.id}
				comedores_por_organizacion.append({'id': comedor.id, 'nombre': comedor.nombre, 'organizacion_hija_id': org_hija.id, 'organizacion_padre_id': org_padre.id})
			else:
				organizaciones_dict[org_hija.id] = {'id': org_hija.id, 'nombre': org_hija.nombre, 'tipo': 'padre', 'padre_id': ''}
				comedores_por_organizacion.append({'id': comedor.id, 'nombre': comedor.nombre, 'organizacion_hija_id': org_hija.id, 'organizacion_padre_id': org_hija.id})

		organizaciones = sorted(organizaciones_dict.values(), key=lambda o: (str(o['padre_id']), o['tipo'], o['nombre']))

		nombre_organizacion_seleccionada = next(
			(o['nombre'] for o in organizaciones if str(o['id']) == str(organizacion_seleccionada)),
			None
		) if organizacion_seleccionada else None

		nombre_comedor_seleccionado = next(
			(c['nombre'] for c in comedores_por_organizacion if str(c['id']) == str(comedor_seleccionado)),
			None
		) if comedor_seleccionado else None

		response.context_data['organizaciones_raciones'] = organizaciones
		response.context_data['comedores_por_organizacion_raciones'] = comedores_por_organizacion
		response.context_data['organizacion_seleccionada_raciones'] = organizacion_seleccionada
		response.context_data['comedor_seleccionado_raciones'] = comedor_seleccionado
		response.context_data['tipo_organizacion_seleccionada_raciones'] = tipo_organizacion_seleccionada
		response.context_data['nombre_organizacion_seleccionada_raciones'] = nombre_organizacion_seleccionada
		response.context_data['nombre_comedor_seleccionado_raciones'] = nombre_comedor_seleccionado

		if comedor_seleccionado:
			lc = comedores_permitidos.filter(id=comedor_seleccionado)
		elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'padre':
			lc = comedores_permitidos.filter(
				Q(organizacion_regional_id=organizacion_seleccionada) |
				Q(organizacion_regional__organizacion_superior_id=organizacion_seleccionada)
			)
		elif organizacion_seleccionada and tipo_organizacion_seleccionada == 'hija':
			lc = comedores_permitidos.filter(organizacion_regional_id=organizacion_seleccionada)

		# Encuestas de los ultimos 12 meses ----------------------------------------------------------------------------

		today = date.today()
		td = relativedelta(months=-11)
		fecha = today + td
		fecha_limite = date(day=1, month=fecha.month, year=fecha.year)

		r_mes_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(fecha_limite, today))

		cantidad_raciones_meses = r_mes_total.values('fecha__year', 'fecha__month').annotate(
			cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))
		).order_by('fecha__year', 'fecha__month')
		response.context_data['raciones_mes'] = cantidad_raciones_meses

		cantidad_raciones_funcionamiento_meses = r_mes_total.values('fecha__year', 'fecha__month', 'funcionamiento').annotate(
			cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))
		)
		response.context_data['raciones_mes_funcionamiento'] = cantidad_raciones_funcionamiento_meses

		cantidad_raciones_rango_etario_meses = r_mes_total.values('fecha__year', 'fecha__month').annotate(
			cantidad_rango_1=Sum(F('cantidad_rango_1')), cantidad_rango_2=Sum(F('cantidad_rango_2')),
			cantidad_rango_3=Sum(F('cantidad_rango_3')), cantidad_rango_4=Sum(F('cantidad_rango_4'))
		)
		response.context_data['raciones_mes_rango_etario'] = cantidad_raciones_rango_etario_meses

		ae_mes = AlimentoEncuesta.objects.filter(
			encuesta__fecha__range=(fecha_limite, today), encuesta__comedor__in=lc
		).values(
			'encuesta_id', 'comida__nombre',
			'encuesta__fecha__year', 'encuesta__fecha__month',
			'encuesta__cantidad_rango_1', 'encuesta__cantidad_rango_2',
			'encuesta__cantidad_rango_3', 'encuesta__cantidad_rango_4',
		).distinct()

		comida_mes_map = {}
		for ae in ae_mes:
			key = (ae['encuesta__fecha__year'], ae['encuesta__fecha__month'], ae['comida__nombre'])
			raciones = (ae['encuesta__cantidad_rango_1'] + ae['encuesta__cantidad_rango_2'] +
						ae['encuesta__cantidad_rango_3'] + ae['encuesta__cantidad_rango_4'])
			if key not in comida_mes_map:
				comida_mes_map[key] = {'encuesta__fecha__year': ae['encuesta__fecha__year'], 'encuesta__fecha__month': ae['encuesta__fecha__month'], 'comida__nombre': ae['comida__nombre'], 'cantidad': 0}
			comida_mes_map[key]['cantidad'] += raciones

		cantidad_raciones_comida_meses = list(comida_mes_map.values())
		fechas_bd = set((r['encuesta__fecha__month'], r['encuesta__fecha__year']) for r in cantidad_raciones_comida_meses)
		fechas = sorted([str(f[0])+'/'+str(f[1]) for f in fechas_bd], key=self.getAñoMes)
		response.context_data['raciones_comida_mes'] = cantidad_raciones_comida_meses
		response.context_data['fechas_mes'] = fechas

		# Encuestas de los ultimos 30 dias -----------------------------------------------------------------------------

		today = date.today()
		td = timedelta(29)
		raciones_30_dias_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(today - td, today))
		raciones_30_dias_total = raciones_30_dias_total.values('fecha').annotate(
			cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))
		).order_by('fecha')
		response.context_data['raciones_dia'] = raciones_30_dias_total

		# Cantidad de raciones de los ultimos 7 dias -------------------------------------------------------------------

		today = date.today()
		td = timedelta(6)
		fecha = today - td
		r_semana_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(fecha, today))

		cantidad_raciones_funcionamiento_dias = r_semana_total.values('fecha', 'funcionamiento').annotate(
			cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))
		)
		response.context_data['raciones_semana_funcionamiento'] = cantidad_raciones_funcionamiento_dias

		cantidad_raciones_rango_etario_dias = r_semana_total.values('fecha').annotate(
			cantidad_rango_1=Sum(F('cantidad_rango_1')), cantidad_rango_2=Sum(F('cantidad_rango_2')),
			cantidad_rango_3=Sum(F('cantidad_rango_3')), cantidad_rango_4=Sum(F('cantidad_rango_4'))
		)
		response.context_data['raciones_semana_rango_etario'] = cantidad_raciones_rango_etario_dias

		ae_semana = AlimentoEncuesta.objects.filter(
			encuesta__fecha__range=(fecha, today), encuesta__comedor__in=lc
		).values(
			'encuesta_id', 'comida__nombre', 'encuesta__fecha',
			'encuesta__cantidad_rango_1', 'encuesta__cantidad_rango_2',
			'encuesta__cantidad_rango_3', 'encuesta__cantidad_rango_4',
		).distinct()

		comida_dia_map = {}
		for ae in ae_semana:
			key = (ae['encuesta__fecha'], ae['comida__nombre'])
			raciones = (ae['encuesta__cantidad_rango_1'] + ae['encuesta__cantidad_rango_2'] +
						ae['encuesta__cantidad_rango_3'] + ae['encuesta__cantidad_rango_4'])
			if key not in comida_dia_map:
				comida_dia_map[key] = {'encuesta__fecha': ae['encuesta__fecha'], 'comida__nombre': ae['comida__nombre'], 'cantidad': 0}
			comida_dia_map[key]['cantidad'] += raciones

		cantidad_raciones_comida_dias = sorted(comida_dia_map.values(), key=lambda x: x['encuesta__fecha'])
		fechas = set(r['encuesta__fecha'] for r in cantidad_raciones_comida_dias)
		response.context_data['raciones_comida_semana'] = cantidad_raciones_comida_dias
		response.context_data['fechas_semana'] = fechas

		return response

admin.site.register(ReportesGenerales, ReportesGeneralesAdmin)
admin.site.register(ReportesRaciones, ReportesRacionesAdmin)


# Comentamos el admin del modelo individual para ocultarlo completamente
# class ReporteNutricionalAdmin(admin.ModelAdmin):
# 	list_display = ['fecha', 'comedor', 'organizacion', 'encuesta']
# 	search_fields = ('comedor',)
# 	list_filter=('fecha','organizacion','comedor')

class ReportesNutricionalesAdmin(admin.ModelAdmin):
	change_list_template = 'reportes_nutricionales.html'

	def changelist_view(self, request, extra_context=None):
		response = super().changelist_view(
			request,
			extra_context=extra_context,
		)

		r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
		if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
			lc = Comedor.objects.all()
		else:
			lc = Comedor.objects.filter(
				Q(responsable_comedor=request.user) |
				Q(organizacion_regional__in=r) |
				Q(organizacion_regional__organizacion_superior__in=r)
			)

		# CÁLCULO AUTOMÁTICO DE NUTRIENTES BASADO EN ENCUESTAS
		today = date.today()
		td = relativedelta(months=-11)
		fecha_limite = today + td

		print(f"\n=== INICIO CÁLCULO NUTRICIONAL ===")
		print(f"Fecha límite: {fecha_limite}")
		print(f"Fecha actual: {today}")

		# Obtener todas las encuestas de los últimos 12 meses
		encuestas_12_meses = Encuesta.objects.filter(
			comedor__in=lc,
			fecha__range=(fecha_limite, today)
		).order_by('-fecha')
		
		print(f"Total encuestas encontradas: {encuestas_12_meses.count()}")

		# Calcular nutrientes por mes
		nutrientes_por_mes = {}
		for encuesta in encuestas_12_meses:
			mes_key = f"{encuesta.fecha.year}-{encuesta.fecha.month:02d}"
			if mes_key not in nutrientes_por_mes:
				nutrientes_por_mes[mes_key] = {
					'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
					'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0, 'porciones': 0,
					'total_comensales': 0, 'total_encuestas': 0
				}
			
			print(f"\n--- ENCUESTA {encuesta.id} - {encuesta.fecha} ---")
			
			# Obtener alimentos de esta encuesta
			alimentos_encuesta = AlimentoEncuesta.objects.filter(encuesta=encuesta)
			print(f"Alimentos en encuesta: {alimentos_encuesta.count()}")
			
			# Calcular total de comensales
			total_comensales = encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 + encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
			print(f"Comensales: {total_comensales} (rango1:{encuesta.cantidad_rango_1}, rango2:{encuesta.cantidad_rango_2}, rango3:{encuesta.cantidad_rango_3}, rango4:{encuesta.cantidad_rango_4})")
			
			if total_comensales > 0:
				# Calcular nutrientes por comensal
				nutrientes_por_comensal = {'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
											'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0}
				
				for alimento_encuesta in alimentos_encuesta:
					# Obtener la unidad y su equivalencia en gramos
					unidad = alimento_encuesta.unidad
					cantidad_unidades = float(alimento_encuesta.cantidad)
					
					print(f"  Alimento: {alimento_encuesta.alimento.nombre}")
					print(f"  Cantidad: {cantidad_unidades} {unidad.nombre}")
					print(f"  Equivalencia gramos: {unidad.equivalencia_gramos}")
					print(f"  Equivalencia ml: {unidad.equivalencia_ml}")
					
					# Convertir a gramos usando la equivalencia de la unidad
					if unidad.equivalencia_gramos:
						cantidad_gramos = cantidad_unidades * float(unidad.equivalencia_gramos)
						print(f"  Conversión: {cantidad_unidades} × {unidad.equivalencia_gramos} = {cantidad_gramos}g")
					else:
						# Si no hay equivalencia en gramos, usar ml y asumir densidad 1g/ml
						cantidad_gramos = cantidad_unidades * float(unidad.equivalencia_ml)
						print(f"  Conversión: {cantidad_unidades} × {unidad.equivalencia_ml} = {cantidad_gramos}g (ml)")
					
					# Obtener nutrientes del alimento (por 100g)
					alimento = alimento_encuesta.alimento
					print(f"  Nutrientes por 100g: H:{alimento.hidratos_carbono}, P:{alimento.proteinas}, G:{alimento.grasas}, GT:{alimento.grasas_totales}, E:{alimento.energia}, S:{alimento.sodio}")
					
					# Calcular nutrientes totales de este alimento
					nutrientes_alimento = {
						'hidratos': (float(alimento.hidratos_carbono) * cantidad_gramos) / 100,
						'proteinas': (float(alimento.proteinas) * cantidad_gramos) / 100,
						'grasasSaturadas': (float(alimento.grasas) * cantidad_gramos) / 100,
						'grasasTotales': (float(alimento.grasas_totales) * cantidad_gramos) / 100,
						'kilocalorias': (float(alimento.energia) * cantidad_gramos) / 100,
						'sodio': (float(alimento.sodio) * cantidad_gramos) / 100
					}
					
					print(f"  Nutrientes totales: H:{nutrientes_alimento['hidratos']:.2f}, P:{nutrientes_alimento['proteinas']:.2f}, G:{nutrientes_alimento['grasasSaturadas']:.2f}, GT:{nutrientes_alimento['grasasTotales']:.2f}, E:{nutrientes_alimento['kilocalorias']:.2f}, S:{nutrientes_alimento['sodio']:.2f}")
					
					# Sumar a los nutrientes totales
					for nutriente in nutrientes_por_comensal:
						nutrientes_por_comensal[nutriente] += nutrientes_alimento[nutriente]
				
				print(f"  Nutrientes totales comida: H:{nutrientes_por_comensal['hidratos']:.2f}, P:{nutrientes_por_comensal['proteinas']:.2f}, G:{nutrientes_por_comensal['grasasSaturadas']:.2f}, GT:{nutrientes_por_comensal['grasasTotales']:.2f}, E:{nutrientes_por_comensal['kilocalorias']:.2f}, S:{nutrientes_por_comensal['sodio']:.2f}")
				
				# Dividir por número de comensales para obtener nutrientes por comensal
				for nutriente in nutrientes_por_comensal:
					nutrientes_por_comensal[nutriente] = nutrientes_por_comensal[nutriente] / total_comensales
				
				print(f"  Nutrientes por comensal: H:{nutrientes_por_comensal['hidratos']:.2f}, P:{nutrientes_por_comensal['proteinas']:.2f}, G:{nutrientes_por_comensal['grasasSaturadas']:.2f}, GT:{nutrientes_por_comensal['grasasTotales']:.2f}, E:{nutrientes_por_comensal['kilocalorias']:.2f}, S:{nutrientes_por_comensal['sodio']:.2f}")
				
				# Sumar al mes
				for nutriente in nutrientes_por_mes[mes_key]:
					if nutriente in nutrientes_por_comensal:
						nutrientes_por_mes[mes_key][nutriente] += nutrientes_por_comensal[nutriente]
				
				nutrientes_por_mes[mes_key]['total_comensales'] += total_comensales
				nutrientes_por_mes[mes_key]['total_encuestas'] += 1

		# Calcular promedios por mes
		promedios_mes = []
		print(f"\n=== RESUMEN POR MES ===")
		for mes, datos in nutrientes_por_mes.items():
			if datos['total_encuestas'] > 0:
				promedio = {
					'mes': mes,
					'hidratos': round(datos['hidratos'] / datos['total_encuestas'], 2),
					'proteinas': round(datos['proteinas'] / datos['total_encuestas'], 2),
					'grasasSaturadas': round(datos['grasasSaturadas'] / datos['total_encuestas'], 2),
					'grasasTotales': round(datos['grasasTotales'] / datos['total_encuestas'], 2),
					'kilocalorias': round(datos['kilocalorias'] / datos['total_encuestas'], 2),
					'sodio': round(datos['sodio'] / datos['total_encuestas'], 2),
					'porciones': round(datos['total_comensales'] / datos['total_encuestas'], 2)
				}
				print(f"Mes {mes}: {datos['total_encuestas']} encuestas, {datos['total_comensales']} comensales")
				print(f"  Promedio por comensal: H:{promedio['hidratos']:.2f}, P:{promedio['proteinas']:.2f}, G:{promedio['grasasSaturadas']:.2f}, GT:{promedio['grasasTotales']:.2f}, E:{promedio['kilocalorias']:.2f}, S:{promedio['sodio']:.2f}")
				promedios_mes.append(promedio)
		
		# Ordenar por fecha (mes-año)
		promedios_mes.sort(key=lambda x: x['mes'])
		print(f"\n=== FIN CÁLCULO NUTRICIONAL ===")

		# CÁLCULO PARA ÚLTIMOS 7 DÍAS
		td_7 = timedelta(days=-6)
		fecha_7 = today + td_7
		encuestas_7_dias = Encuesta.objects.filter(
			comedor__in=lc,
			fecha__range=(fecha_7, today)
		).order_by('-fecha')

		# Calcular nutrientes por día
		nutrientes_por_dia = {}
		for encuesta in encuestas_7_dias:
			dia_key = str(encuesta.fecha)
			if dia_key not in nutrientes_por_dia:
				nutrientes_por_dia[dia_key] = {
					'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
					'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0, 'porciones': 0,
					'total_comensales': 0, 'total_encuestas': 0
				}
			
			# Obtener alimentos de esta encuesta
			alimentos_encuesta = AlimentoEncuesta.objects.filter(encuesta=encuesta)
			
			# Calcular total de comensales
			total_comensales = encuesta.cantidad_rango_1 + encuesta.cantidad_rango_2 + encuesta.cantidad_rango_3 + encuesta.cantidad_rango_4
			
			if total_comensales > 0:
				# Calcular nutrientes por comensal
				nutrientes_por_comensal = {'hidratos': 0, 'proteinas': 0, 'grasasSaturadas': 0, 
											'grasasTotales': 0, 'kilocalorias': 0, 'sodio': 0}
				
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
				
				# Sumar al día
				for nutriente in nutrientes_por_dia[dia_key]:
					if nutriente in nutrientes_por_comensal:
						nutrientes_por_dia[dia_key][nutriente] += nutrientes_por_comensal[nutriente]
				
				nutrientes_por_dia[dia_key]['total_comensales'] += total_comensales
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
					'sodio': round(datos['sodio'] / datos['total_encuestas'], 2),
					'porciones': round(datos['total_comensales'] / datos['total_encuestas'], 2)
				}
				promedios_dia.append(promedio)
		
		# Ordenar por fecha (día)
		promedios_dia.sort(key=lambda x: x['dia'])

		response.context_data['promedios_mes'] = promedios_mes
		response.context_data['promedios_dia'] = promedios_dia
		response.context_data['total_reportes'] = encuestas_12_meses.count()

		return response

# admin.site.register(ReporteNutricional, ReporteNutricionalAdmin)  # Oculto el modelo individual
admin.site.register(ReportesNutricionales, ReportesNutricionalesAdmin)
