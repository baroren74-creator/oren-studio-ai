# Oren Studio AI — Product Requirements & Architecture Document (PRD)

*Original PRD as provided by Oren. Preserved verbatim (Hebrew) as the
source of truth for requirements. See `docs/vision.md` for a distilled
summary and `docs/decisions.md` for where implementation decisions
adapted these requirements based on later research.*

## Vision

אני בונה מערכת עבור משתמש אחד בלבד – עצמי (אורן).
זו אינה מערכת SaaS ואינה מוצר מסחרי בשלב הראשון.
המטרה היא ליצור סביבת עבודה אחת, חכמה ומודולרית, שתאפשר לי ליצור תוכן טכנולוגי איכותי בעברית במהירות מקסימלית.
המטרה הסופית היא להיכנס לסטודיו, לבחור רעיון, ובתוך דקות בודדות להפיק סרטון קצר ומוכן לפרסום.
המערכת צריכה להפוך עם הזמן ל"סוכן אישי" שמכיר אותי, את תחומי העניין שלי ואת סגנון הדיבור שלי.

## Core Philosophy

אין לבנות אוסף של פיצ'רים.
יש לבנות פלטפורמה מודולרית.
כל יכולת חדשה תהיה Agent עצמאי שניתן להוסיף או להסיר מבלי לשנות את שאר המערכת.
המערכת צריכה להיות Agent First.
כל Agent מקבל משימה, מבצע אותה ומחזיר תוצאה.

## Main Goal

להפוך כל רעיון, סרטון, לינק או Repository לתוכן מקורי שלי.
לא להעתיק תוכן.
אלא ללמוד אותו, להבין אותו, ולייצר תוכן חדש בעברית ובסגנון שלי.

## The Workflow

המשתמש נכנס לסטודיו.
מכניס: GitHub Repository / סרטון YouTube / Reel / Post / Tweet / אתר.
המערכת מנתחת את המקור → מוצאת את המקורות האמיתיים → קוראת Documentation →
מבינה את הטכנולוגיה → מחליטה האם זה מספיק מעניין → כותבת עבורי Script →
מייצרת Storyboard → מכינה Visual Assets → מצלמת אותי או משתמשת באווטאר →
עורכת את הסרטון → יוצרת כתוביות → מייצרת Thumbnail → מכינה Caption →
אני מאשר → המערכת מפרסמת.

## Types of Content

GitHub, Open Source, AI, Design, Photoshop, Productivity, Mac, Apple,
Automation, Computer Vision, LLMs, Claude, Gemini, OpenAI, Coding,
Web Design, UI, UX, Tech Tricks, New Tools, Weekly Discoveries — כל דבר
טכנולוגי שמעניין אותי.

## Personal Learning

המערכת צריכה ללמוד אותי: מה אני שומר, מה אני עושה לו Like, מה אני משתף,
מה אני מצלם, על מה אני עובד, אילו נושאים חוזרים, איזה סוג סרטונים אני
אוהב, באיזה אורך, באיזה סגנון, איך אני מדבר, איך אני פותח סרטון, איך אני
מסיים סרטון. המטרה היא שכל חודש הסוכן יכיר אותי טוב יותר.

## Memory

המערכת צריכה Memory אמיתי. לא Chat History. Knowledge Base: Projects,
Ideas, Repositories, Interesting Posts, Prompt Library, Favorite Tools,
Scripts, Templates, Brand Assets, Style Guide, Personal Knowledge —
Everything searchable.

## Main Agents

- **Research Agent** — מחפש מקורות, קורא Documentation, מסכם, מבין את
  הטכנולוגיה, מוצא את המקור האמיתי.
- **Trend Agent** — מוצא דברים חדשים: GitHub Trending, Hacker News,
  Product Hunt, Reddit, AI News, Open Source, Twitter/X, YouTube, Blogs.
- **Knowledge Agent** — לומד Documentation, לומד Projects, שומר הכל, יודע
  לענות מתוך הידע שנאסף.
- **Script Agent** — כותב תסריטים, Hook, CTA, Caption, Title, Hashtags,
  בסגנון שלי.
- **Recording Agent** — מצלם אותי או מפעיל Avatar.
- **Video Agent** — עורך סרטונים: Zoom, כתוביות, Animations, Transitions,
  B-roll, Screenshots, Highlight, Cursor, Effects.
- **Voice Agent** — שיפור קול, דיבוב, תרגום, Voice Clone (אם צריך).
- **Publishing Agent** — מכין ל-Instagram / TikTok / YouTube Shorts /
  Facebook / LinkedIn, אבל תמיד מחכה לאישור שלי לפני פרסום.

## Human Approval

שום דבר לא מתפרסם אוטומטית. תמיד Approval שלי.

## Style Guide

כל סרטון צריך להיות קצר, מהיר, ברור, טכנולוגי, לא מתיש. Hook בתוך 3
שניות. אורך מומלץ: 10–40 שניות.

## Future AI/Video/Avatar Providers

אין תלות ב-AI אחד. צריך לתמוך ב-OpenAI, Claude, Gemini, OpenRouter,
Local Models, Future Models — כל ספק יהיה Plugin. גם עריכת וידאו וגם
Avatar צריכים להיות מודולריים/Plugin, לא תלויים בחברה אחת.

## Architecture Principles

Plugin Based. Agent Based. Event Driven. Scalable. Everything Modular.
Everything Replaceable. No Vendor Lock-In.

## Suggested Tech Stack (original proposal)

Frontend: Next.js. Backend: Python + FastAPI. Database: PostgreSQL.
Vector Database: Qdrant. Queue: Redis. Storage: S3 Compatible.
Authentication: Clerk או Auth.js. Workflow Engine: LangGraph או CrewAI
(לבחינה).

*See `docs/architecture.md` and `docs/open-source-landscape.md` for how
this stack was validated/adjusted after research (LangGraph confirmed
over CrewAI; Auth.js/Clerk deferred in favor of simple API-key auth for
MVP — see `docs/decisions.md`).*

## Development Roadmap (original phase outline)

- **Phase 1** — Studio UI, Chat, Projects, Memory, Knowledge Base, Prompt
  Library, Settings.
- **Phase 2** — Research Agent, Knowledge Agent, Trend Agent.
- **Phase 3** — Script Generation, Storyboard, Idea Ranking, Virality
  Score.
- **Phase 4** — Recording, Avatar, Voice, Video Editing.
- **Phase 5** — Publishing (Instagram, TikTok, YouTube), Approval Flow.
- **Phase 6** — Self Learning, Preference Learning, Recommendation
  Engine, Daily Content Suggestions.

*See `docs/roadmap.md` for the granular, ~70-step version of this plan,
including the Phase 0 / 0.5 additions that came out of the architecture
and open-source research.*

## Final Mission

לא לבנות אתר. לא לבנות כלי. לבנות סטודיו אישי. לבנות סוכן אישי. לבנות
מערכת עבודה אחת שמכירה אותי, חושבת איתי, אוספת מידע עבורי, מייצרת עבורי
תוכן ומאפשרת לי ליצור תוכן טכנולוגי איכותי בעברית במהירות ובאיכות
הגבוהות ביותר.

בכל החלטה ארכיטקטונית יש לשאול: **"האם זה מקרב את המערכת להיות סוכן
אישי חכם וגמיש לטווח ארוך?"** אם לא — לא לבנות זאת.
