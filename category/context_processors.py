from .models import Category


# This context processor adds the list of categories to the context of all templates
# It allows you to access the categories in your templates without explicitly passing them from each view.
# This context processor is added to the 'TEMPLATES' setting in settings.py under 'context_processors'.
def menu_links(request):
    links = Category.objects.all()
    return dict(links=links)