from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.store, name='store'),

    # TO GET ALL PRODUCTS BY CATEGORY:
    # category_slug is a slug field in the Category model named 'slug'. 
    # 'slug:category_slug' is a placeholder for the category slug in the URL. It allows you to pass a specific category slug to the view function.
    # When a user visits a URL like '/store/category-slug/' e.g '/store/shirts/', Django will match it to this pattern and pass 'category-slug', in this case 'shirts' as the 'category_slug' argument to the 'store' view. 
    # For instance if you have a category with the slug 'shirts', the URL would look like '/store/shirts/'. 'shirt' here is the slug(category_slug) of the category:'shirt' and you will notice it bears the same name as the category since it is explicitly told to bear the same name in 'admin' file of 'category' app in the 'prepopulated_fields' area of the admin file.
    # This allows you to filter products by category in the view function.
    path('category/<slug:category_slug>/', views.store, name='products_by_category'),
    
    path('category/<slug:category_slug>/<slug:product_slug>', views.product_detail, name='product_detail'),
    path('search/', views.search, name='search'),
    path('vendor/products/', views.vendor_products, name='vendor_products'),
    path('vendor/products/<int:product_id>/combos/pdf/', views.download_combo_summary, name='download_combo_summary'),
]