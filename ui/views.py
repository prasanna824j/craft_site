from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import UserMaster, ProductMaster,ProductImage, CategoryMaster, CartMaster, OrderMaster, OrderItem, ReviewMaster, WishlistMaster,PasswordResetOTP
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django import forms
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic.edit import UpdateView
from django.utils import timezone
import razorpay
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from datetime import datetime
import requests
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class OrderManagement(TemplateView):
    template = 'order_management.html'

    def get(self, request):
        # Get filter parameters
        status = request.GET.get('status')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        # Base queryset
        orders = OrderMaster.objects.all().order_by('-ordered_at')

        # Apply filters
        if status:
            orders = orders.filter(status=status)
        if date_from:
            orders = orders.filter(ordered_at__gte=datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            orders = orders.filter(ordered_at__lte=datetime.strptime(date_to, '%Y-%m-%d'))

        return render(request, self.template, {
            'orders': orders,
            'status': status,
            'date_from': date_from,
            'date_to': date_to
        })

@csrf_exempt
@staff_member_required
def update_order_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            new_status = data.get('status')

            order = OrderMaster.objects.get(id=order_id)
            order.status = new_status
            order.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@method_decorator(csrf_exempt, name='dispatch')
class index(TemplateView):
    template = 'index.html'

    def get(self, request):
        categories = CategoryMaster.objects.all()
        products = ProductMaster.objects.all()
        wishlist_product_ids = []

        if request.user.is_authenticated:
            wishlist_product_ids = WishlistMaster.objects.filter(
                user=request.user
            ).values_list('product_id', flat=True)

        return render(request, self.template, {
            'categories': categories,
            'products': products,
            'wishlist_ids': wishlist_product_ids
        })


def categories(request):
    categories = CategoryMaster.objects.all()
    return render(request, 'categories.html', {'categories': categories})

@csrf_exempt
@login_required
def add_to_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Please log in to add items to cart.', 'level': 'warning'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))

            product = ProductMaster.objects.get(id=product_id)
            cart_item, created = CartMaster.objects.get_or_create(user=request.user, product=product)

            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity

            cart_item.save()

            return JsonResponse({'status': 'success', 'message': 'Product added to cart'})
        
        except ProductMaster.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@method_decorator(csrf_exempt, name='dispatch')
class ProductAdd(LoginRequiredMixin, TemplateView):
    template = 'product_add.html'

    def get(self, request):
        categories = CategoryMaster.objects.all()
        products = ProductMaster.objects.all()
        return render(request, self.template, {'categories': categories,'products':products})

    def add_category(self, request):
        try:
            category = CategoryMaster.objects.create(
                category_name=request.POST['name'],
                category_description=request.POST['category_description']
            )
            
            if 'category_image' in request.FILES:
                category.category_image = request.FILES['category_image']
                category.save()

            messages.success(request, 'Category added successfully!')
            return redirect('product_add')

        except Exception as e:
            messages.error(request, f'Error adding category: {str(e)}')
            return redirect('product_add')
    
    def post(self, request):
        if 'category_description' in request.POST:  # This is a category submission
            try:
                category = CategoryMaster.objects.create(
                    category_name=request.POST['name'],
                    category_description=request.POST['category_description']
                )
                
                if 'category_image' in request.FILES:
                    category.category_image = request.FILES['category_image']
                    category.save()

                messages.success(request, 'Category added successfully!')
                return redirect('product_add')

            except Exception as e:
                messages.error(request, f'Error adding category: {str(e)}')
                return redirect('product_add')
        else:  # This is a product submission
            try:
                category = get_object_or_404(CategoryMaster, id=request.POST['category'])

                product = ProductMaster.objects.create(
                    product_name=request.POST['name'],
                    category=category,
                    description=request.POST['description'],
                    price=request.POST['price'],
                    stock_no=request.POST.get('stock_no', 1),
                )

                # Save multiple images
                images = request.FILES.getlist('image')
                print("Images:", images)
                for image in images:
                    ProductImage.objects.create(product=product, image=image)

                messages.success(request, 'Product added successfully!')
                return redirect('product_add')

            except Exception as e:
                messages.error(request, f'Error adding product: {str(e)}')
                categories = CategoryMaster.objects.all()
                products = ProductMaster.objects.all()
                return render(request, self.template, {'categories': categories, 'products': products})
            


@method_decorator(csrf_exempt, name='dispatch')
class EditProduct(UpdateView):
    model = ProductMaster
    fields = ['product_name', 'price', 'stock_no']
    template_name = 'product_add.html'
    success_url = '/product_add'

    def form_valid(self, form):
        messages.success(self.request, 'Product updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form Errors:", form.errors)
        messages.error(self.request, 'Error updating product')
        return super().form_invalid(form)

@method_decorator(csrf_exempt, name='dispatch')
class cart(LoginRequiredMixin,TemplateView):
    template = 'cart.html'

    def get(self, request):
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)

            # Use select_related for performance
            cart_items = CartMaster.objects.filter(user=user).select_related('product')

            valid_cart_items = []
            subtotal = 0

            for item in cart_items:
                if item.product:  # Ensure product exists
                    valid_cart_items.append(item)
                    subtotal += item.product.price * item.quantity

            shipping = 50  # fixed
            total = subtotal + shipping

            # Initialize Razorpay client
            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            print('razorpay_client',razorpay_client,{
                    'amount': total * 100,  # Amount in paise
                    'currency': 'INR',
                    'receipt': f'order_rcptid_{user.id}_{timezone.now().timestamp()}',
                    'payment_capture': '1'
                })
            # Create Razorpay order data
            razorpay_order = None
            if valid_cart_items:
                try:
                    razorpay_order = razorpay_client.order.create({
                        'amount': int(total * 100),   # Must be integer paise
                        'currency': 'INR',
                        'receipt': f'order_rcptid_{user.id}_{timezone.now().timestamp()}',
                        'payment_capture': '1'
                    })
                except requests.exceptions.JSONDecodeError as e:
                    print("‼️ Razorpay JSON decode failed")
                    print("Response that caused error:")
                    print(e.doc[:300])  # Print first few chars of bad response
                    raise
            return render(request, self.template, {
                'cart_items': valid_cart_items,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
                'razorpay_order_id': razorpay_order['id'] if razorpay_order else None,
                'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                'callback_url': request.build_absolute_uri(reverse('razorpay_callback'))
            })
        return redirect('login')

@csrf_exempt
def update_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Please log in.', 'level': 'warning'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_item_id = data.get('cart_item_id')
            quantity = int(data.get('quantity'))

            cart_item = CartMaster.objects.get(id=cart_item_id, user=request.user)
            cart_item.quantity = quantity
            cart_item.save()

            return JsonResponse({'status': 'success', 'message': 'Quantity updated'})
        except CartMaster.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Cart item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)

