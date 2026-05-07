from django.shortcuts import render
from rest_framework import generics
from datetime import date, timedelta
from .serializers import ComedorListaSerializer, ComedorListaLabelSerializer
from encuesta.models import Encuesta, AlimentoEncuesta
from django.db.models import Count, Sum, F, Q
from django.http import JsonResponse,HttpResponse
from django.db import connection
import csv
from dateutil.relativedelta import relativedelta
from comedor.models import Comedor
from comida.models import Comida
from responsable_organizacion.models import ResponsableOrganizacion
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



#--------logica generar cvs----------
def getMesAñoComida(e):
    mes = e['mes']
    if mes < 10:
        mes = '0' + str(mes)
    else:
        mes = str(mes)
    return str(e['año']) + ' ' + mes + ' ' + e['comida']

def getAñoMes(e):
    e = e.split('/')
    mes = e[0]
    if int(mes) < 10:
        mes = '0' + str(mes)
    else:
        mes = str(mes)
    return e[1] + ' ' + mes

def getComidaMesAño(e):
    mes = e['encuesta__fecha__month']
    if mes < 10:
        mes = '0' + str(mes)
    else:
        mes = str(mes)
    return e['comida__nombre'] + ' ' + str(e['encuesta__fecha__year']) + ' ' + mes

def getFechaComida(e):
    return str(e['fecha'].year)+str(e['fecha'].month)+str(e['fecha'].day) + ' ' + e['comida']

# --- Vista para exportar el CSV detallado ---
def export_detailed_raciones_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_raciones_detallado.csv"'

    writer = csv.writer(response)

    # Cabeceras del CSV
    writer.writerow([
        'Fecha', 'Organizacion', 'Comedor', 'Comida', 'Tipo de Comida',
        'Cantidad Raciones', 'Hidratos (g)', 'Proteina (g)', 'Grasas Saturadas (g)',
        'Grasas Totales (g)', 'Sodio (g)', 'Kilocalorias'
    ])

    # --- Replicar la lógica de filtrado de comedores de ReportesRacionesAdmin.changelist_view ---
    organizacion_seleccionada = request.GET.get('organizacion')
    comedor_seleccionado = request.GET.get('comedor')
    tipo_organizacion_seleccionada = request.GET.get('tipo_organizacion')

    # Obtener comedores permitidos para el usuario (similar a changelist_view)
    r = ResponsableOrganizacion.objects.filter(responsable=request.user).values('organizacion')
    if (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        comedores_permitidos = Comedor.objects.all()
    else:
        comedores_permitidos = Comedor.objects.filter(
            Q(responsable_comedor=request.user) |
            Q(organizacion_regional__in=r) |
            Q(organizacion_regional__organizacion_superior__in=r)
        )

    lc = comedores_permitidos # Inicialmente, todos los permitidos

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
    # --- Fin de la replicación de lógica de filtrado ---

    # --- Lógica de filtrado por rango de fechas ---
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    if fecha_inicio_str and fecha_fin_str:
        try:
            fecha_inicio = date.fromisoformat(fecha_inicio_str)
            fecha_fin = date.fromisoformat(fecha_fin_str)

            # Validación backend del rango de 3 meses
            max_fecha_fin_permitida = fecha_inicio + relativedelta(months=3) - timedelta(days=1)

            if fecha_fin > max_fecha_fin_permitida:
                fecha_fin = max_fecha_fin_permitida

            # Asegurar que fecha_inicio no sea posterior a fecha_fin
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
        'encuesta',
        'encuesta__comedor',
        'encuesta__comedor__organizacion_regional',
        'encuesta__comedor__organizacion_regional__organizacion_superior',
        'comida',
        'alimento',
    ).order_by(
        'encuesta__fecha',
        'encuesta__comedor__nombre',
        'comida__nombre'
    )

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

    # Obtener horarios desde comida_comida_horarios / comida_horario (M2M en la DB)
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
            encuesta.cantidad_rango_1 +
            encuesta.cantidad_rango_2 +
            encuesta.cantidad_rango_3 +
            encuesta.cantidad_rango_4
        )

        total_hidratos = 0
        total_proteina = 0
        total_grasas_sat = 0
        total_grasas_tot = 0
        total_sodio_mg = 0
        total_kcal = 0

        for ae in data['ingredientes']:
            alimento = ae.alimento
            # factor = cuántas porciones de referencia se usaron
            porcion = alimento.cantidad_porcion if alimento.cantidad_porcion else 1
            factor = ae.cantidad / porcion

            total_hidratos += alimento.hidratos_carbono * factor
            total_proteina += alimento.proteinas * factor
            total_grasas_sat += alimento.grasas * factor
            total_grasas_tot += alimento.grasas_totales * factor
            total_sodio_mg += alimento.sodio * factor  # sodio cargado en mg en la BD
            total_kcal += alimento.energia * factor

        org = encuesta.comedor.organizacion_regional
        if org and org.es_organizacion_regional and org.organizacion_superior:
            org_nombre = org.organizacion_superior.nombre
        elif org:
            org_nombre = org.nombre
        else:
            org_nombre = ''

        tipo_comida = comida_horario_map.get(comida.id, comida.get_horario_display() or '-')

        writer.writerow([
            encuesta.fecha.strftime('%d/%m/%Y'),
            org_nombre,
            encuesta.comedor.nombre,
            comida.nombre,
            tipo_comida,
            f"{total_raciones:.0f}",
            f"{total_hidratos:.2f}",
            f"{total_proteina:.2f}",
            f"{total_grasas_sat:.2f}",
            f"{total_grasas_tot:.2f}",
            f"{total_sodio_mg / 1000:.2f}",  # mg → g
            f"{total_kcal:.2f}",
        ])

    return response

#-------------------------------