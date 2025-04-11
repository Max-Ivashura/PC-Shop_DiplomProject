from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from apps.accounts.models import Wishlist, WishlistItem
from apps.accounts.forms import UserProfileForm, CustomUserForm, CustomUserCreationForm, LoginForm
from apps.configurator.models import Build
from apps.products.models import Product


# --- LOGIN ---
def custom_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        try:
            if form.is_valid():
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f"Добро пожаловать, {username}!")
                    return redirect('home')
                else:
                    messages.error(request, "Неверный логин или пароль.")
            else:
                messages.error(request, "Ошибка в форме. Проверьте введенные данные.")
        except Exception as e:
            messages.error(request, f"Произошла ошибка: {str(e)}")
            return redirect('login')
    else:
        form = LoginForm(request)
    return render(request, 'accounts/login.html', {'form': form})


def custom_logout(request):
    logout(request)
    messages.info(request, "Вы успешно вышли из аккаунта.")
    return redirect('home')


# --- REGISTER ---
def register(request):
    try:
        if request.method == 'POST':
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                login(request, user)
                messages.success(request, "Регистрация прошла успешно!")
                return redirect('profile')
            else:
                messages.error(request, "Ошибка в форме. Исправьте ошибки.")
        else:
            form = CustomUserCreationForm()
    except Exception as e:
        messages.error(request, f"Ошибка регистрации: {str(e)}")
        return redirect('register')
    return render(request, 'accounts/register.html', {'form': form})


# USER
@login_required
def profile(request):
    user = request.user
    # Убираем select_related('status'), так как это CharField
    orders = user.orders.all()  # Используем related_name из модели Order
    builds = user.builds.prefetch_related('components__product').all()
    reviews = user.review_set.select_related('product').all()

    context = {
        'orders': orders,
        'builds': builds,
        'reviews': reviews,
    }
    return render(request, 'accounts/profile.html', context)


# --- EDIT PROFILE ---
@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = CustomUserForm(request.POST, instance=request.user)
        # Передаем request.FILES для обработки файлов
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Профиль успешно обновлен!")
            return redirect('profile')
        else:
            messages.error(request, "Ошибка в форме. Исправьте ошибки.")
    else:
        user_form = CustomUserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.userprofile)

    context = {'user_form': user_form, 'profile_form': profile_form}
    return render(request, 'accounts/edit_profile.html', context)


# --- CHANGE PASSWORD ---
@login_required
def change_password(request):
    try:
        if request.method == 'POST':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Пароль успешно изменен!")
                return redirect('profile')
            else:
                messages.error(request, "Ошибка в форме. Проверьте пароль.")
        else:
            form = PasswordChangeForm(request.user)
    except Exception as e:
        messages.error(request, f"Ошибка при смене пароля: {str(e)}")
        return redirect('change_password')

    return render(request, 'accounts/change_password.html', {'form': form})


# --- WISHLIST ---
@login_required
def add_to_wishlist(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        wishlist.add_product(product)
        messages.success(request, "Товар добавлен в список желаний!")
    except Product.DoesNotExist:
        messages.error(request, "Товар не найден.")
    except Exception as e:
        messages.error(request, f"Ошибка: {str(e)}")
    return redirect('product_detail', product_slug=product.slug)


@login_required
def remove_from_wishlist(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        wishlist = request.user.wishlist
        wishlist.remove_product(product)
        messages.info(request, "Товар удален из списка желаний.")
    except Product.DoesNotExist:
        messages.error(request, "Товар не найден.")
    except Exception as e:
        messages.error(request, f"Ошибка: {str(e)}")
    return redirect('wishlist')


@login_required
def wishlist_view(request):
    wishlist = request.user.wishlist
    # Получаем товары через WishlistItem
    wishlist_items = WishlistItem.objects.filter(wishlist=wishlist).select_related('product')
    return render(request, 'accounts/wishlist.html', {'wishlist_items': wishlist_items})


# --- USER_BUILDS ---
@login_required
def user_builds(request):
    try:
        user_builds = Build.objects.filter(user=request.user).prefetch_related('components')
        if not user_builds.exists():
            messages.info(request, "У вас пока нет сборок.")
    except Exception as e:
        messages.error(request, f"Ошибка загрузки сборок: {str(e)}")
        user_builds = []
    return render(request, 'accounts/user_builds.html', {'builds': user_builds})
