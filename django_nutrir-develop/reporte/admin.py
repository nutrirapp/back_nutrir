from collections import Counter
from datetime import date, timedelta
from itertools import chain

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum, F, Q
from .models import ReporteNutricional, ReportesGenerales, ReportesRaciones
from django.contrib import admin
from comedor.models import Comedor
from encuesta.models import Encuesta, AlimentoEncuesta
from django.http import QueryDict
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

		if 'organizacion' in get_limpio:
			del get_limpio['organizacion']

		if 'comedor' in get_limpio:
			del get_limpio['comedor']

		if 'tipo_organizacion' in get_limpio:
			del get_limpio['tipo_organizacion']

		request.GET = get_limpio

		response = super().changelist_view(
			request,
			extra_context=extra_context,
		)

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
		# response = super().changelist_view(
		# 	request,
		# 	extra_context=extra_context,
		# )

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


		# - filtros Reportes por racion por organizcion/ comedores
		organizaciones_dict = {}
		comedores_por_organizacion = []

		for comedor in comedores_permitidos.select_related(
				'organizacion_regional',
				'organizacion_regional__organizacion_superior'
		):
			organizacion_hija = comedor.organizacion_regional

			if not organizacion_hija:
				continue

			organizacion_padre = organizacion_hija.organizacion_superior

			if organizacion_hija.es_organizacion_regional and organizacion_padre:
				organizaciones_dict[organizacion_padre.id] = {
					'id': organizacion_padre.id,
					'nombre': organizacion_padre.nombre,
					'tipo': 'padre',
					'padre_id': '',
				}

				organizaciones_dict[organizacion_hija.id] = {
					'id': organizacion_hija.id,
					'nombre': organizacion_hija.nombre,
					'tipo': 'hija',
					'padre_id': organizacion_padre.id,
				}

				comedores_por_organizacion.append({
					'id': comedor.id,
					'nombre': comedor.nombre,
					'organizacion_hija_id': organizacion_hija.id,
					'organizacion_padre_id': organizacion_padre.id,
				})

			else:
				organizaciones_dict[organizacion_hija.id] = {
					'id': organizacion_hija.id,
					'nombre': organizacion_hija.nombre,
					'tipo': 'padre',
					'padre_id': '',
				}

				comedores_por_organizacion.append({
					'id': comedor.id,
					'nombre': comedor.nombre,
					'organizacion_hija_id': organizacion_hija.id,
					'organizacion_padre_id': organizacion_hija.id,
				})

		organizaciones = sorted(
			organizaciones_dict.values(),
			key=lambda organizacion: (
				str(organizacion['padre_id']),
				organizacion['tipo'],
				organizacion['nombre']
			)
		)

		# Buscar nombre de organizacoin/comedor
		nombre_organizacion_seleccionada = None

		if organizacion_seleccionada:
			for organizacion in organizaciones:
				if str(organizacion['id']) == str(organizacion_seleccionada):
					nombre_organizacion_seleccionada = organizacion['nombre']
					break

		nombre_comedor_seleccionado = None

		if comedor_seleccionado:
			for comedor in comedores_por_organizacion:
				if str(comedor['id']) == str(comedor_seleccionado):
					nombre_comedor_seleccionado = comedor['nombre']
					break
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
			lc = comedores_permitidos.filter(
				organizacion_regional_id=organizacion_seleccionada
			)

		# Encuestas de los ultimos 12 meses ----------------------------------------------------------------------------

		today = date.today()
		td = relativedelta(months=-11)
		fecha = today + td
		fecha_limite = date(day=1, month=fecha.month, year=fecha.year)

		r_mes_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(fecha_limite, today))

		# Cantidad de raciones por mes de los ultimos 12 meses
		cantidad_raciones_meses = r_mes_total.values('fecha__year', 'fecha__month', 'cantidad_rango_1', 'cantidad_rango_2', 'cantidad_rango_3', 'cantidad_rango_4')
		cantidad_raciones_meses = cantidad_raciones_meses.values('fecha__year', 'fecha__month').annotate(cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))).order_by('fecha__year', 'fecha__month')
		response.context_data['raciones_mes'] = cantidad_raciones_meses

		# Cantidad de raciones por funcionamiento de los ultimos 12 meses
		cantidad_raciones_funcionamiento_meses = r_mes_total.values('fecha__year', 'fecha__month', 'cantidad_rango_1', 'cantidad_rango_2', 'cantidad_rango_3', 'cantidad_rango_4', 'funcionamiento')
		cantidad_raciones_funcionamiento_meses = cantidad_raciones_funcionamiento_meses.values('fecha__year', 'fecha__month', 'funcionamiento').annotate(cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4')))
		response.context_data['raciones_mes_funcionamiento'] = cantidad_raciones_funcionamiento_meses

		# Cantidad de raciones por rango etario de los ultimos 12 meses
		cantidad_raciones_rango_etario_meses = r_mes_total.values('fecha__year', 'fecha__month', 'cantidad_rango_1', 'cantidad_rango_2', 'cantidad_rango_3', 'cantidad_rango_4')
		cantidad_raciones_rango_etario_meses = cantidad_raciones_rango_etario_meses.values('fecha__year', 'fecha__month').annotate(cantidad_rango_1=Sum(F('cantidad_rango_1')), cantidad_rango_2=Sum(F('cantidad_rango_2')), cantidad_rango_3=Sum(F('cantidad_rango_3')), cantidad_rango_4=Sum(F('cantidad_rango_4')))
		response.context_data['raciones_mes_rango_etario'] = cantidad_raciones_rango_etario_meses

		# Cantidad de raciones por comida de los ultimos 12 meses
		# distinct() por (encuesta_id, comida) evita que múltiples ingredientes inflen el conteo
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
				comida_mes_map[key] = {
					'encuesta__fecha__year': ae['encuesta__fecha__year'],
					'encuesta__fecha__month': ae['encuesta__fecha__month'],
					'comida__nombre': ae['comida__nombre'],
					'cantidad': 0,
				}
			comida_mes_map[key]['cantidad'] += raciones

		cantidad_raciones_comida_meses = list(comida_mes_map.values())
		comidas = set(r['comida__nombre'] for r in cantidad_raciones_comida_meses)
		fechas_bd = set((r['encuesta__fecha__month'], r['encuesta__fecha__year']) for r in cantidad_raciones_comida_meses)
		agregar = []
		fechas = []
		for f in fechas_bd:
			fechas.append(str(f[0])+'/'+str(f[1]))
			for c in comidas:
				if not any(r['comida__nombre'] == c and r['encuesta__fecha__month'] == f[0] and r['encuesta__fecha__year'] == f[1] for r in cantidad_raciones_comida_meses):
					agregar.append({'comida__nombre': c, 'encuesta__fecha__month': f[0], 'encuesta__fecha__year': f[1], 'cantidad': 0})
		cantidad_raciones_comida_meses = cantidad_raciones_comida_meses + agregar
		cantidad_raciones_comida_meses.sort(key=self.getComidaMesAño)
		fechas.sort(key=self.getAñoMes)
		response.context_data['raciones_comida_mes'] = cantidad_raciones_comida_meses
		response.context_data['fechas_mes'] = fechas

		# Encuestas de los ultimos 30 dias -----------------------------------------------------------------------------

		today = date.today()
		td = timedelta(29)
		raciones_30_dias_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(today - td, today))
		raciones_30_dias_total = raciones_30_dias_total.values('fecha').annotate(cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4'))).order_by('fecha')
		response.context_data['raciones_dia'] = raciones_30_dias_total

		# Cantidad de raciones de los ultimos 7 dias -------------------------------------------------------------------

		today = date.today()
		td = timedelta(6)
		fecha = today - td
		r_semana_total = Encuesta.objects.filter(comedor__in=lc, fecha__range=(fecha, today))

		# Cantidad de raciones por funcionamiento de los ultimos 7 dias

		cantidad_raciones_funcionamiento_dias = r_semana_total.values('fecha', 'cantidad_rango_1', 'cantidad_rango_2', 'cantidad_rango_3', 'cantidad_rango_4', 'funcionamiento')
		cantidad_raciones_funcionamiento_dias = cantidad_raciones_funcionamiento_dias.values('fecha', 'funcionamiento').annotate(cantidad=Sum(F('cantidad_rango_1') + F('cantidad_rango_2') + F('cantidad_rango_3') + F('cantidad_rango_4')))
		response.context_data['raciones_semana_funcionamiento'] = cantidad_raciones_funcionamiento_dias

		# Cantidad de raciones por rango etario de los ultimos 7 dias
		cantidad_raciones_rango_etario_dias = r_semana_total.values('fecha', 'cantidad_rango_1', 'cantidad_rango_2', 'cantidad_rango_3', 'cantidad_rango_4')
		cantidad_raciones_rango_etario_dias = cantidad_raciones_rango_etario_dias.values('fecha').annotate(cantidad_rango_1=Sum(F('cantidad_rango_1')), cantidad_rango_2=Sum(F('cantidad_rango_2')), cantidad_rango_3=Sum(F('cantidad_rango_3')), cantidad_rango_4=Sum(F('cantidad_rango_4')))
		response.context_data['raciones_semana_rango_etario'] = cantidad_raciones_rango_etario_dias

		# Cantidad de raciones por comida de los ultimos 7 dias
		# distinct() por (encuesta_id, comida) evita que múltiples ingredientes inflen el conteo
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
				comida_dia_map[key] = {
					'encuesta__fecha': ae['encuesta__fecha'],
					'comida__nombre': ae['comida__nombre'],
					'cantidad': 0,
				}
			comida_dia_map[key]['cantidad'] += raciones

		cantidad_raciones_comida_dias = sorted(comida_dia_map.values(), key=lambda x: x['encuesta__fecha'])
		comidas = set(r['comida__nombre'] for r in cantidad_raciones_comida_dias)
		fechas = set(r['encuesta__fecha'] for r in cantidad_raciones_comida_dias)
		agregar = []
		for f in fechas:
			for c in comidas:
				if not any(r['comida__nombre'] == c and r['encuesta__fecha'] == f for r in cantidad_raciones_comida_dias):
					agregar.append({'comida__nombre': c, 'encuesta__fecha': f, 'cantidad': 0})
		cantidad_raciones_comida_dias = cantidad_raciones_comida_dias + agregar
		cantidad_raciones_comida_dias.sort(key=self.getComidaFecha)
		response.context_data['raciones_comida_semana'] = cantidad_raciones_comida_dias
		response.context_data['fechas_semana'] = fechas

		return response

admin.site.register(ReportesGenerales, ReportesGeneralesAdmin)
admin.site.register(ReportesRaciones, ReportesRacionesAdmin)


class ReporteNutricionalAdmin(admin.ModelAdmin):
	list_display = ['fecha', 'comedor', 'organizacion', 'encuesta']
	search_fields = ('comedor',)
	list_filter=('fecha','organizacion','comedor')

admin.site.register(ReporteNutricional, ReporteNutricionalAdmin)
