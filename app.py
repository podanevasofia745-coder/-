import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


EXPERIENCE_LEVELS = {
    "без опыта": 0,
    "стажёр": 0,
    "до 1 года": 1,
    "1-3 года": 2,
    "1-3": 2,
    "3-5 лет": 3,
    "3-5": 3,
    "5+ лет": 4,
    "5+": 4,
}


def normalize_skills(skills_text):
    if isinstance(skills_text, list):
        return [s.strip().lower() for s in skills_text]
    return [s.strip().lower() for s in re.split(r"[,;]", skills_text) if s.strip()]


def experience_score(user_exp, required_exp):
    user_level = EXPERIENCE_LEVELS.get(user_exp.lower().strip(), 1)
    req_level = EXPERIENCE_LEVELS.get(required_exp.lower().strip(), 2)
    if user_level >= req_level:
        return 1.0
    if user_level == req_level - 1:
        return 0.6
    return 0.2


def skills_score(user_skills, required_skills):
    if not required_skills:
        return 0.5
    user_set = set(normalize_skills(user_skills))
    req_set = set(s.lower() for s in required_skills)
    if not req_set:
        return 0.5
    overlap = user_set & req_set
    partial = sum(
        0.5 for u in user_set for r in req_set if u in r or r in u
    )
    score = (len(overlap) + partial * 0.3) / len(req_set)
    return min(score, 1.0)


def location_score(user_city, vacancy_city):
    if not user_city or not vacancy_city:
        return 0.5
    if user_city.lower().strip() == vacancy_city.lower().strip():
        return 1.0
    remote_cities = {"удалённо", "remote", "любой"}
    if user_city.lower() in remote_cities or vacancy_city.lower() in remote_cities:
        return 0.8
    return 0.3


def salary_score(expectation, salary_min, salary_max):
    if not expectation:
        return 0.5
    try:
        exp = int(expectation)
    except (TypeError, ValueError):
        return 0.5
    if salary_min <= exp <= salary_max:
        return 1.0
    if exp < salary_min:
        return 0.7
    if exp <= salary_max * 1.2:
        return 0.5
    return 0.2


def format_score(user_format, vacancy_format):
    if not user_format or not vacancy_format:
        return 0.5
    u, v = user_format.lower().strip(), vacancy_format.lower().strip()
    if u == v:
        return 1.0
    if "удалённо" in u or "удалённо" in v:
        return 0.7
    if "гибрид" in u or "гибрид" in v:
        return 0.8
    return 0.4


def match_vacancies(profile):
    vacancies = load_json("vacancies.json")
    results = []

    for v in vacancies:
        score = (
            skills_score(profile.get("skills", ""), v["skills"]) * 0.4
            + experience_score(profile.get("experience", ""), v["experience"]) * 0.2
            + location_score(profile.get("city", ""), v["city"]) * 0.15
            + salary_score(profile.get("salary", ""), v["salary_min"], v["salary_max"]) * 0.15
            + format_score(profile.get("format", ""), v["format"]) * 0.1
        )
        match_percent = round(score * 100)
        if match_percent >= 30:
            results.append({**v, "match": match_percent})

    results.sort(key=lambda x: x["match"], reverse=True)
    return results[:5]


def match_candidates(vacancy_profile):
    candidates = load_json("candidates.json")
    fake_vacancy = {
        "skills": normalize_skills(vacancy_profile.get("skills", "")),
        "experience": vacancy_profile.get("experience", "1-3 года"),
        "city": vacancy_profile.get("city", ""),
        "salary_min": int(vacancy_profile.get("salary_min", 0) or 0),
        "salary_max": int(vacancy_profile.get("salary_max", 999999) or 999999),
        "format": vacancy_profile.get("format", ""),
    }
    results = []

    for c in candidates:
        score = (
            skills_score(c["skills"], fake_vacancy["skills"]) * 0.4
            + experience_score(c.get("experience", ""), fake_vacancy["experience"]) * 0.2
            + location_score(c.get("city", ""), fake_vacancy["city"]) * 0.15
            + salary_score(c.get("salary_expectation", ""), fake_vacancy["salary_min"], fake_vacancy["salary_max"]) * 0.15
            + format_score(c.get("format", ""), fake_vacancy["format"]) * 0.1
        )
        match_percent = round(score * 100)
        if match_percent >= 30:
            results.append({**c, "match": match_percent})

    results.sort(key=lambda x: x["match"], reverse=True)
    return results[:5]