@csrf_exempt
def remove_cart_item(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Please log in.', 'level': 'warning'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_item_id = data.get('cart_item_id')

            cart_item = CartMaster.objects.get(id=cart_item_id, user=request.user)
            cart_item.delete()

            return JsonResponse({'status': 'success', 'message': 'Item removed from cart'})
        except CartMaster.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Cart item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)

    
    
@method_decorator(csrf_exempt, name='dispatch')
class account(LoginRequiredMixin,TemplateView):
    template = 'account.html'

    def get(self, request):
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)
            # Get user's orders for display in account page
            orders = OrderMaster.objects.filter(user=user).order_by('-ordered_at')
            return render(request, self.template, {'user': user, 'orders': orders})
        return redirect('login')
    
    def post(self, request):
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)
            user.user_name = request.POST.get('user_name', user.user_name)
            user.email = request.POST.get('email', user.email)
            user.address = request.POST.get('address', user.address)
            user.area = request.POST.get('area', user.area)
            user.door_no = request.POST.get('door_no', user.door_no)
            user.postal_code = request.POST.get('postal_code', user.postal_code)
            user.phone = request.POST.get('phone', user.phone)
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('/account')
        return redirect('login')
    
@method_decorator(csrf_exempt, name='dispatch')
class watchlist(LoginRequiredMixin,TemplateView):
    template = 'watchlist.html'

    def get(self, request):
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)
            wishlist_items = WishlistMaster.objects.filter(user=user)
            return render(request, self.template, {'wishlist_items': wishlist_items})
        return redirect('login')
    
    def post(self, request):
        if request.user.is_authenticated:
            try:
                user = get_object_or_404(UserMaster, id=request.user.id)
                product = get_object_or_404(ProductMaster, id=request.POST['product_id'])
                
                # Check if product already in wishlist
                wishlist_item, created = WishlistMaster.objects.get_or_create(
                    user=user,
                    product=product
                )
                
                if not created:
                    messages.info(request, 'Product already in wishlist!')
                else:
                    messages.success(request, 'Product added to wishlist successfully!')
                
                return redirect('watchlist')
            except Exception as e:
                messages.error(request, f'Error adding to wishlist: {str(e)}')
                return redirect('index')
        return redirect('login')


