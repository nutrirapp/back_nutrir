from django.shortcuts import render
from rest_framework import generics
from datetime import date, timedelta
from .serializers import ComedorListaSerializer, ComedorListaLabelSerializer
from encuesta.models import Encuesta, AlimentoEncuesta
from django.db.models import Count, Sum, F, Q
from django.http import JsonResponse
import csv

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
	cantidad_raciones_comida_dias = AlimentoEncuesta.objects.select_related('encuesta').filter(
		encuesta__fecha__range=(fecha_inicio, fecha_fin), encuesta__comedor=comedor).values('encuesta__fecha',
																					  'encuesta__cantidad_rango_1',
																					  'encuesta__cantidad_rango_2',
																					  'encuesta__cantidad_rango_3',
																					  'encuesta__cantidad_rango_4',
																					  'comida')
	cantidad_raciones_comida_dias = cantidad_raciones_comida_dias.values('encuesta__fecha',
																		 'comida__nombre').annotate(cantidad=Sum(
		F('encuesta__cantidad_rango_1') + F('encuesta__cantidad_rango_2') + F('encuesta__cantidad_rango_3') + F(
			'encuesta__cantidad_rango_4'))).order_by('encuesta__fecha')
	comidas = set(cantidad_raciones_comida_dias.values_list('comida__nombre', flat=True))
	fechas = set(cantidad_raciones_comida_dias.values_list('encuesta__fecha', flat=True))
	agregar = []
	for f in fechas:
		for c in comidas:
			t = cantidad_raciones_comida_dias.filter(comida__nombre=c, encuesta__fecha=f)
			if not t:
				agregar.append({'comida__nombre': c, 'encuesta__fecha': f, 'cantidad': 0})
	cantidad_raciones_comida_dias = list(cantidad_raciones_comida_dias) + agregar
	cantidad_raciones_comida_dias.sort(key=getComidaFecha)
	i = 0
	m = []
	comida_semana = []
	comida = ""

	for r in cantidad_raciones_comida_dias:
		while i < 1:
			comida = r['comida__nombre']
			i = 1
		if r['comida__nombre'] == comida:
			m.append(r['cantidad'])
		else:
			comida_semana.append({
				'label': comida,
				'data': m,
			})
			comida = r['comida__nombre']
			m = []
			m.append(r['cantidad'])

	if comida != "":
		comida_semana.append({
			'label': comida,
			'data': m,
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

