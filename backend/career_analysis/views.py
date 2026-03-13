import os, json, re, random
from django.shortcuts import render, redirect
from groq import Groq
from dotenv import load_dotenv
from .models import CareerSubmission, SavedCareer, SkillProgress
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from difflib import get_close_matches

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
4. Provide **required technical skills** (comma-separated)
5. Provide **important soft skills** (comma-separated)
6. Provide a **realistic salary range in India (in LPA)** for entry-level to experienced professionals.
7.Future growth outlook
8. Suggest an appropriate **icon** (use one from: {', '.join(VALID_ICONS)}) 
9. Provide a **UI color**
10. Provide a **domain/industry category**.

Return ONLY valid JSON in the EXACT format below, with **3 career objects**, ranked from most to least suitable:

[
  {{
    "career": "",
    "match" : 0,
    "fit" : "",
    "why": "",
    "description": "",
    "required_skills": "",
    "soft_skills": "",
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
        if not isinstance(career, dict):
            continue

            # --- Technical skills ---
        tech_skills = career.get("required_skills", "")
        career["required_skills_list"] = [
            s.strip() for s in tech_skills.split(",") if s.strip()
        ]

        # --- Soft skills ---
        soft_skills = career.get("soft_skills", "")
        career["soft_skills_list"] = [
            s.strip() for s in soft_skills.split(",") if s.strip()
        ]

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
    if not request.session.get("user_email"):
        return redirect("accounts:login")
    
    user_email = request.session["user_email"]

    saved_career = SavedCareer.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()

    results = None
    avg_match = None
    
    if submission:
        results = submission.results
        avg_match = submission.avg_match

    

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

        avg_match = int(
            sum(c.get("match_percent", 0) for c in results) / len(results)
        )

        CareerSubmission.objects(user_email=user_email).update_one(
            set__education=str(education),
            set__specialization=str(specialization),
            set__expert_skills=expert_skills,
            set__intermediate_skills=intermediate_skills,
            set__soft_skills=soft_skills,          # ✅ list → ListField
            set__interests=interests,
            set__personality=personality,          # ✅ list → ListField
            set__results=results,                  # ✅ list of dict
            set__avg_match=str(avg_match),
            upsert=True
        )


        # ✅ STORE IN SESSION
        request.session["career_results"] = results
        request.session["avg_match"] = avg_match



    return render(request, "career_recomendetion.html", {
        "results": results,
        "avg_match": avg_match,
        "saved_career" : saved_career
    })


@csrf_exempt
@require_POST
def save_career(request):
    user_email = request.session.get("user_email")
    if not user_email:
        return JsonResponse({"status": "unauthorized"})

    career_name = request.POST.get("career_name")
    career_icon = request.POST.get("career_icon", "work")

    if SavedCareer.objects(user_email=user_email).first():
        return JsonResponse({"status": "exists"})


    SavedCareer(
        user_email=user_email,
        career_name=career_name,
        career_icon=career_icon
    ).save()

    return JsonResponse({
        "status": "success",
        "redirect_url": reverse("career_analysis:gap_analyzer")
  
    })

    

@csrf_exempt
@require_POST
def reset_saved_careers(request):
    if not request.session.get("user_email"):
        return JsonResponse({"status": "error"}, status=401)

    user_email = request.session.get("user_email")

    # delete saved career
    SavedCareer.objects(user_email=user_email).delete()

    CareerSubmission.objects(user_email=user_email).delete()

    # CLEAR SESSION RESULTS
    request.session.pop("career_results", None)
    request.session.pop("avg_match", None)

    return JsonResponse({"status": "success"})



def gap_analyzer(request):
    if not request.session.get("user_email"):
        return redirect("accounts:login")

    user_email = request.session["user_email"]

    saved = SavedCareer.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()

    if not saved or not submission:
        return redirect("career_analysis:career_recom")

    # Find saved career details from submission results
    career_data = next(
        (c for c in submission.results if c["career"] == saved.career_name),
        None
    )

    if not career_data:
        return redirect("career_analysis:career_recom")

    # --- Helper: normalize skill names ---
    def normalize(skill):
        return skill.strip().lower()

    # --- Normalize user skills ---
    user_expert_skills = [normalize(s) for s in (submission.expert_skills.split(",") if submission.expert_skills else [])]
    user_intermediate_skills = [normalize(s) for s in (submission.intermediate_skills.split(",") if submission.intermediate_skills else [])]
    user_soft_skills = [normalize(s) for s in (submission.soft_skills.split(",") if submission.soft_skills else [])]

    skills = []

    # --- Add technical skills with fuzzy matching ---
    for skill in career_data.get("required_skills_list", []):
        skill_name = skill.strip()
        norm_skill = normalize(skill_name)

        if norm_skill in user_expert_skills or get_close_matches(norm_skill, user_expert_skills, cutoff=0.8):
            status = "matched"
            current = "Advanced"
        elif norm_skill in user_intermediate_skills or get_close_matches(norm_skill, user_intermediate_skills, cutoff=0.8):
            status = "improving"
            current = "Intermediate"
        else:
            status = "gap"
            current = "Beginner"

        skills.append({
            "name": skill_name,
            "type": "Technical Skill",
            "icon": "dataset",
            "status": status,
            "current": current,
            "required": "Advanced",
        })

    # --- Add soft skills with fuzzy matching ---
    for soft_skill in career_data.get("soft_skills_list", []):
        skill_name = soft_skill.strip()
        norm_skill = normalize(skill_name)

        if norm_skill in user_soft_skills or get_close_matches(norm_skill, user_soft_skills, cutoff=0.8):
            status = "matched"
            current = "Advanced"
        else:
            status = "gap"
            current = "Beginner"

        skills.append({
            "name": skill_name,
            "type": "Soft Skill",
            "icon": "psychology",
            "status": status,
            "current": current,
            "required": "Advanced",
        })
    status_order = {"gap": 0, "improving": 1, "matched": 2}
    skills_sorted = sorted(skills, key=lambda x: status_order[x["status"]])    

    # --- Build chart for top 5 skills ---
    chart_skills = [
        {
            "name": s["name"][:],
            "current": 80 if s["status"] == "matched" else 50 if s["status"] == "improving" else 30,
            "target": 80,
            "status": s["status"],
            "label": s["status"].title()
        }
        for s in skills_sorted[:7]
    ]

      # ---------- Progress Map ----------
    progress_entries = SkillProgress.objects(user_email=user_email)
    progress_map = {p.skill_name: p.completed_weeks for p in progress_entries}

    # ---------- Roadmaps + Progress ----------
    MAX_ROADMAPS = 3  #  limit AI calls per request
    count = 0

    roadmaps = []
    for skill in skills_sorted:
        if skill["status"] in ["gap", "improving"] and count < MAX_ROADMAPS:
            roadmap = generate_skill_roadmap(skill["name"], skill["type"])
            count += 1

            completed = len(progress_map.get(skill["name"], []))
            total = len(roadmap.get("roadmap", []))
            percent = int((completed / total) * 100) if total > 0 else 0

            roadmap.update({
                "completed": completed,
                "total": total,
                "percent": percent,
                "completed_weeks": progress_map.get(skill["name"], [])
            })

            roadmaps.append(roadmap)


    return render(request, "gap_analyzer.html", {
        "career_name": career_data["career"],
        "career_icon": saved.career_icon,
        "match_percent": career_data.get("match_percent", 0),
        "fit": career_data.get("fit", ""),
        "skills": skills_sorted,
        "chart_skills": chart_skills,
        "roadmaps": roadmaps,
        "progress_map": progress_map
    })

def build_roadmap_prompt(skill_name, skill_type):
    if skill_type == "Soft Skill":
        return f"""
You are a professional career coach.

Create a STRICT 3-MONTH (12-WEEK) learning roadmap to master the SOFT SKILL "{skill_name}".

MANDATORY RULES:
- Response MUST be valid JSON ONLY
- Every week MUST include AT LEAST 2 VIDEO LINKS
- Videos MUST be from YouTube, TED, Coursera, Udemy, or LinkedIn Learning
- NO empty resources arrays allowed
- Practical real-life exercises are REQUIRED

STRUCTURE (DO NOT CHANGE):

{{
  "skill": "{skill_name}",
  "type": "Soft Skill",
  "roadmap": [
    {{
      "week": "Week 1",
      "goal": "Specific sub-skill goal",
      "how": "Step-by-step learning plan",
      "resources": [
        {{ "title": "Video Title", "url": "https://youtube.com/..." }},
        {{ "title": "Video Title", "url": "https://coursera.org/..." }}
      ],
      "practice": "Concrete real-world practice task"
    }}
  ]
}}

DO NOT add explanations or text outside JSON.
"""
    else:
        return f"""
You are a senior technical mentor.

Create a STRICT 3-MONTH (12-WEEK) learning roadmap to master the TECHNICAL SKILL "{skill_name}".

MANDATORY RULES:
- Response MUST be valid JSON ONLY
- EVERY WEEK must include:
  - At least 1 VIDEO
  - At least 1 LEARNING WEBSITE or OFFICIAL DOCUMENTATION
- Use platforms like:
  YouTube, Coursera, freeCodeCamp, GeeksforGeeks, W3Schools, MDN, official docs
- Hands-on mini-project EVERY WEEK
- NO empty resources arrays allowed

STRUCTURE (DO NOT CHANGE):

{{
  "skill": "{skill_name}",
  "type": "Technical Skill",
  "roadmap": [
    {{
      "week": "Week 1",
      "goal": "Specific technical concept",
      "how": "Step-by-step learning plan",
      "resources": [
        {{ "title": "Video Tutorial", "url": "https://youtube.com/..." }},
        {{ "title": "Official Docs / Site", "url": "https://developer.mozilla.org/..." }}
      ],
      "practice": "Mini-project or coding task"
    }}
  ]
}}

DO NOT add explanations or text outside JSON.
"""

def generate_skill_roadmap(skill_name, skill_type):
    prompt = build_roadmap_prompt(skill_name, skill_type)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You MUST respond with ONLY valid JSON. No text, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=700
        )

        content = response.choices[0].message.content.strip()
        
        try:
            # Attempt to parse JSON
            roadmap = json.loads(content)
            return roadmap
        except json.JSONDecodeError:
            print("⚠️ AI response is not valid JSON, returning raw content")
            return {"raw": content}

    except Exception as e:
        if "rate limit" in str(e).lower():
            print("⚠️ Rate limit reached – please retry later")
        else:
            print("❌ AI error:", e)

    # Fallback roadmap (used if AI fails or error occurs)
    return {
        "skill": skill_name,
        "type": skill_type,
        "roadmap": [
            {
                "week": "Week 1",
                "goal": "Fundamentals",
                "how": "Learn core concepts and basics",
                "resources": [
                    {"title": "Intro Video", "url": "https://youtube.com"}
                ],
                "practice": "Basic practice task"
            }
        ]
    }


def toggle_week_progress(request):
    if request.method == "POST":
        user_email = request.session.get("user_email")
        skill = request.POST.get("skill")
        week = int(request.POST.get("week"))

        progress = SkillProgress.objects(
            user_email=user_email,
            skill_name=skill
        ).first()

        if not progress:
            progress = SkillProgress(
                user_email=user_email,
                skill_name=skill,
                completed_weeks=[]
            )

        if week in progress.completed_weeks:
            progress.completed_weeks.remove(week)
            completed = False
        else:
            progress.completed_weeks.append(week)
            completed = True

        progress.save()

        return JsonResponse({
            "completed": completed,
            "total_completed": len(progress.completed_weeks)
        })

def generate_with_fallback(prompt): 
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        return response.choices[0].message.content

    except Exception as e:
        # Check if it's a rate limit issue
        if "rate limit" in str(e).lower():
            print("⚠️ Rate limit reached – fallback used")
        else:
            print("❌ AI error:", e)
        return None