class CustomUserCreationForm(forms.ModelForm):
    user_name = forms.CharField(required=True, max_length=150)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)
    
    # Updated fields for address
    street_address = forms.CharField(required=False, max_length=255)
    city = forms.CharField(required=False, max_length=100)
    state = forms.CharField(required=False, max_length=100)
    zip_code = forms.CharField(required=False, max_length=10)

    phone = forms.CharField(required=False)

    class Meta:
        model = UserMaster
        fields = ("user_name", "email", "password1", "password2", "street_address", "city", "state", "zip_code", "phone")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class Signup(View):
    template = 'signup.html'

    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, self.template, {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                authenticated_user = authenticate(request, email=user.email, password=form.cleaned_data["password1"])
                if authenticated_user:
                    login(request, authenticated_user)
                    messages.success(request, 'Account created successfully!')
                    return redirect('index')
                else:
                    messages.error(request, "Authentication failed. Please log in manually.")
            except Exception as e:
                messages.error(request, f"Error creating account: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        return render(request, self.template, {'form': form})

class Login(View):
    template = 'login.html'

    def get(self, request):
        return render(request, self.template)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')  # <--- get checkbox value

        if not email or not password:
            messages.error(request, 'Please enter both email and password')
            return render(request, self.template)

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)

            # If remember is not checked, session expires on browser close
            if not remember:
                request.session.set_expiry(0)  # Session expires on browser close
            else:
                request.session.set_expiry(1209600)  # 2 weeks in seconds

            if user.is_superuser:
                return redirect('product_add')
            return redirect('index')
        else:
            messages.error(request, 'Invalid email or password')
            return render(request, self.template)

class Logout(View):
    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, 'You have been logged out successfully!')
        return redirect('index')


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayPaymentView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            user = request.user
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
                
                # Find order by razorpay_order_id
                order = OrderMaster.objects.get(razorpay_order_id=razorpay_order_id, user=user)
                order.is_paid = True
                order.status = 'Paid'
                order.razorpay_payment_id = payment_id
                order.razorpay_signature = signature
                order.save()
                user_data = UserMaster.objects.get(id=order.user_id)
                # Send order confirmation email
                order_items = OrderItem.objects.filter(order=order)
                total_amount = sum(item.price * item.quantity for item in order_items)+50
                
                email_body = f"Dear {user.user_name},\n\n"
                email_body += "Thank you for your order! Here are your order details:\n\n"
                email_body += f"Order ID: {order.id}\n"
                email_body += f"Order Date: {order.ordered_at.strftime('%Y-%m-%d %H:%M')}\n"
                email_body += "\nOrder Items:\n"
                
                for item in order_items:
                    email_body += f"- {item.product.product_name} x {item.quantity}: ₹{item.price * item.quantity}\n"
                
                email_body += f"\nShipping Address: {order.delivery_address}"
                email_body += f"\nTotal Amount: ₹{total_amount}"
                email_body += "\n\nThank you for shopping with us!"
                email_body += "\nBestRegards"
                email_body += "\nAdoraCrafts Team"
                send_mail(
                    'Order Confirmation - Adora Crafts',
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [order.user.email],
                    fail_silently=True,
                )
                
                # Clear cart after successful payment
                CartMaster.objects.filter(user=user).delete()
                
                messages.success(request, 'Payment successful! Your order has been confirmed. Check your email for details.')
                return redirect('account')
                
            except razorpay.errors.SignatureVerificationError:
                # Signature verification failed
                order = OrderMaster.objects.get(razorpay_order_id=razorpay_order_id, user=user)
                order.status = 'Payment Failed'
                order.save()
                
                messages.error(request, 'Payment verification failed. Please try again.')
                return redirect('cart')
                
        except OrderMaster.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('cart')
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('cart')


