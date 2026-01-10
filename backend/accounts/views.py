from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Profile

def register(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("accounts:register")

        if User.objects(email=email).first():
            messages.error(request, "Email already registered")
            return redirect("accounts:register")

        user = User(email=email)
        user.set_password(password)
        user.save()

        Profile(
            user=email,
            full_name=full_name
        ).save()

        messages.success(request, "Account created successfully")
        return redirect("accounts:login")

    return render(request, "register.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "All fields are required")
            return redirect("accounts:login")

        user = User.objects(email=email).first()

        if user and user.check_password(password):
            request.session["user_email"] = user.email
            request.session.set_expiry(3600)  # 1 hour
            return redirect("career_analysis:career_recom")
        else:
            messages.error(request, "Invalid email or password")
            return redirect("accounts:login")

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    return redirect("accounts:login")



