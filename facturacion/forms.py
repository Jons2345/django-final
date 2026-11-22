from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from .models import Marca, Producto, Venta, DetalleVenta, Categoria, Cliente, Proveedor, Compra, DetalleCompra, Perfil                     # El modelo del que sale el formulario


class MarcaForm(forms.ModelForm):                # ModelForm: formulario construido desde un modelo, 

    class Meta:                                  # Configuración del formulario
        model = Marca                            # ¿De qué modelo sale? De Marca
        fields = ["nombre", "pais_origen", "activo"]   # ¿Qué campos muestra y en qué orden?
        labels = {                               # Cambia el texto de la etiqueta de un campo
            "nombre": "Nombre de la marca",
        }
        widgets = {                              # widgets: CÓMO se dibuja cada campo en HTML
            # TextInput = <input type="text">. attrs agrega atributos HTML: aquí la clase de Bootstrap
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Samsung"}),
            "pais_origen": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Corea del Sur"}),
            # CheckboxInput = <input type="checkbox">. form-check-input es la clase de Bootstrap para casillas
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
   
    def clean_nombre(self):                      # Validación propia del campo "nombre" (clean_ + nombre del campo)
        nombre = self.cleaned_data["nombre"].strip()   # cleaned_data: los datos ya revisados. strip quita espacios
        if len(nombre) < 2:                      # Si tiene menos de 2 letras...
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")  # ...error en rojo bajo el campo
        return nombre.title()  
    
                 # Si está bien, lo devolvemos con la Primera Letra Mayúscula """



class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # user, fecha_creacion y fecha_modificacion NO van: los llena el sistema
        fields = ["nombre", "descripcion", "marca", "categorias", "precio", "stock", "imagen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Galaxy A55"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "marca": forms.Select(attrs={"class": "form-select"}),                         # 1:N → una opción
            "categorias": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),  # N:M → varias
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            # ClearableFileInput = <input type="file"> + casilla "Limpiar" para quitar la foto actual
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = Marca.objects.filter(activo=True)   # solo marcas activas
        self.fields["marca"].empty_label = "— Elige una marca —"

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio
 
 
# =====================================================================
# VENTA: cabecera (maestro)
# =====================================================================
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "fecha_hora", "tipo_pago"]   # subtotal, iva y total los calcula el sistema
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            # type="datetime-local" → el navegador muestra un calendario con hora
            "fecha_hora": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"},
                                              format="%Y-%m-%dT%H:%M"),
            "tipo_pago": forms.Select(attrs={"class": "form-select"}),   # las opciones salen de TipoPago
        } 
 
    
# =====================================================================
# VENTA: filas del detalle
# =====================================================================
class ProductoConPrecioField(forms.ModelChoiceField):
    """Lista desplegable de productos que muestra también el precio y el stock."""
    def label_from_instance(self, obj):           # Django llama a este método para escribir cada <option>
        return f"{obj.nombre} · ${obj.precio} · stock: {obj.stock}"


class DetalleVentaForm(forms.ModelForm):
    producto = ProductoConPrecioField(
        queryset=Producto.objects.filter(activo=True),
        empty_label="— Elige un producto —",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad"]           # el precio NO: lo pone la vista con el precio actual
        widgets = {"cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"})}
        

