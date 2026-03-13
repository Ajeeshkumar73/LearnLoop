import os, json, re, random
from django.shortcuts import render, redirect
from groq import Groq
from dotenv import load_dotenv
from .models import CareerSubmission, SavedCareer, SkillProgress, UserProfile, CompletedRoadmapSkill, CachedRoadmap
from django.http import JsonResponse, HttpResponse
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

    # Clear cached roadmaps so fresh ones are generated for new career
    CachedRoadmap.objects(user_email=user_email).delete()

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

    # ---------- Roadmaps + Progress (WITH CACHING) ----------
    MAX_ROADMAPS = 3
    count = 0

    # Collect gap/improving skills, mix of technical and soft
    gap_skills = [s for s in skills_sorted if s["status"] in ["gap", "improving"]]
    print(f"🎯 Skills needing roadmaps: {[(s['name'], s['type'], s['status']) for s in gap_skills]}")

    roadmaps = []
    for skill in gap_skills:
        if count >= MAX_ROADMAPS:
            break

        # Check cache first
        cached = CachedRoadmap.objects(
            user_email=user_email,
            skill_name=skill["name"]
        ).first()

        if cached and cached.roadmap_data:
            print(f"✅ Using cached roadmap for '{skill['name']}'")
            roadmap = cached.roadmap_data
        else:
            print(f"🔄 Generating roadmap {count+1}/{MAX_ROADMAPS}: '{skill['name']}' ({skill['type']})")
            roadmap = generate_skill_roadmap(skill["name"], skill["type"])
            # Save to cache
            CachedRoadmap.objects(
                user_email=user_email,
                skill_name=skill["name"]
            ).update_one(
                set__skill_type=skill["type"],
                set__roadmap_data=roadmap,
                upsert=True
            )
            print(f"💾 Cached roadmap for '{skill['name']}'")

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

    print(f"✅ Total roadmaps loaded: {len(roadmaps)}")


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

Create a 4-WEEK learning roadmap to master the SOFT SKILL "{skill_name}".

MANDATORY RULES:
- Response MUST be valid JSON ONLY — no markdown, no code fences, no explanation
- Exactly 4 weeks
- Every week MUST include AT LEAST 2 resources with real working URLs
- Videos MUST be from YouTube, TED, Coursera, Udemy, or LinkedIn Learning
- NO empty resources arrays allowed
- Practical real-life exercises are REQUIRED

Return this EXACT JSON structure:

{{
  "skill": "{skill_name}",
  "type": "Soft Skill",
  "roadmap": [
    {{
      "week": "Week 1",
      "goal": "Specific sub-skill goal",
      "how": "Step-by-step learning plan",
      "resources": [
        {{ "title": "Video Title", "url": "https://youtube.com/watch?v=..." }},
        {{ "title": "Course or Article", "url": "https://coursera.org/..." }}
      ],
      "practice": "Concrete real-world practice task"
    }}
  ]
}}
"""
    else:
        return f"""
You are a senior technical mentor.

Create a 4-WEEK learning roadmap to master the TECHNICAL SKILL "{skill_name}".

MANDATORY RULES:
- Response MUST be valid JSON ONLY — no markdown, no code fences, no explanation
- Exactly 4 weeks
- EVERY WEEK must include at least 2 resources with real working URLs
- Use platforms like: YouTube, Coursera, freeCodeCamp, GeeksforGeeks, W3Schools, MDN, official docs
- Hands-on mini-project EVERY WEEK
- NO empty resources arrays allowed

Return this EXACT JSON structure:

{{
  "skill": "{skill_name}",
  "type": "Technical Skill",
  "roadmap": [
    {{
      "week": "Week 1",
      "goal": "Specific technical concept",
      "how": "Step-by-step learning plan",
      "resources": [
        {{ "title": "Video Tutorial", "url": "https://youtube.com/watch?v=..." }},
        {{ "title": "Official Docs / Site", "url": "https://developer.mozilla.org/..." }}
      ],
      "practice": "Mini-project or coding task"
    }}
  ]
}}
"""


def extract_json_from_text(text):
    """Try to extract valid JSON from AI response that may contain markdown or extra text."""
    text = text.strip()

    # 1. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences: ```json ... ``` or ``` ... ```
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Find the first { ... } or [ ... ] block
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start != -1:
            end = text.rfind(end_char)
            if end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass

    return None


def sanitize_roadmap_urls(roadmap):
    """
    Fix AI-generated URLs:
    - YouTube direct video links (watch?v=...) are hallucinated and don't exist
    - Convert them to YouTube search URLs based on the resource title
    - This guarantees all links always work
    """
    if not isinstance(roadmap, dict):
        return roadmap

    from urllib.parse import quote_plus

    for step in roadmap.get("roadmap", []):
        if not isinstance(step, dict):
            continue
        resources = step.get("resources", [])
        if not isinstance(resources, list):
            continue

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            url = resource.get("url", "")
            title = resource.get("title", "")

            # Fix YouTube direct links → search URLs
            if any(pattern in url for pattern in [
                "youtube.com/watch", "youtu.be/", "youtube.com/v/",
                "youtube.com/embed", "youtube.com/..."
            ]):
                search_query = title if title else roadmap.get("skill", "tutorial")
                resource["url"] = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"

            # Fix Coursera fake links → search URLs
            elif "coursera.org/..." in url or ("coursera.org" in url and "/learn/" not in url and "/search" not in url):
                search_query = title if title else roadmap.get("skill", "course")
                resource["url"] = f"https://www.coursera.org/search?query={quote_plus(search_query)}"

            # Fix generic placeholder URLs
            elif url.endswith("...") or url.endswith("/..."):
                search_query = title if title else roadmap.get("skill", "tutorial")
                resource["url"] = f"https://www.google.com/search?q={quote_plus(search_query)}"

    return roadmap


def generate_skill_roadmap(skill_name, skill_type):
    prompt = build_roadmap_prompt(skill_name, skill_type)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You MUST respond with ONLY valid JSON. No text, no markdown, no code fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )

        content = response.choices[0].message.content.strip()
        print(f"📦 AI roadmap response length for '{skill_name}': {len(content)} chars")

        roadmap = extract_json_from_text(content)

        if roadmap and isinstance(roadmap, dict):
            # Ensure required keys exist
            roadmap.setdefault("skill", skill_name)
            roadmap.setdefault("type", skill_type)
            roadmap.setdefault("roadmap", [])
            # Fix hallucinated URLs
            roadmap = sanitize_roadmap_urls(roadmap)
            print(f"✅ Roadmap parsed for '{skill_name}': {len(roadmap.get('roadmap', []))} weeks")
            return roadmap
        else:
            print(f"⚠️ Could not parse AI JSON for '{skill_name}', using fallback")
            print(f"   Raw response preview: {content[:200]}...")

    except Exception as e:
        if "rate limit" in str(e).lower():
            print(f"⚠️ Rate limit reached for '{skill_name}' – using fallback")
        else:
            print(f"❌ AI error for '{skill_name}':", e)

    # Fallback roadmap (used if AI fails or error occurs)
    return {
        "skill": skill_name,
        "type": skill_type,
        "roadmap": [
            {
                "week": "Week 1",
                "goal": f"Introduction to {skill_name}",
                "how": f"Start by understanding the core concepts and fundamentals of {skill_name}. Read introductory articles and watch beginner tutorials.",
                "resources": [
                    {"title": f"{skill_name} Crash Course - YouTube", "url": f"https://www.youtube.com/results?search_query={skill_name.replace(' ', '+')}+tutorial"},
                    {"title": f"Learn {skill_name} - GeeksforGeeks", "url": f"https://www.geeksforgeeks.org/search?q={skill_name.replace(' ', '+')}"}
                ],
                "practice": f"Set up your learning environment and complete a basic {skill_name} exercise."
            },
            {
                "week": "Week 2",
                "goal": f"Core {skill_name} Concepts",
                "how": f"Deep dive into intermediate concepts. Follow along with structured tutorials and documentation.",
                "resources": [
                    {"title": f"{skill_name} Full Course - YouTube", "url": f"https://www.youtube.com/results?search_query={skill_name.replace(' ', '+')}+full+course"},
                    {"title": f"{skill_name} - W3Schools", "url": f"https://www.w3schools.com/search/search_result.asp?search_term={skill_name.replace(' ', '+')}"}
                ],
                "practice": f"Build a small project applying core {skill_name} concepts."
            },
            {
                "week": "Week 3",
                "goal": f"Advanced {skill_name} Techniques",
                "how": f"Explore advanced topics, best practices, and real-world patterns used in industry.",
                "resources": [
                    {"title": f"Advanced {skill_name} - YouTube", "url": f"https://www.youtube.com/results?search_query=advanced+{skill_name.replace(' ', '+')}"},
                    {"title": f"{skill_name} - freeCodeCamp", "url": f"https://www.freecodecamp.org/news/search/?query={skill_name.replace(' ', '+')}"}
                ],
                "practice": f"Implement an advanced feature or solve a challenging problem using {skill_name}."
            },
            {
                "week": "Week 4",
                "goal": f"Mastery & Real-World Application",
                "how": f"Apply all learned concepts to a comprehensive project. Review and refine your understanding.",
                "resources": [
                    {"title": f"{skill_name} Projects - YouTube", "url": f"https://www.youtube.com/results?search_query={skill_name.replace(' ', '+')}+project"},
                    {"title": f"{skill_name} - Coursera", "url": f"https://www.coursera.org/search?query={skill_name.replace(' ', '+')}"}
                ],
                "practice": f"Complete a portfolio-worthy project demonstrating your {skill_name} skills."
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


# =====================================================
# NEW: ROADMAP PAGE VIEW
# =====================================================

@never_cache
def roadmap_page(request):
    """Dedicated roadmap page with full structure, resources, custom duration, and skill completion"""
    if not request.session.get("user_email"):
        return redirect("accounts:login")

    user_email = request.session["user_email"]

    saved = SavedCareer.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()

    if not saved or not submission:
        return redirect("career_analysis:career_recom")

    # Find saved career details
    career_data = next(
        (c for c in submission.results if c["career"] == saved.career_name),
        None
    )
    if not career_data:
        return redirect("career_analysis:career_recom")

    # Custom duration from GET param (default 4 weeks per skill)
    custom_duration = int(request.GET.get("duration", 4))
    custom_duration = max(2, min(custom_duration, 12))  # Clamp between 2-12

    # Normalize user skills
    def normalize(skill):
        return skill.strip().lower()

    user_expert = [normalize(s) for s in (submission.expert_skills.split(",") if submission.expert_skills else [])]
    user_intermediate = [normalize(s) for s in (submission.intermediate_skills.split(",") if submission.intermediate_skills else [])]
    user_soft = [normalize(s) for s in (submission.soft_skills.split(",") if submission.soft_skills else [])]

    # Build skills list
    all_skills = []
    for skill in career_data.get("required_skills_list", []):
        skill_name = skill.strip()
        norm = normalize(skill_name)
        if norm in user_expert or get_close_matches(norm, user_expert, cutoff=0.8):
            status = "matched"
        elif norm in user_intermediate or get_close_matches(norm, user_intermediate, cutoff=0.8):
            status = "improving"
        else:
            status = "gap"
        all_skills.append({"name": skill_name, "type": "Technical Skill", "status": status})

    for skill in career_data.get("soft_skills_list", []):
        skill_name = skill.strip()
        norm = normalize(skill_name)
        if norm in user_soft or get_close_matches(norm, user_soft, cutoff=0.8):
            status = "matched"
        else:
            status = "gap"
        all_skills.append({"name": skill_name, "type": "Soft Skill", "status": status})

    # Get gap/improving skills for roadmaps
    gap_skills = [s for s in all_skills if s["status"] in ["gap", "improving"]]

    # Progress map
    progress_entries = SkillProgress.objects(user_email=user_email)
    progress_map = {p.skill_name: p.completed_weeks for p in progress_entries}

    # Completed skills from roadmap
    completed_skills = CompletedRoadmapSkill.objects(user_email=user_email)
    completed_skill_names = [cs.skill_name for cs in completed_skills]

    # Generate roadmaps (limit to 5 for performance)
    MAX_ROADMAPS = 5
    roadmaps = []
    for i, skill in enumerate(gap_skills[:MAX_ROADMAPS]):
        # Check cache first
        cached = CachedRoadmap.objects(
            user_email=user_email,
            skill_name=skill["name"]
        ).first()

        if cached and cached.roadmap_data:
            print(f"✅ Using cached roadmap for '{skill['name']}'")
            roadmap = cached.roadmap_data
        else:
            print(f"🔄 Generating roadmap for '{skill['name']}' ({skill['type']})")
            roadmap = generate_skill_roadmap(skill["name"], skill["type"])
            # Save to cache
            CachedRoadmap.objects(
                user_email=user_email,
                skill_name=skill["name"]
            ).update_one(
                set__skill_type=skill["type"],
                set__roadmap_data=roadmap,
                upsert=True
            )
            print(f"💾 Cached roadmap for '{skill['name']}'")

        completed = len(progress_map.get(skill["name"], []))
        total = len(roadmap.get("roadmap", []))
        percent = int((completed / total) * 100) if total > 0 else 0

        roadmap.update({
            "completed": completed,
            "total": total,
            "percent": percent,
            "completed_weeks": progress_map.get(skill["name"], []),
            "is_completed_skill": skill["name"] in completed_skill_names,
            "skill_status": skill["status"],
            "index": i
        })
        roadmaps.append(roadmap)

    return render(request, "roadmap_page.html", {
        "career_name": career_data["career"],
        "career_icon": saved.career_icon,
        "match_percent": career_data.get("match_percent", 0),
        "roadmaps": roadmaps,
        "all_skills": all_skills,
        "gap_skills": gap_skills,
        "completed_skill_names": completed_skill_names,
        "custom_duration": custom_duration,
        "total_gap": len(gap_skills),
        "total_completed": len(completed_skill_names),
    })


@csrf_exempt
@require_POST
def add_completed_skill(request):
    """Mark a skill as completed from roadmap checkbox"""
    user_email = request.session.get("user_email")
    if not user_email:
        return JsonResponse({"status": "unauthorized"}, status=401)

    skill_name = request.POST.get("skill_name")
    skill_type = request.POST.get("skill_type", "Technical Skill")
    action = request.POST.get("action", "add")  # "add" or "remove"

    if action == "remove":
        CompletedRoadmapSkill.objects(
            user_email=user_email,
            skill_name=skill_name
        ).delete()
        return JsonResponse({"status": "removed"})

    # Check if already exists
    existing = CompletedRoadmapSkill.objects(
        user_email=user_email,
        skill_name=skill_name
    ).first()

    if existing:
        return JsonResponse({"status": "already_exists"})

    CompletedRoadmapSkill(
        user_email=user_email,
        skill_name=skill_name,
        skill_type=skill_type
    ).save()

    # Also update user profile skills
    profile = UserProfile.objects(user_email=user_email).first()
    if profile:
        current = [s.strip() for s in profile.current_skills.split(",") if s.strip()] if profile.current_skills else []
        if skill_name not in current:
            current.append(skill_name)
            profile.current_skills = ", ".join(current)
            profile.save()

    return JsonResponse({"status": "added", "skill": skill_name})


# =====================================================
# NEW: PROFILE PAGE VIEW
# =====================================================

@never_cache
def profile_page(request):
    """Complete profile page with resume builder"""
    if not request.session.get("user_email"):
        return redirect("accounts:login")

    user_email = request.session["user_email"]

    # Get or create profile
    profile = UserProfile.objects(user_email=user_email).first()
    if not profile:
        profile = UserProfile(user_email=user_email)
        profile.save()

    # Get related data
    saved_career = SavedCareer.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()
    completed_skills = CompletedRoadmapSkill.objects(user_email=user_email)

    # Auto-populate from existing data
    from accounts.models import Profile as AccountProfile
    account_profile = AccountProfile.objects(user=user_email).first()

    if account_profile and not profile.full_name:
        profile.full_name = account_profile.full_name
        profile.save()

    if submission and not profile.education:
        profile.education = submission.education or ""
        profile.specialization = submission.specialization or ""
        if submission.expert_skills:
            existing = profile.current_skills or ""
            combined = set(s.strip() for s in existing.split(",") if s.strip())
            combined.update(s.strip() for s in submission.expert_skills.split(",") if s.strip())
            profile.current_skills = ", ".join(combined)
        profile.save()

    if saved_career and not profile.target_role:
        profile.target_role = saved_career.career_name
        profile.save()

    # Build completed skills list for display
    completed_skill_list = [cs.skill_name for cs in completed_skills]

    return render(request, "profile_page.html", {
        "profile": profile,
        "user_email": user_email,
        "saved_career": saved_career,
        "submission": submission,
        "completed_skills": completed_skill_list,
    })


@csrf_exempt
@require_POST
def update_profile(request):
    """Update user profile data"""
    user_email = request.session.get("user_email")
    if not user_email:
        return JsonResponse({"status": "unauthorized"}, status=401)

    profile = UserProfile.objects(user_email=user_email).first()
    if not profile:
        profile = UserProfile(user_email=user_email)

    # Update fields from POST
    fields = [
        "full_name", "phone", "current_occupation", "target_role",
        "education", "specialization", "current_skills", "bio",
        "linkedin_url", "github_url", "location", "profile_pic"
    ]

    for field in fields:
        value = request.POST.get(field)
        if value is not None:
            setattr(profile, field, value)

    # Complex fields (JSON serialized or comma-separated)
    complex_fields = ["education_list", "projects", "certifications", "achievements", "hobbies"]
    for field in complex_fields:
        value = request.POST.get(field)
        if value:
            try:
                import json
                parsed_value = json.loads(value)
                setattr(profile, field, parsed_value)
            except Exception:
                # Fallback for simple list fields (strings)
                if field in ["certifications", "achievements", "hobbies"]:
                    parsed_value = [s.strip() for s in value.split(",") if s.strip()]
                    setattr(profile, field, parsed_value)
                else:
                    print(f"Error parsing complex field {field}: {value}")

    from datetime import datetime
    profile.updated_at = datetime.utcnow()
    profile.save()

    return JsonResponse({"status": "success"})


@never_cache
def generate_resume(request):
    """Generate a downloadable HTML resume"""
    if not request.session.get("user_email"):
        return redirect("accounts:login")

    user_email = request.session["user_email"]
    profile = UserProfile.objects(user_email=user_email).first()
    saved_career = SavedCareer.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()
    completed_skills = CompletedRoadmapSkill.objects(user_email=user_email)

    if not profile:
        return redirect("career_analysis:profile")

    # Build skills
    expert_skills = [s.strip() for s in (submission.expert_skills.split(",") if submission and submission.expert_skills else [])]
    intermediate_skills = [s.strip() for s in (submission.intermediate_skills.split(",") if submission and submission.intermediate_skills else [])]
    completed_list = [cs.skill_name for cs in completed_skills]
    
    # Also fetch skills from UserProfile if any
    profile_skills = [s.strip() for s in (profile.current_skills.split(",") if profile and profile.current_skills else [])]
    
    all_skills = list(set(expert_skills + intermediate_skills + completed_list + profile_skills))

    # Job Description Tailoring
    jd_text = request.POST.get("job_description") if request.method == "POST" else None
    tailored_summary = None
    if jd_text:
        # Generate summary using AI
        prompt = f"""
        You are a professional resume writer. 
        Create a powerful, 2-3 sentence professional summary for a resume based on the following:
        
        USER PROFILE:
        - Name: {profile.full_name}
        - Bio/Background: {profile.bio}
        - Current Occupation: {profile.current_occupation}
        - Skills: {", ".join(all_skills)}
        
        TARGET JOB DESCRIPTION:
        {jd_text[:2000]} # Limit to avoid issues
        
        Requirements:
        1. Highlight how the user's skills match the job.
        2. Keep it professional and action-oriented.
        3. Do NOT include any placeholders like [Name].
        4. Return ONLY the text of the summary.
        """
        tailored_summary = generate_with_fallback(prompt)

    return render(request, "resume_template.html", {
        "profile": profile,
        "user_email": user_email,
        "saved_career": saved_career,
        "all_skills": all_skills,
        "expert_skills": expert_skills,
        "intermediate_skills": intermediate_skills,
        "completed_skills": completed_list,
        "tailored_summary": tailored_summary,
        "is_tailored": bool(jd_text)
    })


def extract_skills_from_jd(job_description):
    """Uses Groq to extract structured skills from a Job Description"""
    prompt = f"""
    You are an AI Technical Recruiter. Analyze the Job Description below and extract ONLY the specific skills required.
    Categorize them into 'Technical Skills' and 'Soft Skills'.

    MANDATORY: Return ONLY valid JSON in the exact structure below. No extra text.
    {{
      "technical_skills": ["Skill1", "Skill2", ...],
      "soft_skills": ["Skill1", "Skill2", ...]
    }}

    Job Description:
    {job_description}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a professional recruiting assistant. You always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        data = extract_json_from_text(content)
        if data and isinstance(data, dict):
            # Ensure keys exist
            data.setdefault("technical_skills", [])
            data.setdefault("soft_skills", [])
            return data
    except Exception as e:
        print("❌ JD Skill Extraction Error:", e)
    
    return None


