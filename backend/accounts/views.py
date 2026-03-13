import uuid
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from .models import User, Profile
from career_analysis.models import SavedCareer, PasswordResetToken


# =====================================================
# REGISTER
# =====================================================
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


# =====================================================
# LOGIN
# =====================================================
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
            request.session.set_expiry(3600)

            saved = SavedCareer.objects(user_email=user.email).first()

            if saved:
                return redirect("career_analysis:gap_analyzer")
            else:
                return redirect("career_analysis:career_recom")
        else:
            messages.error(request, "Invalid email or password")
            return redirect("accounts:login")

    return render(request, "login.html")


# =====================================================
# LOGOUT
# =====================================================
def logout_view(request):
    request.session.flush()
    return redirect("accounts:login")


# =====================================================
# FORGOT PASSWORD - Request Reset
# =====================================================
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Please enter your email address")
            return redirect("accounts:forgot_password")

        user = User.objects(email=email).first()

        if user:
            # Generate unique token
            token = uuid.uuid4().hex

            # Delete any existing tokens for this email
            PasswordResetToken.objects(email=email).delete()

            # Save new token
            PasswordResetToken(
                email=email,
                token=token,
            ).save()

            # Build reset URL
            reset_url = request.build_absolute_uri(
                f"/auth/reset-password/{token}/"
            )

            # Send email
            try:
                send_mail(
                    subject="LearnLoop - Reset Your Password",
                    message=f"Hi,\n\nClick the link below to reset your password:\n\n{reset_url}\n\nThis link expires in 1 hour.\n\nIf you didn't request this, please ignore this email.\n\n— LearnLoop Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, "Password reset link sent to your email!")
            except Exception as e:
                print(f"Email sending failed: {e}")
                # If email fails (dev mode), show the link directly
                messages.success(request, "Password reset link sent! (Dev mode: check console)")
                print(f"\n🔗 PASSWORD RESET LINK: {reset_url}\n")
        else:
            # Don't reveal if email exists or not (security)
            messages.success(request, "If an account with that email exists, a reset link has been sent.")

        return redirect("accounts:forgot_password")

    return render(request, "forgot_password.html")


# =====================================================
# RESET PASSWORD - Set New Password
# =====================================================
def reset_password(request, token):
    # Find the token
    reset_token = PasswordResetToken.objects(token=token, used=0).first()

    if not reset_token:
        messages.error(request, "Invalid or expired reset link")
        return redirect("accounts:login")

    # Check if token is expired (1 hour)
    if datetime.utcnow() - reset_token.created_at > timedelta(hours=1):
        reset_token.delete()
        messages.error(request, "Reset link has expired. Please request a new one.")
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not password or len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return render(request, "reset_password.html", {"token": token})

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, "reset_password.html", {"token": token})

        # Update user password
        user = User.objects(email=reset_token.email).first()
        if user:
            user.set_password(password)
            user.save()

            # Mark token as used
            reset_token.used = 1
            reset_token.save()

            messages.success(request, "Password reset successfully! Please log in.")
            return redirect("accounts:login")
        else:
            messages.error(request, "User not found")
            return redirect("accounts:login")

    return render(request, "reset_password.html", {"token": token})


# =====================================================
# GOOGLE SIGN-IN
# =====================================================
@csrf_exempt
def google_signin(request):
    """Handle Google Sign-In callback"""
    if request.method == "POST":
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        credential = request.POST.get("credential")

        if not credential:
            messages.error(request, "Google sign-in failed")
            return redirect("accounts:login")

        try:
            # Verify the Google ID token
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo.get("email", "").lower()
            full_name = idinfo.get("name", "")

            if not email:
                messages.error(request, "Could not get email from Google")
                return redirect("accounts:login")

            # Check if user exists
            user = User.objects(email=email).first()

            if not user:
                # Create new user (no password needed for Google auth)
                user = User(email=email)
                user.set_password(uuid.uuid4().hex)  # random password
                user.save()

                Profile(
                    user=email,
                    full_name=full_name
                ).save()

            # Log them in
            request.session["user_email"] = user.email
            request.session.set_expiry(3600)

            saved = SavedCareer.objects(user_email=user.email).first()

            if saved:
                return redirect("career_analysis:gap_analyzer")
            else:
                return redirect("career_analysis:career_recom")

        except ValueError as e:
            print(f"Google token verification failed: {e}")
            messages.error(request, "Google sign-in verification failed")
            return redirect("accounts:login")

    return redirect("accounts:login")
