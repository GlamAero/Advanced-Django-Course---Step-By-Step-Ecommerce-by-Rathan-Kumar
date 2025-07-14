from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True
    s3_object_parameters = {
        'CacheControl': 'max-age=31536000',  # 1 year
    }
    
    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = settings.AWS_S3_CUSTOM_DOMAIN
        super().__init__(*args, **kwargs)

class MediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
    s3_object_parameters = {
        'CacheControl': 'max-age=86400',  # 1 day
    }
    
    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = settings.AWS_S3_CUSTOM_DOMAIN
        super().__init__(*args, **kwargs)

