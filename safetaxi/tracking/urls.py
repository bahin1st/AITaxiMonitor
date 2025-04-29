from django.urls import path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('map_monitor', views.taxi_map, name='map_monitor'),
    path('',views.home, name='home'),
    path('api/taxis/', views.get_taxis, name='get_taxis'),
    path('register/', views.register_view, name='register'),

#    path('driver_dashboard/realtime/<str:driver_name>/', views.driver_dashboard, name='driver_dashboard'),
    # path('driver_search/', views.driver_search, name='driver_search'),
    path('driver/<str:username>/', views.driver_navigation_dashboard, name="driver_navigation_dashboard"),
    path('api/anomalies/<str:ride_name>/', views.get_ride_anomalies, name='get_ride_anomalies'),
    path('telegram/webhook/', views.telegram_webhook, name='telegram_webhook'),
    path('start-simulation/', views.start_simulation, name='start-simulation'),
    # path('copy-anomalies/', views.copy_anomalies_to_daily_weekly, name='copy_anomalies'),
    path('cleanup-anomalies/', views.cleanup_anomalies, name='cleanup_anomalies'),
    path("trip-anomalies/", views.trip_anomalies, name="trip_anomalies"),

    path('rate-trip/', views.rate_trip, name='rate_trip'),
    path('driver_profile/<str:username>/', views.driver_profile, name='driver_profile'),
    path('trips/<str:tripName>/details/', views.trip_detail_view, name='trip_detail_view'),
    path('update_driver_info/<str:username>/', views.update_driver_info, name='update_driver_info'),
    path("general_monitor/", views.general_monitor, name="dashboard"),
    path('generate-dataset/', views.generate_dataset_view, name='generate_dataset'),
    path('driver_details/<str:username>/', views.driver_details, name="driver_details"),
    path("report-endangered/", views.report_endangered_passenger, name="report_endangered"),
    

    
    ## apies to pass info fo llM
    path('driver/<str:username>/summarize/', views.summarize_driver, name='summarize_driver'),
    path('trip/summarize/', views.trip_summary, name='trip_summary')

]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)