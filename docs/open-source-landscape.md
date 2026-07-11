# Open Source Landscape for Oren Studio AI

**מסמך:** Phase 0 — Open Source Research
**סטטוס:** לאישור לפני עדכון הארכיטקטורה הסופית וכתיבת קוד
**מתודולוגיה:** מחקר חי (WebSearch + בדיקת דפי GitHub בפועל, יולי 2026) על 17 תחומים, ~60 פרויקטים. המספרים (Stars, גרסאות, רישיונות) אומתו מול המקור בזמן המחקר, לא משוערים מהזיכרון.

---

## 0. תמצית מנהלים — וביקורת ישירה על הארכיטקטורה שהצענו

ביקשת שאהיה ביקורתי ולא אנסה לרצות אותך. הנה זה, בלי ריפוד:

**שלושה דברים בארכיטקטורה שהצענו ב-Phase 0 הקודם היו נכונים ואושרו על ידי המחקר** — Qdrant כ-Vector DB, LangGraph כ-Orchestrator, וגישת "Recording/Video ידניים בהתחלה". אלה נשארים.

**חמישה דברים דורשים שינוי ממשי, לא קוסמטי:**

1. **"No Vendor Lock-In" בקול/אווטאר הוא אשליה נעימה, לא תוכנית עבודה.** בדקנו את כל אופציות ה-TTS/Voice-Cloning הפתוחות המובילות (XTTS, Fish Speech) — שתיהן ברישיון **לא-מסחרי**, כאשר בעל הרישיון של אחת (Coqui) כבר לא קיים כחברה, ושל השנייה (Fish Audio) דורש הסכם תשלום נפרד. האופציה הפתוחה היחידה עם רישיון מסחרי נקי (OpenVoice, MIT) — איכות העברית שלה **לא מאומתת בשום מקור**. המסקנה ההנדסית: **אל תתכנן על Voice Clone פתוח כברירת מחדל**. ההמלצה שלי: להתחיל עם API מסחרי (למשל ElevenLabs) לקול, ולבדוק בפועל אם OpenVoice מספיק טוב בעברית לפני שמשקיעים זמן פיתוח בו. זו לא "פשרה זמנית" — זו כנראה המצב הקבוע, אלא אם התמונה תשתנה.
2. **n8n לא מתאים כרכיב תשתית קבוע**, בניגוד למה שאולי דמיינת כ"מנוע האוטומציה". הרישיון שלו (Sustainable Use License) הוא לא Open Source אמיתי — הוא "fair-code", ומגביל שימוש מסחרי/הפצה. למערכת אישית זה כרגע לא בעיה, אבל זה נעל אפשרית לעתיד שלא כדאי לבנות עליה את הליבה. המלצתי: n8n בתפקיד היקפי בלבד (webhooks/טריגרים), לא כ-Orchestrator.
3. **כתוביות בעברית (RTL) הן סיכון טכני אמיתי שלא הופיע כלל במסמך הקודם.** גילינו Bug מתועד ופתוח ב-MoviePy (הספרייה שרוב כלי ה-Caption הפתוחים משתמשים בה) שהופך טקסט RTL להפוך/מקוטע. ffmpeg+libass יכול לעבוד נכון, אבל רק אם קומפל עם `--enable-libfribidi` ולא מובטח. המלצתי: **להוסיף Spike/Prototype מפורש לפני Phase 4** — לבדוק בפועל אם Remotion (מבוסס דפדפן, תמיכת Unicode bidi מובנית) מציג עברית נכון, לפני שבונים סביב זה את כל ה-Video Agent.
4. **תזמון הגשת בקשות ה-API לפרסום (Instagram/TikTok/YouTube/LinkedIn) חייב לזוז מ-Phase 5 להיום.** זו לא פרטים טכניים — זה Lead Time חיצוני של שבועות עד חודשים שלא תלוי בקצב הפיתוח שלך. TikTok במיוחד: אישור ראשוני 2-6 שבועות, ואז **Audit נוסף ונפרד** לפני שאפשר לפרסם בפומבי (עד אז — רק Private). אם זה נשאר ב-Phase 5 כמתוכנן, זה יהפוך ל-Bottleneck שמעכב את כל התוכנית בחודשים, לא בגלל קוד. **זו הביקורת המשמעותית ביותר שיש לי על התוכנית המקורית.**
5. **"בניית Publishing Agent מאפס" לא נכון.** יש כלי קוד פתוח (Postiz) שכבר פותר בדיוק את בעיית ה-OAuth/scheduling/multi-platform, ומיועד גם לשליטה על ידי Agent. במקום לבנות שכבת פרסום, נכון יותר לאמץ אותו ולעטוף אותו רק בשכבת האישור האנושי (שהוא כבר לא נותן — וזה בדיוק החלק שאתה צריך לבנות בעצמך).