class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Validación de TODAS las filas juntas: ¿hay stock para lo que se pide?"""

    def clean(self):
        super().clean()                           # primero las validaciones normales de cada fila
        if any(self.errors):                      # si alguna fila ya tiene errores, no seguimos
            return

        pedido = {}                               # {producto: cantidad total pedida}
        for fila in self.forms:
            datos = fila.cleaned_data
            if not datos or datos.get("DELETE"):  # fila vacía o marcada para quitar → se ignora
                continue
            producto = datos["producto"]
            pedido[producto] = pedido.get(producto, 0) + datos["cantidad"]   # suma si el producto se repite

        anterior = {}                             # al EDITAR: lo que esta venta ya tenía reservado
        if self.instance.pk:
            for detalle in self.instance.detalles.all():
                anterior[detalle.producto_id] = anterior.get(detalle.producto_id, 0) + detalle.cantidad

        for producto, cantidad in pedido.items():
            disponible = producto.stock + anterior.get(producto.pk, 0)
            if cantidad > disponible:
                raise ValidationError(
                    f"Stock insuficiente de «{producto.nombre}»: pides {cantidad} y hay {disponible}."
                )
                
# inlineformset_factory crea una CLASE de formset: muchos DetalleVentaForm unidos a UNA Venta
DetalleVentaFormSet = inlineformset_factory(
    Venta,                                        # el maestro
    DetalleVenta,                                 # el detalle (tiene la ForeignKey venta)
    form=DetalleVentaForm,                        # el formulario de cada fila
    formset=BaseDetalleVentaFormSet,              # nuestra validación de stock
    extra=0,                                      # filas vacías extra (las agrega el botón con JavaScript)
    min_num=1,                                    # mínimo 1 fila...
    validate_min=True,                            # ...y se valida que exista
    can_delete=True,                              # cada fila tiene la casilla "Quitar"
)


class CategoriaForm(forms.ModelForm):
 class Meta:                                  
        model = Categoria                            
        fields = ["nombre", "descripcion", "activo"]
        labels = {                              
            "nombre": "Nombre de la categoria",
        }
        widgets = {                              
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: fruta"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }        
        
        
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["cedula", "nombres", "apellidos", "email", "telefono", "direccion"]
        widgets = {
            "cedula": forms.TextInput(attrs={"class": "form-control", "maxlength": "10", "placeholder": "10 dígitos"}),
            "nombres": forms.TextInput(attrs={"class": "form-control"}),
            "apellidos": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_cedula(self):
        """Regla de la cédula: exactamente 10 caracteres y solo números."""
        cedula = self.cleaned_data["cedula"].strip()     
        if len(cedula) != 10:
            raise forms.ValidationError("La cédula debe tener exactamente 10 dígitos.")
        if not cedula.isdigit():                        
            raise forms.ValidationError("La cédula solo puede tener números.")
        return cedula                                     



class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "apellido", "ruc", "email", "contacto", "logo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "apellido": forms.TextInput(attrs={"class": "form-control"}),
            "ruc": forms.TextInput(attrs={"class": "form-control", "maxlength": "13", "placeholder": "13 dígitos, termina en 001"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "contacto": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean_ruc(self):
        """Regla del RUC de Ecuador: 13 dígitos, solo números y termina en 001."""
        ruc = self.cleaned_data["ruc"].strip()
        if len(ruc) != 13 or not ruc.isdigit():
            raise forms.ValidationError("El RUC debe tener exactamente 13 números.")
        if not ruc.endswith("001"):                      
            raise forms.ValidationError("El RUC debe terminar en 001.")
        return ruc


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["proveedor", "fecha_hora", "tipo_pago"] 
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "fecha_hora": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"},
                                              format="%Y-%m-%dT%H:%M"),
            "tipo_pago": forms.Select(attrs={"class": "form-select"}),
        }

class DetalleCompraForm(forms.ModelForm):
    producto = ProductoConPrecioField(
        queryset=Producto.objects.all(),
        empty_label="— Elige un producto —",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DetalleCompra
        fields = ["producto", "cantidad", "precio"]
        widgets = {
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
        }

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El costo debe ser mayor que 0.")
        return precio


class BaseDetalleCompraFormSet(BaseInlineFormSet):
    """
    Validación de TODAS las filas juntas.
    Al CREAR no hace falta revisar stock: comprar siempre SUBE el stock.
    Al EDITAR (reto): primero se quita lo que la compra había metido y luego se mete lo nuevo.
    Si de esas unidades ya se vendió una parte, el stock final podría quedar NEGATIVO. Lo impedimos.
    """

    def clean(self):
        super().clean()                          
        if any(self.errors) or not self.instance.pk:  
            return

        nuevo = {}                              
        for fila in self.forms:
            datos = fila.cleaned_data
            if not datos or datos.get("DELETE"):
                continue
            pid = datos["producto"].pk
            nuevo[pid] = nuevo.get(pid, 0) + datos["cantidad"]

        anterior = {}                            
        for detalle in self.instance.detalles.all():
            anterior[detalle.producto_id] = anterior.get(detalle.producto_id, 0) + detalle.cantidad

        for pid, cantidad_anterior in anterior.items():
            producto = Producto.objects.get(pk=pid)
            final = producto.stock - cantidad_anterior + nuevo.get(pid, 0)   # cómo quedaría la bodega
            if final < 0:
                raise ValidationError(
                    f"No puedes reducir tanto «{producto.nombre}»: de esta compra ya se vendieron "
                    f"unidades y el stock quedaría en {final}."
                )


DetalleCompraFormSet = inlineformset_factory(
    Compra,                                       
    DetalleCompra,                                
    form=DetalleCompraForm,                      
    formset=BaseDetalleCompraFormSet,             
    extra=0,                                      
    min_num=1,                                   
    validate_min=True,                            
    can_delete=True,                            
)


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["cedula", "telefono", "cargo"]
        widgets = {
            "cedula": forms.TextInput(attrs={"class": "form-control", "maxlength": "10"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Vendedor"}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip()
        if cedula and (len(cedula) != 10 or not cedula.isdigit()):   
            raise forms.ValidationError("La cédula debe tener 10 números.")
        return cedula
