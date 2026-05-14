from django.urls import path, include, re_path
from .views import RacionesMesViewList, RacionesSemanaViewList, ComidasMesViewList, ComidasSemanaViewList, ReportesNutricionalesMesViewList, ReportesNutricionalesSemanaViewList, export_detailed_raciones_csv

urlpatterns = [
	re_path('racion_mes/(?P<comedor>.+)/$', RacionesMesViewList.as_view(), name='racion-mes'),
	re_path('racion_semana/(?P<comedor>.+)/$', RacionesSemanaViewList.as_view(), name='racion-semana'),
	re_path('comida_mes/(?P<comedor>.+)/$', ComidasMesViewList.as_view(), name='comida-mes'),
	re_path('comida_semana/(?P<comedor>.+)/$', ComidasSemanaViewList.as_view(), name='comida-semana'),
	re_path('nutricional_mes/(?P<comedor>.+)/$', ReportesNutricionalesMesViewList.as_view(), name='nutricional-mes'),
	re_path('nutricional_semana/(?P<comedor>.+)/$', ReportesNutricionalesSemanaViewList.as_view(), name='nutricional-semana'),
	path('export_detailed_raciones_csv/', export_detailed_raciones_csv, name='export-detailed-raciones-csv'),
]
