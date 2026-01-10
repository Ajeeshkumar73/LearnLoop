import os, json, re, random
from django.shortcuts import render, redirect
from groq import Groq
from dotenv import load_dotenv
from .models import CareerSubmission, SavedCareer
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache


load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))


VALID_ICONS = {
    "code", "analytics", "cloud", "security", "smart_toy",
    "business_center", "science", "precision_manufacturing",
    "bolt", "work", "engineering", "developer_mode",
    "memory", "terminal", "dataset"
}

# growth in percentage
def extract_growth_percent(growth_text):
    """
    Extracts numeric growth percent (int) from AI text
    """
    if not growth_text:
        return random.randint(12, 25)

    growth_text = growth_text.lower()

    # If AI gives exact percentage
    match = re.search(r"(\d+)\s*%", growth_text)
    if match:
        return int(match.group(1))

    # Fallback based on words
    if "high" in growth_text:
        return 22
    if "medium" in growth_text or "moderate" in growth_text:
        return 15
    if "low" in growth_text:
        return 8

    return random.randint(12, 25)


def get_career_recommendation(education, skills, interests, personality):
    prompt = f"""
You are an expert AI career counselor.


Analyze the user profile below and suggest the TOP 3 most suitable career domains.

User Profile:
- Education: {education}
- Skills: {skills}
- Interests: {interests}
- Personality Traits: {personality}

Requirements for each career:
1. Provide a **career name** that is highly relevant to the user's profile.
2. Provide a **clear explanation ("why")** why this career suits the user, based on skills, interests, and personality.
3. Provide a **short description** of the career (what the role involves, typical tasks, and work environment).
4. List **key required skills** that are most important for the career.
5. Provide a **realistic salary range in India (in LPA)** for entry-level to experienced professionals.
6.Future growth outlook
7. Suggest an appropriate **icon** (use one from: {', '.join(VALID_ICONS)}) and a **color** for UI.
8. Provide a **domain/industry category**.

Return ONLY valid JSON in the EXACT format below, with **3 career objects**, ranked from most to least suitable:

[
  {{
    "career": "",
    "match" : 0,
    "fit" : "",
    "why": "",
    "description": "",
    "skills": "",
    "salary": "",
    "growth": "",
    "icon": "",
    "color": "",
    "domain" : ""
  }}
]

Make sure:
- The "why" field explains why the career is suitable.
- The "description" field is informative and clear.
- "Salary" is realistic for India in LPA.
- Only 3 careers are returned.

"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional AI career guidance expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=800
    )

    content = response.choices[0].message.content.strip()
    
    # 🔒 SAFETY CHECK 1: Empty response
    if not content:
        return {
            "error": "AI returned empty response"
    }

    # 🔒 SAFETY CHECK 2: JSON parsing
    try:
        results = json.loads(content)
    except json.JSONDecodeError:
        print("❌ INVALID JSON FROM AI:\n", content)
        return {
            "error": "Invalid JSON received from AI",
            "raw_response": content
        }

    # 🔒 SAFETY CHECK 3: Ensure list
    if not isinstance(results, list):
        return {
            "error": "AI response is not a list",
            "raw_response": results
        }

    for career in results:
        skills = career.get("skills", "")
        career["skills_list"] = [s.strip() for s in skills.split(",") if s.strip()]

        if not isinstance(career, dict):
            continue

        icon = career.get("icon", "").strip()

        if icon not in VALID_ICONS:
            career["icon"] = "work"  # default safe icon

        match_value = int(career.get("match", 0))
        match_value = max(0, min(match_value, 10))
        career["match_percent"] = match_value * 10

        growth_text = career.get("growth", "")
        growth_percent = extract_growth_percent(growth_text)

        career["growth_percent"] = growth_percent


    return results

@never_cache
def career_recom(request):
    results = None
    if not request.session.get("user_email"):
        return redirect("accounts:login")


    if request.method == "POST":
        user_email = request.session.get("user_email")
        education = request.POST.get("education")
        specialization = request.POST.get("specialization")

        expert_skills = request.POST.get("expert_skills")
        intermediate_skills = request.POST.get("intermediate_skills")

        soft_skills_list = request.POST.getlist("soft_skills")
        soft_skills = ", ".join(soft_skills_list)

        interests = request.POST.get("interests")

        personality_list = request.POST.getlist("personality")
        personality = ", ".join(personality_list)


        # 🔥 Combine education with specialization
        education_full = f"{education} ({specialization})"

        # 🔥 Combine skills for AI
        skills = (
            f"Expert Skills: {expert_skills} | "
            f"Intermediate Skills: {intermediate_skills} | "
            f"Soft Skills: {soft_skills}"
        )

        results = get_career_recommendation(
            education_full,
            skills,
            interests,
            personality
        )

        if isinstance(results, list) and results:
            avg_match = int(
                sum(c.get("match_percent", 0) for c in results) / len(results)
            )
        else:
            avg_match = 0

        CareerSubmission(
            user_email=user_email,
            education=education,
            specialization=specialization,
            expert_skills=expert_skills,
            intermediate_skills=intermediate_skills,
            soft_skills=soft_skills_list,
            interests=interests,
            personality=personality_list,
            results=results,
            avg_match=str(avg_match)
        ).save()    

        context = {
            "results": results,
            "avg_match": avg_match
        }


        return render(request, "career_recomendetion.html",context)


    return render(request, "career_recomendetion.html")

@csrf_exempt
@require_POST
def save_career(request):
    if not request.session.get("user_email"):
        return JsonResponse({"status": "error", "message": "Not logged in"}, status=401)

    user_email = request.session.get("user_email")
    career_name = request.POST.get("career_name")

    if not career_name:
        return JsonResponse({"status": "error", "message": "Career name missing"})

    try:
        SavedCareer(
            user_email=user_email,
            career_name=career_name
        ).save()

        return JsonResponse({"status": "success", "career": career_name, "redirect_url": reverse("career_analysis:gap_analyser")})

    except Exception:
        return JsonResponse({"status": "exists", "message": "Career already saved"})
    
@csrf_exempt
@require_POST
def reset_saved_careers(request):
    if not request.session.get("user_email"):
        return JsonResponse({"status": "error", "message": "Not logged in"}, status=401)

    user_email = request.session.get("user_email")

    SavedCareer.objects(user_email=user_email).delete()

    return JsonResponse({"status": "success"})
    
def gap_analyzer(request):
    return render(request, 'gap_analyzer.html')