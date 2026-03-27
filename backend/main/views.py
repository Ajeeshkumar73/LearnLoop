from django.shortcuts import render

from career_analysis.models import Review, UserProfile, CommunityPost, DirectMessage
from accounts.models import User, Profile
from django.shortcuts import redirect

def home(request):
    reviews_cursor = Review.objects.order_by('-created_at')[:3]
    reviews = []
    for r in reviews_cursor:
        profile = UserProfile.objects(user_email=r.user_email).first()
        reviews.append({
            "full_name": getattr(profile, 'full_name', '') if profile else r.user_email,
            "profile_pic": getattr(profile, 'profile_pic', '') if profile else None,
            "rating": r.rating,
            "stars": range(r.rating) if r.rating else [],
            "empty_stars": range(5 - r.rating) if r.rating else range(5),
            "review_text": r.review_text
        })
    return render(request, 'index.html', {"reviews": reviews})

def register_view(request):
    return render(request, 'register.html')

def admin_dashboard(request):
    user_email = request.session.get('user_email')
    if user_email != "ajeeshexatech@gmail.com":
        return redirect('accounts:login')
    
    raw_users = User.objects.all()
    users = []
    for u in raw_users:
        if u.email == "ajeeshexatech@gmail.com":
            continue
        prof = Profile.objects(user=u.email).first()
        users.append({
            'email': u.email,
            'full_name': prof.full_name if prof else "-"
        })

    posts = CommunityPost.objects.order_by('-created_at')
    supports = DirectMessage.objects.order_by('-timestamp')

    context = {
        'users': users,
        'posts': posts,
        'supports': supports
    }
    return render(request, 'admin_dashboard.html', context)


def delete_user(request, email):
    user_email = request.session.get('user_email')
    if request.method == "POST" and user_email == "ajeeshexatech@gmail.com":
        if email != "ajeeshexatech@gmail.com":
            User.objects(email=email).delete()
            Profile.objects(user=email).delete()
            UserProfile.objects(user_email=email).delete()
    return redirect('admin_dashboard')


def delete_post(request, post_id):
    user_email = request.session.get('user_email')
    if request.method == "POST" and user_email == "ajeeshexatech@gmail.com":
        CommunityPost.objects(id=post_id).delete()
    return redirect('admin_dashboard')


def delete_support(request, support_id):
    user_email = request.session.get('user_email')
    if request.method == "POST" and user_email == "ajeeshexatech@gmail.com":
        DirectMessage.objects(id=support_id).delete()
    return redirect('admin_dashboard')