**מעבר לזה — תגלית חיובית משמעותית:** יש הרבה יותר "רכיבים קיימים ברמה גבוהה" ממה שהארכיטקטורה המקורית הניחה. Crawling (Crawl4AI/Firecrawl), ניתוח GitHub (Gitingest/Repomix), STT בעברית (faster-whisper + ivrit-ai — פתרון מצוין ומוכן!), ו-OCR בעברית (Tesseract) — כולם קיימים, בוגרים, וברישיון נקי. אלה חוסכים לך שבועות של פיתוח שהיית עושה בטעות בעצמך.

---

## 1. Agent Frameworks & Orchestration

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **LangGraph** | Active | 36.8k | MIT (core) — ⚠️ `langgraph-api`/Platform server בנפרד, מסחרי | **Adopt** |
| CrewAI | Active/Stable | 55k | MIT | לא לאמץ כ-Orchestrator |
| AutoGen (Microsoft) | **Maintenance mode — הוכרז רשמית** | 58k (קפוא) | MIT | לא לאמץ |
| AG2 (fork קהילתי של AutoGen) | Active אך צעיר | 4.5k | Apache 2.0 | לא רלוונטי כרגע |
| OpenHands | Active | 76k | MIT | Extend — לשאוב רק את שכבת ה-Sandbox/Code-execution ל-Research Agent |
| Mastra | Active, צעיר | 26k | Apache 2.0 (ליבה) + Enterprise License על SSO/RBAC | לא מתאים — TypeScript-first, שגוי לזמן ריצה FastAPI |

**Pros of LangGraph:** מנגנון `interrupt()`/resume מובנה — בדיוק מה שצריך ל-Approval Gate; Checkpointing ל-Postgres מובנה; MIT בליבה; לא תלוי ב-LangChain המלא.
**Cons:** עקומת למידה גבוהה יותר מ-CrewAI; חובה להימנע מ-`langgraph-api` המסחרי בפרודקשן — להריץ את הגרף מוטמע בתוך FastAPI, לא כשירות נפרד.

**Workflow Engines (השוואה נפרדת):**

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| n8n | Active מאוד | 186k | **Sustainable Use License — לא OSI-approved** | Extend בלבד (טריגרים/webhooks), לא כליבה |
| Temporal | Active, בוגר | 20.7k | MIT | Extend — רק אם שלב הרינדור מתגלה כפגיע לקריסות; לא להטמיע Temporal מלא מהיום הראשון |
| Prefect | Active, בוגר | 22.4k | Apache 2.0 | לא לאמץ — חופף ל-LangGraph בלי ערך מוסף לתרחיש הזה |

**סינתזה:** Orchestrator = LangGraph, מוטמע ב-FastAPI, checkpointing ל-Postgres. LLM Routing = LiteLLM (סעיף הבא). n8n רק בתפקיד היקפי. Temporal רק אם רינדור וידאו יתגלה בפועל כלא-אמין.

---

## 2. LLM Routing

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **LiteLLM** | Active | ~45k | MIT (ליבה) | **Adopt** |
| OpenRouter | Active, מסחרי | — | **סגור, לא Open Source, לא self-hostable** | לא לאמץ כליבה |
| Vercel AI SDK | Active | 23.7k-25.5k | Apache 2.0 | Extend בלבד — Frontend streaming, לא routing layer |