@csrf_exempt
def razorpay_callback(request):
    if request.method == "POST":
        try:
            # Get the payment details from POST data
            payment_id = request.POST.get('razorpay_payment_id', '')
            order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify signature
            try:
                client.utility.verify_payment_signature(params_dict)
                # Find the order by razorpay order ID
                # This would require adding a razorpay_order_id field to your OrderMaster model
                # For now, we'll use session to store the mapping
                if 'order_mapping' in request.session and order_id in request.session['order_mapping']:
                    order_pk = request.session['order_mapping'][order_id]
                    order = OrderMaster.objects.get(pk=order_pk)
                    order.is_paid = True
                    order.status = 'Paid'
                    order.save()
                    user_data = UserMaster.objects.get(id=order.user_id)
                    # print('user_data',user_data,user_data.street_address)
                    # Send order confirmation email
                    order_items = OrderItem.objects.filter(order=order)
                    total_amount = sum(item.price * item.quantity for item in order_items)+50
                    
                    email_body = f"Dear {order.user.user_name},\n\n"
                    email_body += "Thank you for your order! Here are your order details:\n\n"
                    email_body += f"Order ID: {order.id}\n"
                    email_body += f"Order Date: {order.ordered_at.strftime('%Y-%m-%d %H:%M')}\n"
                    email_body += "\nOrder Items:\n"
                    
                    for item in order_items:
                        email_body += f"- {item.product.product_name} x {item.quantity}: ₹{item.price * item.quantity}\n"
                    
                    email_body += f"\nShipping Address: {user_data.street_address}"
                    email_body += f"\nTotal Amount: ₹{total_amount}"
                    email_body += "\n\nThank you for shopping with us!"
                    email_body += "\nBestRegards"
                    email_body += "\nAdoraCrafts Team"
                    # print(email_body,order.user.email)
                    send_mail(
                        'Order Confirmation - Adora Crafts',
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [order.user.email],
                        fail_silently=True,
                    )
                    
                    # Clear cart items
                    CartMaster.objects.filter(user=order.user).delete()
                    
                    # Add success message
                    messages.success(request, 'Payment successful! Your order has been confirmed. Check your email for details.')
                    return redirect('account')
                else:
                    return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
                    
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': 'Payment verification failed'}, status=400)
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


