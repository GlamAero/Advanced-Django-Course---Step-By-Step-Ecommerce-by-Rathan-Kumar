from django.db import models
from django.urls import reverse


# Create your models here.
class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)

    # slug is a URL-friendly version of a string e.g '/category/books' instead of '/category/1'. Slugs make URLs more readable and search-engine friendly:
    slug = models.SlugField(max_length=100, unique=True)

    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/categories', blank=True, null=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


    # In the below, 'reverse' is a function that is used to dynamically generate URLs based on named URL patterns(urls.py file content url path). Instead of hardcoding URLs, reverse() allows you to construct them programmatically using the view name and parameters.
    # This is particularly useful for maintaining clean and maintainable code, as it allows you to change the URL patterns in one place (urls.py) without having to update them throughout your codebase.

    # 'self.slug' is the slug of the current category instance('class Category' in this model.py file). 'self' means the 'class Category'. 

    # In the below 'reverse' function, 'products_by_category' is the name of the URL pattern defined in the urls.py file of the store app. This URL pattern is used to display all products in a specific category. The 'args' parameter is a list of arguments that will be passed to the URL pattern. In this case, it includes the slug of the category instance. This means that when you call get_url() on a Category instance, it will return the URL for that specific category's products page based on its slug.
    def get_url(self):
        return reverse('products_by_category', args=[self.slug])
    
    
    def __str__(self):
        return self.category_name 