from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import os

class MediaStorage(S3Boto3Storage):
    """
    Custom storage class for media files with folder organization
    """
    location = settings.AWS_LOCATION
    file_overwrite = False  # Don't overwrite files with same name
    
    def get_available_name(self, name, max_length=None):
        """
        Override to handle duplicate filenames by appending a number
        """
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
    location = settings.AWS_LOCATION
    default_acl = 'public-read'
    file_overwrite = False
    querystring_auth = False  # URLs don't need authentication

class PrivateMediaStorage(S3Boto3Storage):
    """
    Storage for private media files (requires signed URLs)
    """
    location = settings.AWS_LOCATION
    default_acl = 'private'
    file_overwrite = False
    querystring_auth = True  # URLs require authentication
    querystring_expire = 300  # 5 minutes