**סינתזה:** LiteLLM self-hosted כשכבת ה-Abstraction היחידה ל-LLM providers — MIT, ללא Vendor Lock-in אמיתי, cost tracking מובנה. OpenRouter (שהמסמך המקורי הניח כ"ספק") הוא בפועל שירות סגור — אפשר להגדיר אותו כ-Provider *אחד מני רבים* בתוך LiteLLM (לגיבוי), אבל לא כשכבת הניתוב הראשית.

---

## 3. Memory / Vector Database

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **Qdrant** | Active | 31.4k | Apache 2.0, ללא היסטוריית Relicensing | **Adopt** (תואם למה שכבר תוכנן) |
| Chroma | Active | 28k | Apache 2.0 | חלופה קרובה טובה, פחות מוכח בפרודקשן |
| Weaviate | Active, בוגר | 16.3k | BSD-3 (הרישיון הכי נקי מבין הארבעה) | Skip — רוצה להיות Object DB, מנוגד לעיקרון "אינדקס בלבד" |
| Milvus | Active, בוגר מאוד | 40k+ | Apache 2.0 (LF AI Foundation) | Skip — Overkill לקנה מידה של משתמש יחיד (דורש etcd/MinIO/Pulsar) |

**Knowledge Base / RAG Frameworks:**

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| LlamaIndex | Active, מסחרי מאחוריו | 38-49k | MIT | Extend חלקי — רק connectors/chunking, לא כל ה-Runtime |
| Haystack | Active, בוגר | 25k | Apache 2.0 | Extend חלקי — אם כן פריימוורק, זה עדיף על LlamaIndex פילוסופית |
| AnythingLLM | Active מאוד | 60-63k | MIT | **לא לאמץ כתשתית** — אפליקציה שלמה, לא ספרייה, מתנגש עם "Postgres = מקור אמת" |
| Open WebUI | Active מאוד | 144.9k | ⚠️ **Relicensed מ-BSD-3 ל-"Open WebUI License"** (מוגבל מותג מעל 50 משתמשים) | לא לאמץ כתשתית — רק כהשראת UX |

**סינתזה:** Qdrant מאושר. **המלצה חדשה וחשובה: לא לאמץ LlamaIndex/Haystack כ-Framework מלא** — לבנות שכבת chunking+embedding דקה בעצמנו (כ-300 שורות קוד), כי מקורות המידע קבועים וידועים מראש (Repo/YouTube/Article/Tweet), וה-Framework "נלחם" בעיקרון "Postgres הוא מקור האמת". לשאוב רעיונות/קוד מ-LlamaIndex Loaders (MIT, חופשי להעתקה) בלי לאמץ את כל הפריימוורק.

---

## 4. Video Editing & Content Generation

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **FFmpeg** | Active | — (ענק) | LGPL/GPL תלוי בבנייה | **Adopt** — מנוע ההרצה הבסיסי, חובה |
| **Auto-Editor** | Active | 4.4k | Unlicense (public domain) | **Adopt** — לחיתוך שקטים/מתים אוטומטי |
| Remotion | Active | 50.6k | ⚠️ לא OSS מלא — חינם עד 3 עובדים, אח"כ מסחרי | Extend — לשכבת כתוביות/עיצוב, בגלל רינדור מבוסס דפדפן (bidi טוב יותר) |
| Shotstack | מסחרי | — | סגור (API בתשלום) | Skip |
| OpenMontage | חדש מאוד, ⚠️ יחס Stars/Contributors חשוד | 23-36k (תנודתי) | AGPL-3.0 | Extend/reference בלבד — לא לאמץ כתלות |
| Twick | Active, צעיר | לא אומת | Sustainable Use License (לא OSS מלא) | Extend/evaluate |

**Captions:** Captacity (MIT, 138 stars) — לוגיקה טובה אך **מבוססת MoviePy עם Bug פתוח ב-RTL**; auto-subtitle — כמעט נטוש. **אין כלי בוגר עם תמיכת עברית מאומתת.**

