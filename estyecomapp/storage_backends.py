from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import os

class MediaStorage(S3Boto3Storage):
    """
    Custom storage class for media files with folder organization
    """
    def __init__(self, *args, **kwargs):
        # Only set location if using S3
        if settings.USE_S3:
            self.location = getattr(settings, 'AWS_LOCATION', 'media')
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """
        Override to handle duplicate filenames by appending a number
        Only applies when using S3
        """
        if not settings.USE_S3:
            return name
            
        if self.exists(name):
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)
            counter = 1
            while self.exists(os.path.join(dir_name, f"{file_root}_{counter}{file_ext}")):
                counter += 1
            name = os.path.join(dir_name, f"{file_root}_{counter}{file_ext}")
        return name

class PublicMediaStorage(S3Boto3Storage):
    """
    Storage for publicly accessible media files
    """
    def __init__(self, *args, **kwargs):
        if settings.USE_S3:
            self.location = getattr(settings, 'AWS_LOCATION', 'media')
            self.default_acl = 'public-read'
            self.querystring_auth = False
        super().__init__(*args, **kwargs)

class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage for private media files (requires signed URLs)
    """
    def __init__(self, *args, **kwargs):
        if settings.USE_S3:
            self.location = getattr(settings, 'AWS_LOCATION', 'media')
            self.default_acl = 'private'
            self.querystring_auth = True
            self.querystring_expire = 300
        super().__init__(*args, **kwargs)