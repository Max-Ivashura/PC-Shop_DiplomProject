from django.utils import timezone


class CartActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if hasattr(request, 'cart') and request.cart.is_active:
            request.cart.updated_at = timezone.now()
            request.cart.save(update_fields=['updated_at'])

        return response