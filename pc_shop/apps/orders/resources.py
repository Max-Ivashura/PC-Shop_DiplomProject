from import_export import resources
from .models import Order

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('id', 'user__email', 'status', 'total_price', 'paid', 'created_at')
        export_order = fields