method_decorator(csrf_exempt, name='dispatch')
class PasswordReset(View):
    template = 'password_reset.html'

    def send_otp(self, email):
        otp = ''.join(random.choices(string.digits, k=6))
        PasswordResetOTP.objects.update_or_create(
            email=email,
            defaults={'otp': otp, 'created_at': timezone.now()}
        )
        send_mail(
            'Password Reset OTP',
            f'Your OTP for password reset is: {otp}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return otp

    def get(self, request):
        return render(request, self.template, {'show_otp': False})


    def post(self, request):
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        resend = request.POST.get('resend')

        if not email:
            messages.error(request, 'Email is required!')
            return redirect('password_reset')

        if resend == 'true':
            try:
                UserMaster.objects.get(email=email)
                self.send_otp(email)
                messages.success(request, 'New OTP sent to your email!')
                return render(request, self.template, {'show_otp': True, 'email': email})
            except UserMaster.DoesNotExist:
                messages.error(request, 'Email not found!')
                return redirect('password_reset')

        elif not otp:
            try:
                UserMaster.objects.get(email=email)
                self.send_otp(email)
                messages.success(request, 'OTP sent to your email!')
                return render(request, self.template, {'show_otp': True, 'email': email})
            except UserMaster.DoesNotExist:
                messages.error(request, 'Email not found!')
                return redirect('password_reset')

        else:
            try:
                otp_record = PasswordResetOTP.objects.get(email=email)

                if (timezone.now() - otp_record.created_at).total_seconds() > 300:
                    messages.error(request, 'OTP has expired!')
                    return render(request, self.template, {'show_otp': True, 'email': email})

                if otp == otp_record.otp:
                    new_password = request.POST.get('new_password')
                    confirm_password = request.POST.get('confirm_password')

                    if new_password != confirm_password:
                        messages.error(request, 'Passwords do not match!')
                        return render(request, self.template, {'show_otp': True, 'email': email})

                    user = UserMaster.objects.get(email=email)
                    user.set_password(new_password)
                    user.save()

                    otp_record.delete()
                    messages.success(request, 'Password reset successfully! Please login with new password.')
                    return redirect('login')

                else:
                    messages.error(request, 'Invalid OTP!')
                    return render(request, self.template, {'show_otp': True, 'email': email})
            except PasswordResetOTP.DoesNotExist:
                messages.error(request, 'OTP not found or expired!')
                return render(request, self.template, {'show_otp': True, 'email': email})

@method_decorator(csrf_exempt, name='dispatch')
class Order(LoginRequiredMixin,TemplateView):
    template = 'order.html'

    def get(self, request):
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)
            orders = OrderMaster.objects.filter(user=user)
            shipping = 50  # fixed
            return render(request, self.template, {'orders': orders,'shipping':shipping})
        return redirect('login')
    
    def post(self, request):
        if request.user.is_authenticated:
            try:
                user = get_object_or_404(UserMaster, id=request.user.id)
                cart_items = CartMaster.objects.filter(user=user)
                
                if not cart_items:
                    messages.error(request, 'Your cart is empty!')
                    return redirect('cart')
                
                total_price = sum(item.product.price * item.quantity for item in cart_items)
                shipping = 50  # fixed
                total_price = total_price + shipping
                total_quantity = sum(item.quantity for item in cart_items)
                
                # Initialize Razorpay client
                razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                
                # Create Razorpay order
                receipt_id = f'receipt_{user.id}_{int(timezone.now().timestamp())}'
                razorpay_order = razorpay_client.order.create({
                    'amount': total_price * 100,  # Amount in paise
                    'currency': 'INR',
                    'receipt': receipt_id,
                    'payment_capture': '1'
                })
                
                # Get address details from form
                street_address = request.POST.get('street_address')
                city = request.POST.get('city')
                state = request.POST.get('state')
                zip_code = request.POST.get('zip_code')
                phone = request.POST.get('phone')

                if not all([street_address, city, state, zip_code, phone]):
                    messages.error(request, 'Please provide all address details')
                    return redirect('cart')

                # Update user's address if changed
                if user.street_address != street_address or \
                   user.city != city or \
                   user.state != state or \
                   user.zip_code != zip_code or \
                   user.phone != phone:
                    user.street_address = street_address
                    user.city = city
                    user.state = state
                    user.zip_code = zip_code
                    user.phone = phone
                    user.save()

                # Create order but mark as unpaid
                order = OrderMaster.objects.create(
                    user=user,
                    total_price=total_price,
                    total_quantity=total_quantity,
                    is_paid=False,
                    status='Pending Payment',
                    razorpay_order_id=razorpay_order['id']
                )
                
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                
                # Store order mapping in session
                if 'order_mapping' not in request.session:
                    request.session['order_mapping'] = {}
                request.session['order_mapping'][razorpay_order['id']] = order.id
                request.session.modified = True
                
                # Don't delete cart items yet - only after successful payment
                
                context = {
                    'order': order,
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                    'callback_url': request.build_absolute_uri(reverse('razorpay_callback')),
                    'amount': total_price * 100,
                    'currency': 'INR',
                    'user_name': user.user_name,
                    'user_email': user.email,
                    'user_phone': user.phone
                }
                
                messages.success(request, 'Order created successfully! Proceed to payment.')
                return render(request, 'payment.html', context)
            except Exception as e:
                messages.error(request, f'Error placing order: {str(e)}')
                return redirect('cart')
        return redirect('login')