def ai_chat_response(message, profile, role, matches):
    msg = message.lower().strip()

    if any(w in msg for w in ["привет", "здравств", "добрый"]):
        name = profile.get("name", "друг")
        return f"Здравствуйте, {name}! Я ИИ-ассистент ТрудИИсь. Помогу найти {'работу' if role == 'seeker' else 'кандидатов'} и ответить на вопросы о рынке труда."

    if any(w in msg for w in ["как работает", "что умеешь", "помощь", "help"]):
        return (
            "Я анализирую ваш профиль — навыки, опыт, город, зарплату и формат работы — "
            "и подбираю наиболее подходящие варианты. Задайте вопрос о вакансиях, "
            "попросите уточнить рекомендации или расскажите о своих предпочтениях."
        )

    if any(w in msg for w in ["рекомендац", "подбор", "ваканс", "кандидат", "лучш"]):
        if not matches:
            return "Пока нет подходящих совпадений. Попробуйте расширить навыки или изменить требования к зарплате и городу."
        top = matches[0]
        if role == "seeker":
            return (
                f"Лучшее совпадение — «{top['title']}» в {top['company']} ({top['match']}% совпадение). "
                f"Зарплата: {top['salary_min']:,}–{top['salary_max']:,} ₽. {top['description']}"
            ).replace(",", " ")
        return (
            f"Лучший кандидат — {top['name']}, {top['title']} ({top['match']}% совпадение). "
            f"{top['summary']}"
        )

    if any(w in msg for w in ["зарплат", "деньг", "оплат", "доход"]):
        if role == "seeker" and matches:
            salaries = [m["salary_max"] for m in matches[:3]]
            avg = sum(salaries) // len(salaries)
            return f"По вашему профилю средняя верхняя граница зарплаты в топ-3 вакансиях — около {avg:,} ₽.".replace(",", " ")
        return "Укажите желаемую зарплату в профиле — я учту её при подборе и покажу релевантные предложения."

    if any(w in msg for w in ["удалён", "офис", "гибрид", "формат"]):
        if matches:
            formats = ", ".join(set(m.get("format", "") for m in matches[:3]))
            return f"В ваших рекомендациях встречаются форматы: {formats}. Могу отфильтровать, если уточните предпочтение."
        return "Выберите предпочитаемый формат работы в анкете: офис, удалённо или гибрид."

    if any(w in msg for w in ["навык", "скилл", "опыт", "обуч"]):
        skills = profile.get("skills", "не указаны")
        return (
            f"В вашем профиле указаны навыки: {skills}. "
            "Чем точнее список, тем лучше подбор. Добавьте технологии, с которыми работали, "
            "и инструменты, которые знаете."
        )

    if any(w in msg for w in ["спасибо", "благодар"]):
        return "Рад помочь! Если появятся новые вопросы — пишите. Удачи в поиске!"

    return (
        "Я учитываю ваш профиль при каждом ответе. Спросите о рекомендациях, зарплате, "
        "формате работы или попросите совет по улучшению профиля."
    )


@app.route("/")
def index():
    css = (BASE_DIR / "static" / "css" / "style.css").read_text(encoding="utf-8")
    js = (BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")
    return render_template("index.html", inline_css=css, inline_js=js)


@app.route("/api/match", methods=["POST"])
def api_match():
    data = request.json or {}
    role = data.get("role", "seeker")
    profile = data.get("profile", {})

    if role == "seeker":
        matches = match_vacancies(profile)
    else:
        matches = match_candidates(profile)

    return jsonify({"matches": matches, "role": role})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    message = data.get("message", "")
    profile = data.get("profile", {})
    role = data.get("role", "seeker")

    if role == "seeker":
        matches = match_vacancies(profile)
    else:
        matches = match_candidates(profile)

    reply = ai_chat_response(message, profile, role, matches)
    return jsonify({"reply": reply, "matches": matches})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
