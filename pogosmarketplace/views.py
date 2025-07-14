from django.shortcuts import render
from store.models import Product

def home(request):
    products = Product.objects.filter(is_available=True)

    context = {
        'products': products,
    }

    # Render the home page template
    return render(request, 'home.html', context)