from rest_framework import status,permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from django.shortcuts import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings

import requests
from . serializers import *
from . models import *

class CategoryView(APIView):
    def get(self, request):
        category = Category.objects.all()
        serializer = CategorySerializer(category, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# :: category get,update and delete
class CategoryEditView(APIView):
    def get(self,request,pk):
        try:
            category = get_object_or_404(Category,pk=pk)
            serializer = CategorySerializer(category)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def put(self,request,pk):
        try:
            category = get_object_or_404(Category,pk=pk)
            serializer = CategorySerializer(category,data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,status=status.HTTP_201_CREATED)
            return Response(serializer.errors,status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def delete(self,request,pk):
        try:
            category = get_object_or_404(Category,pk=pk)
            category.delete()
            return Response({"Message":"Category deleted"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# :: product get and post
class ProductView(APIView):
    def get(self,request):
        try:
            product = Product.objects.all() 
            serializer = ProductSerializer(product,many=True)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # permission_classes=[permissions.IsAdminUser]
    def post(self,request):
        try:
            serializer = ProductSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,status=status.HTTP_201_CREATED)
            return Response(serializer.errors,status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# :: product get,update and delete
class ProductEditView(APIView):
    def get(self,request,pk):
        try:
            product = get_object_or_404(Product,pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def put(self,request,pk):
        try:
            product = get_object_or_404(Product,pk=pk)
            serializer = ProductSerializer(product,data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,status=status.HTTP_201_CREATED)
            return Response(serializer.errors,status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def delete(self,request,pk):
        try:
            product = get_object_or_404(Product,pk=pk)
            product.delete()
            return Response({"Message":"Product deleted"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add to cart
class AddToCartView(APIView):
    def post(self,request,id):
        try:
            # fet the product
            product = get_object_or_404(Product,id=id)
            # get the cart id
            cart_id = request.session.get('cart_id',None)
            
            with transaction.atomic():
                if cart_id:
                    cart = Cart.objects.filter(id=cart_id).first()
                    if cart is None:
                        cart = Cart.objects.create(total=0)
                        request.session['cart_id'] = cart.id
                    
                    this_product_in_cart = cart.cartproduct_set.filter(product=product)

                    # assigning cart to a user 
                    if request.user.is_authenticated and hasattr(request.user,'profile'):
                        cart.profile = request.user.profile
                        cart.save()

                    if this_product_in_cart.exists():
                        cartproduct = this_product_in_cart.last()
                        cartproduct.quantity +=1
                        cartproduct.subtotal +=product.price
                        cartproduct.save()
                        # update our cart
                        cart.total += product.price
                        cart.save()
                        return Response({"Message":"Item increase in cart"})
                    else:
                        cartproduct = CartProduct.objects.create(cart=cart,product=product,quantity=1,subtotal=product.price)
                        cartproduct.save()
                        # update our cart
                        cart.total += product.price
                        cart.save()
                        return Response({"Message":"A new Item added to cart"})

                else:
                    # create a cart
                    cart = Cart.objects.create(total=0)
                    request.session['cart_id'] = cart.id
                    cartproduct = CartProduct.objects.create(cart=cart,product=product,quantity=1,subtotal=product.price)
                    cartproduct.save()
                    # update our cart
                    cart.total += product.price
                    cart.save()
                    return Response({"Message":"A new cart created"})

        except Exception as e:
            return Response({"error":str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# My cart
class MyCartView(APIView):
    def get(self,request):
        try:
            cart_id = request.session.get('cart_id', None)
            if cart_id:
                cart = get_object_or_404(Cart,id=cart_id)
                # assigning cart to a user 
                if request.user.is_authenticated and hasattr(request.user,'profile'):
                    cart.profile = request.user.profile
                    cart.save()
                serializer = CartSerializer(cart)
                return Response(serializer.data,status=status.HTTP_200_OK)
            return Response({"error":"cart not found"},status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error":str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# manage user cart
class ManageCart(APIView):
    def post(self,request,id):
        action = request.data.get('action')
        try:
            cart_obj = get_object_or_404(CartProduct,id=id)
            cart = cart_obj.cart
            if action == "inc":
                cart_obj.quantity +=1
                cart_obj.subtotal += cart_obj.product.price
                cart_obj.save()
                cart.total +=cart_obj.product.price
                cart.save()
                return Response({"Message":"Item increase"},status=status.HTTP_200_OK)
            elif action == "dcr":
                cart_obj.quantity -=1
                cart_obj.subtotal -= cart_obj.product.price
                cart_obj.save()
                cart.total -=cart_obj.product.price
                cart.save()
                if cart_obj.quantity == 0:
                    cart_obj.delete()
                return Response({"Message":"Item decrease"},status=status.HTTP_200_OK)
            elif action == 'rmv':
                cart.total -= cart_obj.subtotal
                cart.save()
                cart_obj.delete()
                return Response({"Message":"Item removed"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error":str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# checkout    
class CheckoutView(APIView):
    def post(self,request):
        cart_id = request.session.get('cart_id',None)
        if not cart_id:
            return Response({"Error":"Cart not found"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cart_obj = get_object_or_404(Cart,id=cart_id)
        except Cart.DoesNotExists:
            return Response({"Error":"Cart does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save(
                cart = cart_obj,
                amount = cart_obj.total,
                subtotal = cart_obj.total,
                order_status = 'pending'
            )
            del request.session['cart_id']

            if order.payment_method == 'paystack':
                payment_url = reverse('payment',args=[order.id])
                return Response({'redirect_url': payment_url},status=status.HTTP_302_FOUND)
            
            return Response({'Message': 'Order Created Successfully'})
        
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

# payment
class PaymentPageView(APIView):
    def get(self,request,id):
        try:
            order = get_object_or_404(Order,id=id)
        except Order.DoesNotExist:
            return Response({'Error':'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        # Create payment request
        url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        data = {
            "amount": order.amount * 100,
            "email": order.email,
            "reference": order.ref
        }

        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()

        if response_data["status"]:
            paystack_url = response_data["data"]["authorization_url"]

            return Response({
                'order': order.id,
                'total': order.amount_value(),
                'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
                'paystack_url': paystack_url
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Payment initiation failed"}, status=status.HTTP_400_BAD_REQUEST)

# verify payment
class VerifyPaymentView(APIView):
    def get(self,request,ref):
        try:
            order = get_object_or_404(Order,ref=ref)
            url = f'https://api.paystack.co/transaction/verify/{ref}'
            headers= {"Authorization":f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            response = requests.get(url,headers=headers)
            response_data = response.json()

            if response_data["status"] and response_data["data"]["status"]=="success":
                order.payment_complete = True
                order.save()
                return Response({"Message":"Payment verify successfully"},status=status.HTTP_200_OK)
            elif response_data["data"]["status"] == "abandoned":
                # Handle abandoned payment
                order.order_status = "pending" 
                order.save()
                return Response({"Error": "Payment abandoned, please try again."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"Error":"Payment verify failed"},status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({'error':'invalid payment reference'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
                