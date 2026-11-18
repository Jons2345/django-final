from django.urls import path               # path() une una dirección con una vista
from . import views                        # Las vistas de ESTA app (facturacion/views.py)

app_name = "facturacion"                   # "Apellido" de las URLs de esta app. En templates: 'facturacion:marca_lista'

urlpatterns = [
    # ---------- MARCAS: funciones (VBF) ----------
    path("marcas/", views.marca_lista, name="marca_lista"),   # /facturacion/marcas/ → vista marca_lista
    # En los pasos siguientes agregarás aquí crear, editar y eliminar
    path("marcas/crear/", views.marca_crear, name="marca_crear"),   # /facturacion/marcas/crear/
       # <int:pk> captura el número de la URL y se lo pasa a la vista como parámetro pk
    path("marcas/editar/<int:pk>/", views.marca_editar, name="marca_editar"),
    path("marcas/eliminar/<int:pk>/", views.marca_eliminar, name="marca_eliminar"),
    # ---------- PRODUCTOS: clases (VBC) ----------
    path("productos/", views.ProductoListView.as_view(), name="producto_lista"),   # .as_view(): obligatorio en clases
    path("productos/crear/", views.ProductoCreateView.as_view(), name="producto_crear"),
    path("productos/editar/<int:pk>/", views.ProductoUpdateView.as_view(), name="producto_editar"),   # pk → get_object()
    path("productos/<int:pk>/", views.ProductoDetailView.as_view(), name="producto_detalle"),
    path("productos/eliminar/<int:pk>/", views.ProductoDeleteView.as_view(), name="producto_eliminar"),
    
    
    
]