from django.db import models
from django.contrib.auth.models import User

# Create your models here.
GENDER =(
    ('M','Male'),
    ('F','Female'),
)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    gender = models.CharField(max_length=10, choices=GENDER)
    profile_pix = models.ImageField(upload_to='profile', blank=True,null=True)

    def __str__(self):
        return self.fullname
