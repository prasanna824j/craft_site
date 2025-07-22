from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserMasterManager(BaseUserManager):
    def create_user(self, email, user_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, user_name=user_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, user_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, user_name, password, **extra_fields)

class UserMaster(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    user_name = models.CharField(max_length=100)
    password = models.CharField(max_length=255)

    street_address = models.CharField(max_length=255, blank=True)  # Street Address
    city = models.CharField(max_length=100, blank=True)  # City
    state = models.CharField(max_length=100, blank=True)  # State
    zip_code = models.CharField(max_length=6, blank=True)  # ZIP Code

    phone = models.CharField(max_length=15, blank=True)

    joined_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserMasterManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['user_name']

    def __str__(self):
        return self.user_name




class CategoryMaster(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    category_image = models.ImageField(upload_to='categories/', blank=True, null=True)
    category_description = models.TextField(blank=True)

    def __str__(self):
        return self.category_name


class ProductMaster(models.Model):
    product_name = models.CharField(max_length=200)
    category = models.ForeignKey(CategoryMaster, on_delete=models.CASCADE)
    
    description = models.TextField()
    price = models.IntegerField()
    stock_no = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name

class ProductImage(models.Model):
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return f"Image for {self.product.product_name}"



class CartMaster(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Avoid duplicate cart items

    def __str__(self):
        return f"{self.user.user_name}'s Cart - {self.product.product_name}"



class OrderMaster(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE)
    total_price = models.IntegerField()
    total_quantity = models.IntegerField()
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='Pending')
    ordered_at = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.user_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(OrderMaster, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    price = models.IntegerField()
    quantity = models.IntegerField()
    order_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name} x {self.quantity}"


class ReviewMaster(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    review_date = models.DateTimeField(auto_now_add=True)
    review_text = models.TextField()
    rating = models.IntegerField()

    def __str__(self):
        return f"Review by {self.user.user_name} - {self.product.product_name}"


class WishlistMaster(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    added_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user_name}'s Wishlist - {self.product.product_name}"
class PasswordResetOTP(models.Model):
    email = models.EmailField(unique=True)  # Since you're using update_or_create
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.otp}"