@never_cache
def job_analyzer(request):
    """Page to paste JD, extract skills, and show gaps/roadmaps"""
    if not request.session.get("user_email"):
        return redirect("accounts:login")

    user_email = request.session["user_email"]
    profile = UserProfile.objects(user_email=user_email).first()
    submission = CareerSubmission.objects(user_email=user_email).first()
    
    analysis = None
    jd_text = ""

    if request.method == "POST":
        jd_text = request.POST.get("job_description", "")
        if jd_text.strip():
            extracted = extract_skills_from_jd(jd_text)
            if extracted:
                # 1. Gather all user skills for comparison
                user_skills_raw = []
                if profile and profile.current_skills:
                    user_skills_raw.extend(profile.current_skills.split(","))
                if submission:
                    if submission.expert_skills:
                        user_skills_raw.extend(submission.expert_skills.split(","))
                    if submission.intermediate_skills:
                        user_skills_raw.extend(submission.intermediate_skills.split(","))
                    # Handle soft_skills if stored as list or string
                    if submission.soft_skills:
                        if isinstance(submission.soft_skills, list):
                            user_skills_raw.extend(submission.soft_skills)
                        else:
                            user_skills_raw.extend(submission.soft_skills.split(","))

                # Normalize user skills
                user_skills = [s.strip().lower() for s in user_skills_raw if s.strip()]
                
                # 2. Compare extracted skills with user skills
                def analyze_skills(extracted_list, skill_type):
                    matched = []
                    gap = []
                    for skill in extracted_list:
                        skill_norm = skill.strip().lower()
                        if skill_norm in user_skills or get_close_matches(skill_norm, user_skills, cutoff=0.75):
                            matched.append(skill)
                        else:
                            gap.append(skill)
                    return matched, gap

                tech_matched, tech_gap = analyze_skills(extracted["technical_skills"], "Technical Skill")
                soft_matched, soft_gap = analyze_skills(extracted["soft_skills"], "Soft Skill")

                # 3. Handle Roadmap Generation (if requested)
                # For now, just identify the gaps. We'll show a "Generate Roadmap" button for these.
                
                analysis = {
                    "tech_matched": tech_matched,
                    "tech_gap": tech_gap,
                    "soft_matched": soft_matched,
                    "soft_gap": soft_gap,
                    "match_score": int(((len(tech_matched) + len(soft_matched)) / 
                                       (max(1, len(extracted["technical_skills"]) + len(extracted["soft_skills"])))) * 100)
                }

    return render(request, "job_analyzer.html", {
        "analysis": analysis,
        "jd_text": jd_text,
    })


