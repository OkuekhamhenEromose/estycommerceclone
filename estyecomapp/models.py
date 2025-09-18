from django.db import models

import uuid
import secrets
from paystackapi.paystack import Paystack
from paystackapi.transaction import Transaction
from users.models import Profile

#::::: CATEGORY Model :::::
class Category(models.Model):
    title = models.CharField(max_length=50)
    image = models.ImageField(upload_to='category')
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title

#::::: PRODUCT Model :::::
class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.PositiveBigIntegerField()
    discount_price = models.PositiveBigIntegerField(null=True,blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    main = models.ImageField(upload_to='product')
    photo1 = models.ImageField(upload_to='product',null=True,blank=True)
    photo2 = models.ImageField(upload_to='product',null=True,blank=True)
    photo3 = models.ImageField(upload_to='product',null=True,blank=True)
    photo4 = models.ImageField(upload_to='product',null=True,blank=True)
    product_id = models.UUIDField(unique=True,default=uuid.uuid4)
    is_available = models.BooleanField(default=True)
    in_stock = models.BigIntegerField()
    rating = models.BigIntegerField()
    review = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title
    def save(self,*args, **kwargs):
        if not self.product_id:
            self.product_id = uuid.uuid4()
        super().save(*args, **kwargs)

#::::: CART Model :::::
class Cart(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE,null=True,blank=True)
    total = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{str(self.total)}'

#::::: CART PRODUCT Model :::::
class CartProduct(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    subtotal = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Cart Product - {self.cart.id} -{self.quantity}'

#::::: ORDER Model :::::
ORDER_STATUS=(
    ('pending','pending'),
    ('cancel','cancel'),
    ('complete','complete')
)
PAYMENT_METHOD=(
    ('paystack','paystack'),
    ('paypal','paypal'),
    ('transfer','transfer')
)

class Order(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    order_by = models.CharField(max_length=255)
    shipping_address = models.TextField()
    mobile = models.CharField(max_length=50)
    email = models.EmailField()
    amount = models.PositiveBigIntegerField()
    subtotal = models.PositiveBigIntegerField()
    order_status = models.CharField(max_length=50,choices=ORDER_STATUS,default='pending')
    payment_method = models.CharField(max_length=50,choices=PAYMENT_METHOD,default='paystack')
    payment_complete = models.BooleanField(default=False)
    ref = models.CharField(max_length=255,null=True,unique=True)

    def __str__(self):
        return f'{self.amount} - {str(self.id)}'
    
    # auto save ref
    def save(self,*args,**kwargs):
        # if not self.ref:
        #     self.ref = self.secrets.token_urlsafe(50)
        # super().save(**args,**kwargs)
        while not self.ref:
            ref = secrets.token_urlsafe(50)
            obj_with_sm_ref = Order.objects.filter(ref=ref)
            if not obj_with_sm_ref:
                self.ref = ref
        super().save(*args, **kwargs)
    
    # amount from cent/kobo to naira
    def amount_value(self)->int:
        return self.amount * 100
    
    # verifying payment on paystack
    def verify_payment(self):
        paystack = Paystack()
        status,result = paystack.verify_payment(self.ref)
        if status and result.get('status') == 'success':
            # ensure the amount  matches'
            if result['amount']/100 == self.amount:
                self.payment_complete = True
                # del self.cart
                self.save()
                return True
        # if payment is not successful
        return False

