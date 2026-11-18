from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin      # exige sesión
from django.contrib.messages.views import SuccessMessageMixin  # mensaje de éxito automático
from django.db.models import ProtectedError
from django.shortcuts import redirect,render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView   # las 5 genéricas

from .forms import MarcaForm, ProductoForm
from .mixins import UsuarioRegistroMixin
from .models import Marca, Producto                               # Nuestro modelo


# =====================================================================
# MARCAS · Vistas Basadas en Funciones (VBF)
# =====================================================================

def marca_lista(request):                                  # READ: muestra todas las marcas
    q = request.GET.get("q", "") #                         # 1. Leemos el buscador: /facturacion/marcas/?q=sam (si no hay, queda "")
    marcas = Marca.objects.all()                          # 2. Pedimos todas las marcas a la base de datos

    if q:                                                  # 3. Si el usuario escribió algo en el buscador...
        marcas = marcas.filter(nombre__icontains=q)        #    ...dejamos solo las que contienen ese texto

    contexto = {                                           # 4. Datos que enviamos al template
        "titulo": "Marcas",                                #    → {{ titulo }}
        "marcas": marcas,                                  #    → {% for marca in marcas %}
        "q": q,                                            #    → para que el buscador no se borre
    }
    return render(request, "facturacion/marca_lista.html", contexto)   # 5. Mostramos la página

def marca_crear(request):                                  # CREATE: crear una marca nueva

    if request.method == "POST":                           # ¿El usuario presionó "Guardar"? (llegó por POST)
        form = MarcaForm(request.POST)                     # 1. Llenamos el formulario con lo que escribió
        if form.is_valid():                                # 2. ¿Los datos están bien? (obligatorios, únicos, clean_nombre)
            marca = form.save()                            # 3. Guardamos en la base de datos (save devuelve la marca)
            messages.success(request, f"Marca «{marca.nombre}» creada correctamente.")   # 4. Mensaje verde
            return redirect("facturacion:marca_lista")     # 5. Vamos a la lista. Así, si recarga, no se guarda dos veces
        # Si NO es válido, no entra al if: baja hasta el render y muestra el formulario CON errores

    else:                                                  # Si llegó por GET (solo abrió la página)...
        form = MarcaForm()                                 # ...creamos un formulario vacío

    contexto = {                                           # Datos para el template
        "titulo": "Nueva marca",                           # Título de la página
        "form": form,                                      # El formulario (vacío o con errores)
        "boton": "Guardar",                                # Texto del botón
    }
    return render(request, "facturacion/marca_form.html", contexto)



def marca_editar(request, pk):                             # UPDATE. pk llega desde la URL: /marcas/editar/3/ → pk=3
    marca = get_object_or_404(Marca, pk=pk)   
    #marca = Marca.objects.get(id=pk)             # 1. Buscamos la marca. Si no existe → página 404

    if request.method == "POST":                           # 2. ¿Presionó "Actualizar"?
        form = MarcaForm(request.POST, instance=marca)     #    Datos nuevos + la marca que vamos a cambiar
        if form.is_valid():                                #    ¿Están bien?
            form.save()                                    #    Actualiza (UPDATE), no crea una nueva
            messages.success(request, f"Marca «{marca.nombre}» actualizada.")
            return redirect("facturacion:marca_lista")     #    Volvemos a la lista
    else:                                                  # 3. Llegó por GET...
        form = MarcaForm(instance=marca)                   #    ...formulario lleno con los datos actuales

    contexto = {
        "titulo": f"Editar marca: {marca.nombre}",
        "form": form,
        "boton": "Actualizar",
    }
    return render(request, "facturacion/marca_form.html", contexto)   # ¡El mismo template de crear!



def marca_eliminar(request, pk):                           # DELETE
    marca = get_object_or_404(Marca, pk=pk)                # Buscamos la marca o mostramos 404

    if request.method == "POST":                           # ¿Presionó "Sí, eliminar"?
        try:                                               # Intentamos borrar...
            nombre = marca.nombre                          # Guardamos el nombre para el mensaje
            marca.delete()                                 # DELETE en la base de datos
            messages.success(request, f"Marca «{nombre}» eliminada.")
        except ProtectedError:                             # ...si tiene productos, PROTECT no deja borrarla
            messages.error(request, f"No se puede eliminar «{marca.nombre}» porque tiene productos. Desactívala en su lugar.")
        return redirect("facturacion:marca_lista")         # En los dos casos volvemos a la lista

    # Si llegó por GET: mostramos la pregunta "¿Seguro?"
    contexto = {"titulo": "Eliminar marca", "marca": marca}
    return render(request, "facturacion/marca_eliminar.html", contexto)

class ProductoListView(LoginRequiredMixin, ListView):     # LISTAR
    model = Producto                                       # ¿qué tabla?
    template_name = "facturacion/producto_lista.html"      # ¿qué HTML?
    context_object_name = "productos"                      # nombre de la lista en el HTML
    paginate_by = 5                                        # 5 por página → envía page_obj
    extra_context = {"titulo": "Productos"}                # datos fijos extra para el HTML

    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        productos = super().get_queryset()                 # lo normal: Producto.objects.all()
        productos = productos.select_related("marca").prefetch_related("categorias")   # menos consultas
        q = self.request.GET.get("q", "")                  # buscador: ?q=galaxy
        if q:
            productos = productos.filter(nombre__icontains=q)
        return productos

    def get_context_data(self, **kwargs):                  # ¿qué datos EXTRA recibe el HTML?
        contexto = super().get_context_data(**kwargs)      # lo que ListView ya armó
        contexto["q"] = self.request.GET.get("q", "")      # + lo buscado
        return contexto
    
class ProductoCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Producto
    form_class = ProductoForm                              # nuestro formulario
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")   # a dónde ir al guardar
    success_message = "Producto «%(nombre)s» creado."      # %(nombre)s = el campo nombre del formulario
    extra_context = {"titulo": "Nuevo producto", "boton": "Guardar"}
    
class ProductoUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"       # el mismo template de crear
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto «%(nombre)s» actualizado."
    extra_context = {"titulo": "Editar producto", "boton": "Actualizar"}

    def form_invalid(self, form):                          # cuando hay errores (POST inválido)
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)                  # vuelve a mostrar el formulario
    
class ProductoDetailView(LoginRequiredMixin, DetailView):  # VER UNO
    model = Producto
    template_name = "facturacion/producto_detalle.html"
    context_object_name = "producto"
    
class ProductoDeleteView(LoginRequiredMixin, DeleteView):  # ELIMINAR
    model = Producto
    template_name = "facturacion/producto_eliminar.html"
    context_object_name = "producto"
    success_url = reverse_lazy("facturacion:producto_lista")

    def form_valid(self, form):                            # se ejecuta al confirmar (POST)
        nombre = self.object.nombre                        # self.object = el producto a eliminar
        try:
            respuesta = super().form_valid(form)           # DELETE + redirect
        except ProtectedError:                             # ya está en una venta o compra (PROTECT)
            messages.error(self.request, f"No se puede eliminar «{nombre}»: ya tiene ventas o compras. Desactívalo.")
            return redirect("facturacion:producto_lista")
        messages.success(self.request, f"Producto «{nombre}» eliminado.")
        return respuesta
    