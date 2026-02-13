from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator

GENDER = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Profile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='profile',  # Added for reverse lookup
        db_index=True  # Add index
    )
    fullname = models.CharField(
        max_length=100,  # Reduced from 255
        validators=[MinLengthValidator(2)]
    )
    phone = models.CharField(
        max_length=20,  # Reduced from 50
        db_index=True  # For phone lookups
    )
    gender = models.CharField(
        max_length=1,  # Reduced from 10
        choices=GENDER,
        db_index=True
    )
    profile_pix = models.ImageField(
        upload_to='profile',
        blank=True,
        null=True,
        default='profile/default-avatar.png'  # Add default
    )
    
    # Cache frequently accessed fields
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'gender']),
            models.Index(fields=['phone']),
        ]
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return self.fullname
    
    @property
    def avatar_url(self):
        """Cache busting for images"""
        if self.profile_pix and hasattr(self.profile_pix, 'url'):
            return f"{self.profile_pix.url}?v={self.updated.timestamp()}"
        return '/static/images/default-avatar.png'