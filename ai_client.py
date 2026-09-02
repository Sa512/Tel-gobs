"""
كل تعاملات البوت مع Claude تمر من هنا فقط
"""
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_claude(system_prompt: str, messages: list[dict], max_tokens: int = 1200) -> str:
    """
    messages: [{"role": "user"/"assistant", "content": "..."}]
    """
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


def polish_cv_summary(raw_data: dict) -> dict:
    """
    ياخذ بيانات السيرة الذاتية الخام (كما كتبها المستخدم) ويرجعها
    مصاغة بشكل احترافي: ملخص مهني + وصف كل خبرة + مهارات مرتبة
    """
    system_prompt = (
        "أنت خبير كتابة سير ذاتية احترافية باللغة العربية والإنجليزية. "
        "مهمتك إعادة صياغة المعلومات الخام التي يعطيك إياها المستخدم لتصبح "
        "احترافية، موجزة، وقوية الأثر، دون اختلاق أي معلومة غير موجودة. "
        "أجب بصيغة JSON فقط بدون أي نص إضافي أو Markdown، بالمفاتيح التالية: "
        '{"summary": "...", "experience": [{"title":"", "company":"", '
        '"period":"", "description":""}], "skills": ["..."], "education": '
        '[{"degree":"", "institution":"", "period":""}]}'
    )
    user_content = (
        "هذه بيانات المستخدم الخام، أعد صياغتها باحترافية وحافظ على نفس اللغة "
        f"التي كتب بها:\n\n{raw_data}"
    )
    raw_response = ask_claude(system_prompt, [{"role": "user", "content": user_content}])

    import json
    try:
        # إزالة أي أسوار Markdown محتملة قبل التحليل
        cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # في حال فشل التحليل، نرجع نصاً عادياً كملخص احتياطي
        return {"summary": raw_response, "experience": [], "skills": [], "education": []}


def career_advisor_reply(user_id: int, cv_data: dict | None, history: list[dict], user_message: str) -> str:
    system_prompt = (
        "أنت مرشد مهني (Career Coach) محترف وودود، تتحدث باللهجة أو اللغة "
        "التي يستخدمها المستخدم. تساعده في: تطوير مساره المهني، التحضير "
        "للمقابلات، تحديد نقاط القوة والضعف في سيرته الذاتية، واختيار "
        "الوظائف والمهارات المناسبة له. كن مباشراً وعملياً وأعط نصائح "
        "قابلة للتطبيق، وليس كلاماً عاماً فقط."
    )
    if cv_data:
        system_prompt += f"\n\nهذه بيانات السيرة الذاتية للمستخدم كمرجع:\n{cv_data}"

    messages = history + [{"role": "user", "content": user_message}]
    return ask_claude(system_prompt, messages)


def draft_application_email(cv_data: dict, job_title: str, job_details: str, company_email: str) -> dict:
    """
    يرجع dict فيها subject و body لإيميل تقديم على وظيفة
    """
    system_prompt = (
        "أنت كاتب محترف لإيميلات التقديم على الوظائف. اكتب إيميل تقديم "
        "مختصر، احترافي، ومقنع بناءً على السيرة الذاتية للمرشح وتفاصيل "
        "الوظيفة. لا تختلق معلومات غير موجودة في السيرة الذاتية. "
        "أجب بصيغة JSON فقط بدون أي نص إضافي، بالمفاتيح: "
        '{"subject": "...", "body": "..."}. اكتب الإيميل بنفس اللغة '
        "التي كُتبت بها تفاصيل الوظيفة."
    )
    user_content = (
        f"بيانات المرشح (السيرة الذاتية):\n{cv_data}\n\n"
        f"المسمى الوظيفي المتقدم له: {job_title}\n"
        f"تفاصيل إضافية عن الوظيفة أو الشركة: {job_details}\n"
        f"سيُرسل الإيميل إلى: {company_email}"
    )
    raw_response = ask_claude(system_prompt, [{"role": "user", "content": user_content}])

    import json
    try:
        cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"subject": f"التقديم على وظيفة {job_title}", "body": raw_response}