**Thumbnails:** Hecate (Yahoo, Apache 2.0) — בורר frame חכם אך ללא text overlay, ומיושן (C++/OpenCV, לא תוחזק מ-2016). **קטגוריה שצריך לבנות בעצמנו** (ffmpeg frame extraction + Pillow/Remotion overlay).

**Storyboard:** StoryboardAI, StoryGen-Atelier — קיימים אך צעירים/לא מוכחים, וחלקם קשורים לספק LLM ספציפי. **קטגוריה דלה — צריך לבנות שכבת LLM-prompting מותאמת אישית.**

**⚠️ ממצא קריטי — סיכון עברית/RTL מאומת:** יש Bug פתוח ומתועד ב-MoviePy (issue #1694) שהופך טקסט RTL. ffmpeg+libass **יכול** לעבוד נכון אך רק עם `--enable-libfribidi` ולא מובטח כברירת מחדל. Remotion (רינדור דפדפן אמיתי) הכי מבטיח אבל **לא נבדק בפועל בעברית על ידי אף מקור שנמצא**. Whisper עצמו מתמלל עברית טוב — הבעיה היא רק בשכבת ה-Rendering.

**המלצה חדשה: להוסיף Spike מפורש (משימה בת יום-יומיים) לפני Phase 4** — לרנדר כתובית עברית עם מספרים/אנגלית מעורבים דרך (א) ffmpeg+libass+fribidi ו-(ב) קומפוננטת Remotion, ולבחור את מה שבאמת עובד, לפני שבונים עליו ארכיטקטורה.

**סינתזה:** FFmpeg (מנוע) + Auto-Editor (חיתוך) + Remotion (כתוביות/thumbnail, בגלל bidi) + שכבת החלטות LLM מותאמת אישית (מה לזום, מה B-roll, storyboard) — כי אין כלי בוגר לשכבת ה"שיפוט" הזו.

---

## 5. Avatar, Voice, STT, OCR

### Avatar

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| "OpenAvatar" | **לא קיים כפרויקט אמיתי** (1 star, לא רציני) | — | — | להסיר מהתכנון |
| OpenAvatarChat | Active | 3.3k | Apache 2.0 | Extend — כארכיטקטורת ייחוס |
| **MuseTalk** | Active | 3.9k | **MIT נקי — הכי טוב מבין כולם** | **Adopt** |
| LivePortrait | Active מאוד | 18.3k | MIT (קוד) ⚠️ אבל תלוי ב-InsightFace `buffalo_l` — **מחקר בלבד, לא מסחרי** | Adopt בתנאי שמחליפים את רכיב הזיהוי |
| SadTalker | מאט | 13.9k | Apache 2.0 (הוסר איסור מסחרי) | Fallback בלבד, איכות נמוכה יותר |
| Wav2Lip | קפוא, המחברים עברו למוצר בתשלום | 13k | **מפורשות לא-מסחרי** | לא לאמץ |
| EchoMimic V1-V3 | Active | 4.2k+ | Apache 2.0 (V3) | לעקוב, לא ראשון בתור |

**ממצא: "אווטאר פתוח שמוכן לפרודקשן היום" לא קיים באמת.** MuseTalk+LivePortrait (עם תיקון InsightFace) הם הבסיס הכי טוב, אך הרכבתם לפייפליין מלוטש היא פרויקט אינטגרציה לא טריוויאלי, ואף מקור לא אימת דיוק ויזמות (visemes) בעברית. **תואם למה שכבר תוכנן ב-Phase 4 — לדחות, להתחיל עם צילום ידני.**

### Voice / TTS

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| Kokoro | Active | 7.5-7.8k | Apache 2.0 | לא ל-Hebrew (8 שפות, לא כולל עברית), לא Voice Cloning אמיתי |
| Coqui/XTTS | **החברה נסגרה ב-2024**, פורק קהילתי (Idiap) | 45.6k (קפוא)/2.1k (fork) | קוד MPL 2.0, **משקלי XTTS: CPML — לא-מסחרי, אין יותר למי לשלם** | להשתמש בזהירות רבה בלבד |
| Piper | Active, מטופל ע"י Open Home Foundation | 10.4k | MIT (repo מקורי) | Fallback לשפות שאינן עברית; עברית לא רשמית |
| **OpenVoice** | Active | 36.6k | **MIT — הכי נקי מבין אופציות ה-Cloning** | **Adopt בתנאי** — לבדוק עברית בפועל קודם |
| Fish Speech / OpenAudio | Active מאוד | 29.8k | **Fish Audio Research License — לא-מסחרי, נדרש הסכם בתשלום לשימוש מסחרי** | לא לאמץ ללא הסכם מסחרי מפורש |

**ממצא קריטי:** שני האופציות עם האיכות הכי גבוהה (XTTS, Fish Speech) חסומות מסחרית. **OpenVoice הוא היחיד עם רישיון מסחרי נקי, אך איכות העברית שלו לא אומתה בשום מקור.**

### Speech-to-Text

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| Whisper (OpenAI) | Stable | 94.8k | MIT | בסיס בלבד — לא ישירות, דיוק עברית בינוני |
| **Faster-Whisper + ivrit-ai fine-tunes** | Active | 23.3k (faster-whisper) | MIT/Apache 2.0 | **Adopt — הזוכה הברור** |
| NVIDIA Parakeet/NeMo | Active | — | Apache 2.0 / CC-BY-4.0 | **לא תומך בעברית כלל** — לא רלוונטי |

**ממצא מצוין:** קהילת ivrit.ai (ישראלית, קוד פתוח) כבר פתרה בדיוק את הבעיה — Fine-tune של Whisper לעברית, ארוז ל-runtime המהיר של faster-whisper, רישיון MIT/Apache. **זו ההמלצה החד-משמעית ביותר בכל המחקר.**

### OCR

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **Tesseract** | Stable | 72.4k | Apache 2.0 | **Adopt** — היחיד עם תמיכת עברית אמיתית (92-96% על טקסט נקי) |
| PaddleOCR | Active מאוד | 70k+ | Apache 2.0 | **אין תמיכת עברית בכלל** |
| EasyOCR | Stable, איטי | 29.4k | Apache 2.0-style | **בקשת עברית פתוחה מ-2020, לא מומשה** |

**סינתזה כוללת לקטגוריה:** STT — פתרון מוכן ומצוין (faster-whisper+ivrit-ai). OCR — Tesseract, מספיק טוב לצילומי מסך נקיים (בדיוק השימוש המתוכנן). Voice/TTS ו-Avatar הם אזור הסיכון הגבוה ביותר בכל הפרויקט: **המלצה מעשית — Voice: להתחיל עם API מסחרי (ElevenLabs) ולבדוק OpenVoice כפרויקט הוזלת-עלויות נפרד; Avatar: לדחות לגמרי, כפי שכבר תוכנן.**

---

## 6. Web Crawling, Browser Automation, Search, GitHub Analysis, Publishing

### Web Crawling

| Project | Maturity | Stars (~) | License/Pricing | המלצה |
|---|---|---|---|---|
| Firecrawl | Active | 149k | AGPL-3.0 (ליבה, self-hostable) + Tiers בתשלום | Adopt (self-hosted) — לאתרים קשים/anti-bot |
| **Crawl4AI** | Active | 60-71k | Apache 2.0, חינם לגמרי | **Adopt** — ברירת מחדל לחילוץ מאמרים |
| Jina AI Reader | Active | — | חינם עד מכסה, לא self-hostable | Fallback לקריאות חד-פעמיות |

### Browser Automation

| Project | Maturity | Stars (~) | License | המלצה |
|---|---|---|---|---|
| **Playwright** | Active, Microsoft | 62k+ | Apache 2.0 | **Adopt** — מנוע הרינדור הבסיסי |
| **Browser Use** | Active מאוד, YC | 99.9k | MIT | **Adopt** — למשימות דורשות שיפוט (login, UI לא מוכר) |
| Stagehand | Active | 22.6k | MIT | Extend רק אם הסטאק נוטה ל-TypeScript |
| Puppeteer | Active/Stable | 93.5k | Apache-family | Skip — מיותר מול Playwright |

### Search APIs

| Project | Pricing | המלצה |
|---|---|---|
| **Tavily** | חינם 1,000 credits/חודש, ללא כרטיס אשראי | **Adopt** — ברירת מחדל |
| Exa | חינם 1,000/חודש, יקר יותר ב-"deep" | משלים לחיפוש סמנטי |
| SerpAPI | חינם רק 250/חודש | רק אם צריך תוצאות Google מילוליות |
| Brave Search | ⚠️ **המכסה החינמית בוטלה בפברואר 2026** | לשקול מחדש — לא באמת חינמי יותר |
| **SearXNG** | חינם לגמרי, self-hosted, AGPL-3.0 | **Adopt** — לכמות גבוהה/חקר גס |

### GitHub Analysis

| Project | Stars (~) | License | המלצה |
|---|---|---|---|
| **Gitingest** | 15k | MIT | **Adopt** |
| **Repomix** | 22.4k | MIT | **Adopt** — יחד עם Gitingest, לא במקום |

**ממצא: הקטגוריה הזו קיימת ובוגרת** — בניגוד להנחה אפשרית שצריך לבנות Parser בעצמנו.

### Publishing — הממצא הכי חשוב במחקר כולו

| פלטפורמה | חיכוך | זמן המתנה |
|---|---|---|
| YouTube | **נמוך** (עדכון Google דצמבר 2025 הוזיל quota) — עד ~100 uploads/יום בחינם | ללא Audit נדרש בקנה המידה הזה |
| LinkedIn (פרופיל אישי) | **נמוך** — Self-serve, ללא review | מיידי |
| LinkedIn (עמוד חברה) | **גבוה מאוד** | 4 שבועות עד 4 חודשים, דחייה נפוצה |
| Instagram/Facebook | בינוני-גבוה — App Review + Business Verification | 2-6 שבועות |
| **TikTok** | **הכי גבוה — תהליך דו-שלבי** | 2-6 שבועות לאישור ראשוני, ואז **Audit נוסף** לפני שאפשר לפרסם בפומבי (לא רק Private) |

| כלי Scheduling | Stars | License | המלצה |
|---|---|---|---|
| **Postiz** | 29.6k | AGPL-3.0, agent-native (CLI לסוכני AI) | **Adopt** — לעטוף בשכבת אישור אנושי משלנו |
| Mixpost | — | MIT (Lite) / $269 חד-פעמי ל-Pro (כל הפלטפורמות) | חלופה אם רישיון AGPL מפריע |

**סינתזה:** לא לבנות Publishing Agent מאפס — לאמץ Postiz (OAuth+scheduling מוכן ל-5 הפלטפורמות), ולבנות רק את שכבת ה-Approval Gate שהיא הדרישה הייחודית של Oren Studio (Postiz לא נותן את זה). **להתחיל בהגשת הבקשות ל-Instagram/Facebook App Review ו-TikTok Content Posting API כבר עכשיו, במקביל לכל פיתוח אחר** — כי זה ה-Bottleneck האמיתי של לוח הזמנים, לא הקוד.

---

## 7. טבלת סיכום — מה מאמצים, מה בונים, מה דוחים

| רכיב | החלטה | כלי נבחר |
|---|---|---|
| Orchestrator | Adopt | LangGraph (מוטמע, לא Platform server) |
| LLM Routing | Adopt | LiteLLM self-hosted |
| Vector DB | Adopt | Qdrant |
| RAG Framework | **Build** (לא לאמץ LlamaIndex/Haystack) | שכבת chunking+embedding מותאמת, ~300 שורות |
| Video Execution Engine | Adopt | FFmpeg |
| Video Cutting | Adopt | Auto-Editor |
| Captions/Thumbnails | Extend | Remotion (בגלל bidi) + Spike לעברית לפני התחייבות |
| Storyboard Logic | **Build** | LLM prompting מותאם, אין כלי בוגר |
| Avatar | **Defer** | MuseTalk+LivePortrait(מתוקן) — רק ב-Phase 4 מתקדם |
| Voice/TTS | Hybrid — API מסחרי כברירת מחדל | ElevenLabs (בדיקה), OpenVoice כפרויקט הוזלה נפרד |
| STT | Adopt | faster-whisper + ivrit-ai checkpoints |
| OCR | Adopt | Tesseract |
| Web Crawling | Adopt | Crawl4AI (ברירת מחדל) + Firecrawl self-hosted (fallback) |
| Browser Automation | Adopt | Playwright + Browser Use |
| Search | Adopt | Tavily (ברירת מחדל) + SearXNG (נפח גבוה) |
| GitHub Analysis | Adopt | Gitingest + Repomix |
| Publishing/Scheduling | Adopt + Build | Postiz + שכבת Approval Gate משלנו |
| Workflow glue/triggers | Extend (היקפי בלבד) | n8n (לא כליבה, בגלל רישיון) |

---

## 8. מה זה משנה בפועל ב-Roadmap

עדכונים נדרשים למסמך הארכיטקטורה הקודם (לא רק תוספות — שינויי סדר):

1. **Phase 0.5 חדש (לפני הכל):** הגשת בקשות Instagram/Facebook App Review + TikTok Content Posting API — Lead time של שבועות-חודשים, לא תלוי בקוד. מתחילים עכשיו, לא ב-Phase 5.
2. **Phase 1:** להוסיף אימוץ LiteLLM (לא לבנות provider abstraction בעצמנו).
3. **Phase 2 (Research/Knowledge):** להוסיף Gitingest+Repomix ל-Research Agent, Crawl4AI/Firecrawl ל-Trend/Research Agents, Tavily/SearXNG לחיפוש — הכל Adopt, לא Build. חוסך שבועות.
4. **Phase 2 (Knowledge Agent):** לא לאמץ LlamaIndex/Haystack — לבנות שכבת chunking דקה ישירות מול Qdrant.
5. **Phase 3.5 חדש — Hebrew RTL Caption Spike:** יום-יומיים, לפני שממשיכים ל-Video Agent המלא. תוצר: החלטה מבוססת נתונים (ffmpeg+libass או Remotion) במקום הנחה.
6. **Phase 4 (Video):** FFmpeg+Auto-Editor+Remotion, בהתאם לתוצאת ה-Spike. Storyboard = LLM prompting מותאם (לא כלי חיצוני).
7. **Phase 4 (Voice):** לתכנן קודם כ-API מסחרי (ElevenLabs), לא OSS. OpenVoice כפרויקט נפרד אחרי שערוץ עם קהל אמיתי קיים.
8. **Phase 4 (STT):** faster-whisper+ivrit-ai — פשוט, זול, מוכן. אין צורך ב-Spike, הפתרון כבר קיים.
9. **Phase 5 (Publishing):** לא לבנות Publishing Agent מאפס — לאמץ Postiz, לבנות רק Approval Gate. אם Phase 0.5 בוצע מוקדם, זה כבר לא Bottleneck.

---

## 9. הערת סגירה כנה

הביקורת המרכזית על התוכנית המקורית היא לא ארכיטקטונית — היא **סדר עדיפויות**. הקוד עצמו (Agent framework, DB schema, Event flow) היה נכון ברובו מההתחלה. מה שהיה חסר זה הכרה בכך שהפרויקט הזה תלוי בשלושה דברים חיצוניים שלא נשלטים בקוד: רישיונות (קול/אווטאר), תמיכת עברית (כתוביות/TTS — לא מובנת מאליה בעולם שרובו אנגלי-קודם), ואישורי API של פלטפורמות (זמן המתנה חיצוני). שלושתם דורשים החלטה/פעולה **מוקדם**, לא בסוף. זה השינוי האמיתי במסמך הזה.
