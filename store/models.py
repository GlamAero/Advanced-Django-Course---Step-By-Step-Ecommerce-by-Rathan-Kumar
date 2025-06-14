from django.db import models
from category.models import Category
from django.urls import reverse


# Create your models here.

class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    price = models.IntegerField()
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


    # In the below, 'reverse' is a function that is used to dynamically generate URLs based on named URL patterns(urls.py file content url path). Instead of hardcoding URLs, reverse() allows you to construct them programmatically using the view name and parameters.
    # This is particularly useful for maintaining clean and maintainable code, as it allows you to change the URL patterns in one place (urls.py) without having to update them throughout your codebase.

    # In the below 'reverse' function, 'product_detail' is the name of the URL pattern defined in the urls.py file of the store app.

    # 'self.slug' is the slug of the current product instance('class Product' in this model.py file). 'self' means the 'class Product'. 
    # The 'args' parameter is a list of arguments that will be passed to the URL pattern. In this case, it includes the slug of the product instance and the slug of the category model instance because the Product model above has field 'slug' as the product's slug and also the category field in the model has a slug field as well in the 'Category' model. This is reflected in the store's URL: 'path('<slug:category_slug>/<slug:product_slug>', views.product_detail, name='product_detail'),' which specifies both the product_slug(represented below as 'self.slug') and the category_slug(represented below as 'self.category.slug'). This means that when you call get_url() on a Product instance, it will return the URL for that specific product page from the associated category.

    # Thus this 'get_url' method is used to generate the URL for the particular product page based on its slug. This allows you to easily create links to each  product in your templates or views.
    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])


    def __str__(self):
        return self.product_name


class VariationManager(models.Manager):
    def colors(self):
        return super(VariationManager, self).filter(variation_category='color', is_active=True)
    
    def sizes(self):
        return super(VariationManager, self).filter(variation_category='size', is_active=True)
    

variation_category_choice = (
    ('color', 'color'),
    ('size', 'size')
)

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # 'variation_category' is used to specify the type of variation (e.g., color, size) for the product. This allows you to categorize variations based on their attributes.
    # The 'choices' parameter defines the possible values for this field. In this case, it can be either 'color' or 'size'.
    variation_category = models.CharField(max_length=100, choices=variation_category_choice)

    # 'variation_value' is used to store the specific value of the variation (e.g., red, blue for color; small, medium for size). This allows you to define the actual options available for each variation category.
    variation_value = models.CharField(max_length=100)

    # 'is_active' is used to determine whether the variation is active or not. This can be useful for managing product variations that may not be available for sale at a given time.
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)

    # telling this model class that we have a model manager for it:
    objects = VariationManager()

    
    def __str__(self):
        return self.variation_value
    