def get_skill_roadmap(request):
    """AJAX endpoint to generate/fetch a roadmap for a specific skill"""
    skill_name = request.GET.get("skill")
    skill_type = request.GET.get("type", "Technical Skill")
    user_email = request.session.get("user_email")

    if not skill_name:
        return JsonResponse({"error": "No skill provided"}, status=400)

    # 1. Check Cache
    if user_email:
        cached = CachedRoadmap.objects(
            user_email=user_email,
            skill_name=skill_name
        ).first()
        if cached and cached.roadmap_data:
            return JsonResponse(cached.roadmap_data)

    # 2. Generate if not cached
    roadmap = generate_skill_roadmap(skill_name, skill_type)

    # 3. Save to cache
    if user_email and roadmap:
        CachedRoadmap.objects(
            user_email=user_email,
            skill_name=skill_name
        ).update_one(
            set__skill_type=skill_type,
            set__roadmap_data=roadmap,
            upsert=True
        )

    return JsonResponse(roadmap)


def mentor_dashboard(request):
    user_email = request.session.get('user_email')
    if not user_email:
        return redirect('accounts:login')
    
    user = User.objects(email=user_email).first()
    if not user or getattr(user, 'role', 'student') != 'mentor':
        return redirect('career_analysis:career_recom')
    
    # Get some stats for the mentor
    # For now, just dummy data
    stats = {
        'total_students': 42,
        'active_sessions': 12,
        'pending_requests': 5,
        'average_rating': 4.8
    }
    
    return render(request, 'mentor_dashboard.html', {'user': user, 'stats': stats})