@method_decorator(csrf_exempt, name='dispatch')
class Review(LoginRequiredMixin,TemplateView):
    template = 'review.html'

    def get(self, request, product_id):
        if request.user.is_authenticated:
            product = get_object_or_404(ProductMaster, id=product_id)
            reviews = ReviewMaster.objects.filter(product=product)
            return render(request, self.template, {'product': product, 'reviews': reviews})
        return redirect('login')
    
    def post(self, request, product_id):
        if request.user.is_authenticated:
            try:
                user = get_object_or_404(UserMaster, id=request.user.id)
                product = get_object_or_404(ProductMaster, id=product_id)
                rating = int(request.POST.get('rating', 0))
                
                if rating < 1 or rating > 5:
                    messages.error(request, 'Rating must be between 1 and 5')
                    return redirect('review', product_id=product_id)
                
                review = ReviewMaster.objects.create(
                    user=user,
                    product=product,
                    review_text=request.POST.get('review_text', ''),
                    rating=rating
                )
                
                messages.success(request, 'Review submitted successfully!')
                return redirect('review', product_id=product_id)
            except Exception as e:
                messages.error(request, f'Error submitting review: {str(e)}')
                return redirect('review', product_id=product_id)
        return redirect('login')


@csrf_exempt
def add_category(request):
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            # Check if category already exists
            if not CategoryMaster.objects.filter(category_name=name).exists():
                CategoryMaster.objects.create(category_name=name)
                messages.success(request, "Category added successfully!")
            else:
                messages.warning(request, "Category already exists.")
        else:
            messages.error(request, "Category name cannot be empty.")
        print(f"Messages: {messages.get_messages(request)}")

        return redirect('product_add')  # Redirect to the same form or another page
    return redirect('product_add')


@csrf_exempt
@login_required
def add_to_wishlist(request, product_id):
    if request.method == 'POST':
        product = ProductMaster.objects.get(id=product_id)
        user = request.user
        WishlistMaster.objects.get_or_create(user=user, product=product)
        return JsonResponse({'message': 'Added to wishlist'})

@csrf_exempt
@login_required
def remove_from_wishlist(request, product_id):
    if request.method == 'POST':
        user = request.user
        WishlistMaster.objects.filter(user=user, product_id=product_id).delete()
        return JsonResponse({'message': 'Removed from wishlist'})


def UpdateAccount(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            user = get_object_or_404(UserMaster, id=request.user.id)

            # Get data from form
            username = request.POST.get('username')
            phone = request.POST.get('phone')
            email = request.POST.get('email')

            # Update user info
            user.user_name = username
            user.phone = phone
            user.email = email
            user.save()

            messages.success(request, "Account details updated successfully.")
            return redirect('/account')  # Or your desired redirect route

        messages.error(request, "You need to log in to update your account.")
        return redirect('/login/')

@login_required
def update_address(request):
    if request.method == 'POST':
        user = get_object_or_404(UserMaster, id=request.user.id)
        user.user_name = request.POST.get('address_name')  # Optional, if editable
        user.street_address = request.POST.get('street')
        user.city = request.POST.get('city')
        user.state = request.POST.get('state')
        user.zip_code = request.POST.get('zip')
        user.save()
        messages.success(request, "Address details updated successfully.")
        return redirect('/account')  # Replace with your actual template/view name
    messages.error(request, "Something went wrong.")
    return redirect('/account')