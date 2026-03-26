from django.shortcuts import render

from career_analysis.models import Review, UserProfile

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


