# Oren Studio AI — ניתוח ארכיטקטורה (CTO Review)

**מסמך:** Architecture Proposal
**סטטוס:** לאישור לפני תחילת כתיבת קוד — **עודכן לאחר מחקר Open Source, ראה תיקונים בסעיף 0.1**
**תפקיד:** ניתוח ה-PRD, הצעת ארכיטקטורה מלאה, זיהוי סיכונים, Roadmap מפורט

---

## 0.1 עדכון לאחר מחקר Open Source (ראה מסמך נפרד: `Open_Source_Landscape_for_Oren_Studio_AI.md`)

המחקר אישר את רוב ההחלטות כאן (LangGraph, Qdrant, Recording ידני קודם), אבל חייב חמישה שינויים ממשיים:

1. **Voice/Avatar אינם "Plugin ללא Vendor Lock-In" בפועל** — כל אופציות ה-Voice-Cloning הפתוחות האיכותיות (XTTS, Fish Speech) ברישיון לא-מסחרי. ברירת המחדל המעודכנת: API מסחרי (ElevenLabs) לקול, OSS (OpenVoice) כפרויקט הוזלה נפרד רק אחרי אימות איכות עברית.
2. **n8n לא ישמש כתשתית ליבה** (רישיון Sustainable Use, לא OSS אמיתי) — רק כשכבת טריגרים היקפית.
3. **נוסף Spike מפורש ל-Hebrew RTL Captions לפני Phase 4** — יש Bug מאומת ב-MoviePy עם טקסט RTL; צריך לבדוק בפועל ffmpeg+libass מול Remotion לפני שבונים על זה.
4. **הגשת בקשות Publishing API (Instagram/TikTok/YouTube/LinkedIn) עוברת ל-Phase 0.5, מייד** — לא Phase 5. TikTok דורש אישור דו-שלבי (עד חודשיים), זה Bottleneck חיצוני שלא תלוי בקצב הפיתוח.
5. **Publishing Agent לא נבנה מאפס** — מאמצים Postiz (OSS, agent-native) ובונים רק את שכבת ה-Approval Gate מעליו.

כמו כן אומצו רכיבים שלא היו בתכנון המקורי כי לא ידענו שקיימים ברמה גבוהה: **faster-whisper + ivrit-ai** ל-STT עברית (פתרון מוכן ומצוין), **Tesseract** ל-OCR עברית, **Crawl4AI/Firecrawl/Gitingest/Repomix** למחקר/ניתוח GitHub, **LiteLLM** לניתוב LLM. פירוט מלא, כולל Stars/License/Pros/Cons לכל פרויקט, במסמך המחקר הנפרד.

---

## 0. סיכום מנהלים

ה-Vision ברור וממוקד: כלי אישי אחד, לא SaaS, שהופך רעיון/מקור לסרטון מוכן לפרסום, ולומד את הסגנון שלך עם הזמן. זה מצוין — יעד ברור מקל מאוד על החלטות ארכיטקטורה.

שני סיכונים מרכזיים לפני שנתחיל:

1. **Scope גדול מדי ל-MVP אחד.** ה-PRD מכיל בפועל שלוש מערכות שכל אחת מהן פרויקט בפני עצמו: (א) מערכת Research/Knowledge, (ב) Script/Idea Engine, (ג) Video Production Pipeline (הקלטה/אווטאר/עריכה/קול). בונים את שלושתן ברצף, לא במקביל, אחרת אף חלק לא יגיע ל"מוכן".
2. **"Agent First" צריך הגדרה טכנית מדויקת**, אחרת זו מילה יפה בלי מימוש. למטה מוצעת הגדרה קונקרטית: כל Agent הוא פונקציה טהורה בחוזה קבוע (Input schema → Output schema), רשומה ב-Registry, מופעלת דרך Orchestrator אחד, ומתקשרת רק דרך Event Bus/DB — אף פעם לא קוראת ל-Agent אחר ישירות.

הארכיטקטורה המוצעת למטה עונה על העיקרון המנחה שהגדרת: "האם זה מקרב את המערכת להיות סוכן אישי חכם וגמיש לטווח ארוך?" — כל החלטה כאן נבחרה כדי להישאר קטנה, מוחלפת, ולא לנעול אותך לספק אחד.

---

## 1. עקרונות ארכיטקטורה (מחייבים)

1. **Agent = חוזה, לא מחלקה.** כל Agent מקבל `AgentInput` (JSON סכמטי, מאומת ב-Pydantic), ומחזיר `AgentOutput`. אין תקשורת ישירה Agent→Agent.
2. **Orchestrator אחד, לא הרבה לוגיקת "מי קורא למי" מפוזרת.** ה-Workflow (הדיאגרמה שלך: Source → Research → Script → Storyboard → ... → Publish) הוא Graph מוגדר במקום אחד.
3. **Event-Driven לתיעוד ולשחזור, לא רק לתקשורת.** כל מעבר בין שלבים הוא Event ב-DB. זה נותן חינם: היסטוריה, Retry, Debug, ו-"תראה לי מה קרה לרעיון הזה".
4. **Provider = Plugin.** LLM / Video / Avatar / Voice / Publishing — לכולם Interface אחיד. מחליפים ספק ע"י שינוי שורה אחת ב-config, לא קוד.
5. **Postgres הוא מקור האמת. Qdrant הוא אינדקס בלבד.** כל Vector ב-Qdrant מצביע חזרה ל-`id` בפוסטגרס. אף פעם לא שומרים משהו רק ב-Qdrant.
6. **שום דבר לא מתפרסם בלי אישור אנושי.** זו לא המלצה — זו Invariant במודל הנתונים (`publications.status` לא יכול לעבור ל-`published` בלי `approved_at`).
7. **מערכת למשתמש אחד ≠ מערכת בלי משמעת הנדסית.** בלי Multi-tenancy, בלי RBAC מורכב — אבל כן: Schema נקי, טיפוסים, בדיקות, ו-Observability. אתה תהיה היחיד שמנפה את הבאגים ב-3 בלילה.

---

## 2. שכבות המערכת (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│  Studio UI (Next.js)                                         │
│  Chat · Projects · Knowledge Base · Prompt Library · Settings │
└───────────────────────────┬────────────────────────────────┘
                            │  REST + WebSocket
┌───────────────────────────▼────────────────────────────────┐
│  API Layer (FastAPI)  — Auth, Validation, BFF ל-UI            │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│  Orchestrator (LangGraph)                                    │
│  מריץ את ה-Workflow Graph, שולט ב-Approval Gates              │
└───────────────────────────┬────────────────────────────────┘
                            │  publishes/consumes
┌───────────────────────────▼────────────────────────────────┐
│  Event Bus (Redis Streams)                                   │
└──────┬────────┬────────┬────────┬────────┬────────┬────────┘
       │        │        │        │        │        │
   Research  Trend   Knowledge  Script   Video    Publishing
    Agent    Agent    Agent     Agent    Agent      Agent
       │        │        │        │        │        │
┌──────▼────────▼────────▼────────▼────────▼────────▼────────┐
│  Provider Plugin Layer                                        │
│  LLM(OpenAI/Claude/Gemini/OpenRouter/Local) · Video · Avatar · Voice · Publish │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│  Data Layer:  PostgreSQL (source of truth) · Qdrant (vectors) │
│               S3-compatible Storage (assets/video) · Redis    │
└─────────────────────────────────────────────────────────────┘
```

**למה LangGraph ולא CrewAI:** ה-Workflow שלך הוא Graph עם ענפים ברורים (Research → החלטה "מספיק מעניין?" → Script → ... → Approval Gate → Publish), לא צוות אוטונומי שמתכנן בעצמו. LangGraph נותן State Machine מפורש, checkpointing (חשוב כי שלבי וידאו יקרים וארוכים), ו-Human-in-the-loop native. CrewAI מתאים יותר לצוותי Agent שמנהלים את עצמם — פחות מתאים כשאתה, המשתמש, צריך לעצור באמצע ולאשר.

---

## 3. חוזה ה-Agent (הליבה של "Agent First")

כל Agent במערכת, בלי יוצא מן הכלל, מיישם את אותו Interface:

```python
class AgentInput(BaseModel):
    run_id: UUID
    project_id: UUID
    payload: dict          # schema ספציפי לכל Agent, מאומת בנפרד
    context: AgentContext  # memory refs, style guide refs, budget remaining

class AgentOutput(BaseModel):
    status: Literal["success", "failed", "needs_approval", "skipped"]
    result: dict
    artifacts: list[ArtifactRef]   # קבצים/רשומות שנוצרו
    cost: CostInfo                 # tokens, $, זמן ריצה
    next_event: str | None         # מה Event לפרסם הלאה

class Agent(Protocol):
    name: str
    version: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]

    async def run(self, input: AgentInput) -> AgentOutput: ...
```

**Agent Registry** — טבלה/קובץ config יחיד שממפה `agent_name → implementation + provider config`. Orchestrator לא "מכיר" Agents בקוד קשיח — הוא קורא מה-Registry. זה מה שהופך הוספת Agent חדש לפעולה של "תוסיף רשומה", לא "תשנה את הליבה".

כל ריצת Agent נרשמת ב-`agent_runs` + `agent_events` (ראה סעיף 5) — זה נותן Observability בחינם בלי להוסיף מערכת ניטור נפרדת ב-MVP.

---

## 4. מבנה תיקיות מוצע (Monorepo)

```
oren-studio/
├── apps/
│   ├── web/                      # Next.js — Studio UI
│   │   ├── app/
│   │   │   ├── (studio)/chat/
│   │   │   ├── (studio)/projects/
│   │   │   ├── (studio)/knowledge/
│   │   │   ├── (studio)/prompts/
│   │   │   └── (studio)/settings/
│   │   └── components/
│   └── api/                      # FastAPI
│       ├── routers/              # REST endpoints (סעיף 6)
│       ├── ws/                   # WebSocket (progress events)
│       └── deps/                 # auth, db session, etc.
│
├── packages/
│   ├── core/                     # דומיין משותף, לא תלוי בספק
│   │   ├── schemas/              # Pydantic models (AgentInput/Output וכו')
│   │   ├── events/                # Event type definitions
│   │   └── orchestrator/         # LangGraph graph definition
│   │
│   ├── agents/                   # כל Agent = תיקייה עצמאית
│   │   ├── research_agent/
│   │   ├── trend_agent/
│   │   ├── knowledge_agent/
│   │   ├── script_agent/
│   │   ├── recording_agent/
│   │   ├── video_agent/
│   │   ├── voice_agent/
│   │   └── publishing_agent/
│   │       ├── agent.py          # מימוש run()
│   │       ├── prompts/
│   │       └── tests/
│   │
│   ├── providers/                # Plugin adapters
│   │   ├── llm/  (openai.py, claude.py, gemini.py, openrouter.py, local.py)
│   │   ├── video/  (capcut.py, ffmpeg_pipeline.py, ...)
│   │   ├── avatar/  (heygen.py, synthesia.py, ...)
│   │   ├── voice/  (elevenlabs.py, ...)
│   │   └── publish/  (instagram.py, tiktok.py, youtube.py, ...)
│   │
│   └── memory/                   # ראה סעיף 7
│       ├── knowledge_store/      # Qdrant client + chunking
│       ├── preference_engine/    # style/preference learning
│       └── prompt_library/
│
├── infra/
│   ├── docker-compose.yml        # postgres, redis, qdrant, minio
│   ├── migrations/                # Alembic
│   └── terraform/ (עתידי, אם יעבור לענן)
│
└── docs/
    ├── architecture.md           # המסמך הזה
    └── agents/                   # תיעוד לכל Agent
```

**עיקרון מפתח:** `packages/agents/*` אף פעם לא מייבא Agent אחר. תקשורת רק דרך `core/events` ו-DB. זו האכיפה בפועל של "Plugin שאפשר להוסיף/להסיר בלי לשבור את השאר".

---

## 5. Database Schema (PostgreSQL — מקור האמת)

```sql
-- ===== ליבת התוכן =====

projects (
  id UUID PK,
  title TEXT,
  status TEXT,              -- draft|researching|scripting|producing|review|published|archived
  source_type TEXT,         -- github|youtube|reel|post|tweet|website|idea
  source_url TEXT,
  created_at, updated_at
)

sources (
  id UUID PK,
  project_id FK,
  type TEXT,                 -- repo|video|article|post
  raw_url TEXT,
  fetched_content JSONB,      -- transcript / README / scraped text
  fetched_at TIMESTAMPTZ
)

research_notes (
  id UUID PK,
  project_id FK,
  summary TEXT,
  key_points JSONB,
  interest_score NUMERIC,     -- "האם זה מספיק מעניין"
  scored_by TEXT,              -- agent version
  created_at
)

ideas (
  id UUID PK,
  project_id FK NULL,          -- יכול להיות עצמאי, לפני שהופך לפרויקט
  title TEXT,
  stage TEXT,                  -- new|researched|scored|approved|scripted|produced|published|archived|rejected
  virality_score NUMERIC,
  tags TEXT[],
  created_at
)

scripts (
  id UUID PK,
  project_id FK,
  hook TEXT,
  body TEXT,
  cta TEXT,
  caption TEXT,
  title TEXT,
  hashtags TEXT[],
  style_profile_id FK,          -- לאיזו גרסת סגנון נכתב
  version INT,
  created_at
)

storyboards (
  id UUID PK,
  script_id FK,
  scenes JSONB                   -- [{order, description, visual_ref, duration}]
)

assets (
  id UUID PK,
  project_id FK,
  type TEXT,                     -- video_raw|broll|screenshot|thumbnail|voiceover|caption_file
  storage_url TEXT,               -- S3 path
  metadata JSONB,
  created_at
)

videos (
  id UUID PK,
  project_id FK,
  status TEXT,                    -- rendering|ready|failed
  final_url TEXT,
  duration_seconds NUMERIC,
  provider TEXT,                   -- which video provider produced it
  created_at
)

publications (
  id UUID PK,
  project_id FK,
  video_id FK,
  platform TEXT,                    -- instagram|tiktok|youtube_shorts|facebook|linkedin
  status TEXT,                       -- pending_approval|approved|scheduled|published|failed
  approved_at TIMESTAMPTZ NULL,      -- NULL = לא ניתן לפרסם, אוכף ברמת DB/Trigger
  approved_by TEXT DEFAULT 'oren',
  published_at TIMESTAMPTZ NULL,
  external_post_id TEXT,
  created_at
)

-- ===== Agent Runtime / Observability =====

agent_runs (
  id UUID PK,
  project_id FK,
  agent_name TEXT,
  status TEXT,                      -- running|success|failed|needs_approval
  input JSONB,
  output JSONB,
  cost_usd NUMERIC,
  tokens_used INT,
  started_at, finished_at
)

agent_events (
  id UUID PK,
  run_id FK,
  event_type TEXT,                  -- ראה סעיף 6 לרשימת סוגי Events
  payload JSONB,
  created_at
)

approvals (
  id UUID PK,
  project_id FK,
  stage TEXT,                        -- script|storyboard|final_video|publish
  status TEXT,                        -- pending|approved|rejected|edited
  notes TEXT,
  decided_at TIMESTAMPTZ
)

-- ===== Memory / Knowledge (ראה סעיף 7) =====

memory_entries (
  id UUID PK,
  type TEXT,                          -- fact|preference|habit|repeated_topic
  content TEXT,
  confidence NUMERIC,
  source_run_id FK NULL,
  created_at, updated_at
)

style_profile (
  id UUID PK,
  version INT,
  tone_notes TEXT,
  opening_patterns TEXT[],
  closing_patterns TEXT[],
  avg_length_seconds NUMERIC,
  vocabulary_notes JSONB,
  updated_at
)

prompt_library (
  id UUID PK,
  name TEXT,
  category TEXT,
  prompt_text TEXT,
  version INT,
  parent_id FK NULL,                  -- לגרסאות קודמות
  created_at
)

favorite_tools (
  id UUID PK,
  name TEXT,
  category TEXT,
  notes TEXT,
  saved_at
)

brand_assets (
  id UUID PK,
  type TEXT,                           -- logo|font|color_palette|intro_outro
  storage_url TEXT,
  metadata JSONB
)
```

**Qdrant Collections (אינדקס בלבד, כל Point מצביע ל-Postgres `source_id`):**

| Collection | תוכן | מקור |
|---|---|---|
| `knowledge_docs` | קטעי Documentation/README/מאמרים שנקראו | `sources.id` |
| `transcripts` | תמלולי סרטונים/רילס שנותחו | `sources.id` |
| `personal_style` | קטעי תסריטים/כתוביות שאתה כתבת/אישרת | `scripts.id` |
| `prompt_library` | חיפוש סמנטי בספריית הפרומפטים | `prompt_library.id` |
| `preferences` | תמצות של Like/Save/Share signals | `memory_entries.id` |

---

## 6. API Contracts + Event Flow

### 6.1 REST — עיקריים

```
POST   /api/projects                     צור פרויקט חדש ממקור
GET    /api/projects/{id}
GET    /api/projects/{id}/timeline        כל ה-agent_events בסדר כרונולוגי

POST   /api/agents/{agent_name}/run       הפעלה ידנית/דיבוג של Agent בודד
GET    /api/agent-runs/{id}

POST   /api/approvals/{id}/approve
POST   /api/approvals/{id}/reject
POST   /api/approvals/{id}/request-edit   {notes}

GET    /api/knowledge/search?q=...        חיפוש סמנטי ב-Qdrant + פוסטגרס
POST   /api/prompt-library
GET    /api/style-profile/current
```

### 6.2 WebSocket

```
WS /ws/projects/{id}/events
→ סטרימינג בזמן אמת של agent_events (progress bar בסטודיו:
  "Research Agent: קורא README... 40%")
```

### 6.3 Internal Agent Envelope (Orchestrator ↔ Agent)

זהה תמיד: `AgentInput` בכניסה, `AgentOutput` ביציאה (סעיף 3). ה-Orchestrator הוא היחיד שמכיר את סדר ה-Graph — Agent בודד לא יודע "מי אחריו".

### 6.4 Event Types (על Redis Streams, גם נשמרים ב-`agent_events`)

מיפוי ישיר לזרימה שהגדרת במסמך המקורי:

```
source.ingested
research.completed
idea.scored              → אם מתחת לסף: idea.rejected (עוצר כאן, חוסך עלות)
script.drafted
script.approved          → Approval Gate #1 (אופציונלי, ניתן לדלג)
storyboard.ready
assets.ready
recording.requested → recording.completed   (או avatar.requested → avatar.completed)
video.rendered
captions.generated
thumbnail.generated
caption.text.ready
final_review.requested   → Approval Gate #2 (חובה)
publish.approved
publish.completed / publish.failed
```

כל Event → Orchestrator מחליט מה השלב הבא לפי ה-Graph. אם Agent נכשל → Event `*.failed` → Retry policy (סעיף 8.5) לפני שמעירים אותך.

### 6.5 Approval State Machine

```
draft → pending_approval → approved → published
                        ↘ rejected (חוזר ל-stage הקודם עם notes)
```
נאכף ב-DB: `publications.published_at` לא ניתן להגדרה אם `approved_at IS NULL` (constraint/trigger, לא רק לוגיקת אפליקציה — כדי שטעות קוד לא תפרסם בטעות).

---

## 7. Memory — לא Chat History, אלא Knowledge Base אמיתי

חשוב להפריד ל-4 סוגי זיכרון שונים, כי לכל אחד מנגנון עדכון שונה:

| סוג | מה זה | איפה נשמר | איך מתעדכן |
|---|---|---|---|
| **Working Memory** | הקשר של ריצה בודדת (הרעיון הנוכחי, מקורות שנקראו) | `agent_runs.input/output` | לכל ריצה מחדש |
| **Episodic Memory** | היסטוריית פרויקטים — "מה עשיתי, מתי, למה" | Postgres (`projects`, `agent_events`) | append-only |
| **Semantic/Knowledge Memory** | ידע על טכנולוגיות, תיעוד, מקורות | Qdrant + `sources` | בכל Ingestion |
| **Preference Memory** | מה אתה אוהב, איך אתה מדבר, אורך מועדף | `style_profile` + `memory_entries` | **Batch job חודשי** (לא בזמן אמת) |

**נקודה קריטית:** Preference Learning לא צריך לרוץ בכל אינטראקציה — זה יגרום ל-Drift ולרעש. מוצע Job שרץ פעם בחודש (Phase 6), אוסף signals (מה שמרת/עשית Like/שיתפת/צילמת/ערכת בתסריט שהמערכת הציעה), ומייצר גרסה חדשה של `style_profile` — עם Diff שאתה יכול לראות ולאשר/לדחות, בדיוק כמו Pull Request. זה גם עונה על "Human Approval" כעיקרון גורף, לא רק בפרסום.

---

## 8. סיכונים ובעיות עתידיות שזיהיתי

1. **Scope creep הוא הסיכון מספר 1.** תשע קטגוריות Agent + Avatar + Voice Clone + עריכת וידאו אוטומטית זה scope של צוות, לא של אדם אחד. הפתרון: MVP שמוכיח את ה-Loop המלא מקצה לקצה עם השלבים הכי "מטומטמים" האפשריים (למשל: Recording/Video Agent בהתחלה = את מצלם ידנית ומעלה קובץ, לא Avatar אוטומטי) — ורק אז משדרגים כל שלב בנפרד.
2. **זכויות יוצרים / Fair Use.** המערכת "לומדת" מ-Repo/סרטון/Reel/Tweet ומייצרת תוכן חדש. צריך גבול ברור מוגדר *עכשיו*, לא בדיעבד: איסור על ציטוט מילולי מעבר לסף מסוים, חובת "טרנספורמציה" (סיכום+דעה+הקשר, לא שכתוב), ושדה `originality_check` לפני פרסום. זה נושא משפטי אמיתי, לא רק טכני.
3. **Voice Clone / Avatar של עצמך.** גם כשזה "רק אתה" — ספקי Avatar/Voice שומרים ביומטריה בענן שלהם. לבדוק ToS (שמירת דגימות, שימוש לאימון מודל) לפני שמעלים חומר. מומלץ Provider-agnostic מהיום הראשון (כבר מתוכנן ב-PRD) ולבחור ספק עם מדיניות מחיקה ברורה.
4. **Postgres/Qdrant Drift.** בלי משמעת (Postgres = source of truth, Qdrant = אינדקס בלבד, נבנה מ-Postgres) בקלות נוצר מצב שבו הם לא מסונכרנים. מוצע: Qdrant נבנה *רק* מ-Job שקורא מ-Postgres, אף פעם לא נכתב אליו ישירות מ-Agent.
5. **עלות LLM/Video ללא בקרה.** אין Cost Tracking/Budget ב-PRD המקורי. Pipeline שרץ Research→Script→Video על כל רעיון יכול להתייקר מהר אם אין Idea Scoring *לפני* שמשקיעים בשלבים היקרים. מוצע: `interest_score`/`virality_score` הם Gate מוקדם (סעיף 6.4: `idea.rejected`), לא רק שדה מידע.
6. **Observability.** Multi-agent pipeline בלי לוגים מובנים = ניפוי באגים עיוור. `agent_runs`+`agent_events` (כבר בסכמה) הם המינימום; שווה לשקול חיבור ל-LangSmith/Helicone בהמשך (זול, plug-in, לא חוסם MVP).
7. **Retry / Idempotency.** שלבי וידאו ארוכים ויקרים — אם Video Agent נופל אחרי 10 דקות רינדור, לא רוצים להתחיל הכל מחדש. Orchestrator (LangGraph) תומך ב-Checkpointing — לנצל את זה מהיום הראשון, לא להוסיף בדיעבד.
8. **Rate Limits / עלות מקורות מידע.** X/Twitter API יקר מאוד היום; GitHub/HN/RSS/YouTube זולים/חינמיים. מוצע לדחות אינטגרציית Twitter/X ב-Trend Agent לשלב מאוחר, ולהתחיל במקורות חינמיים.
9. **Auth "עתידי" (Clerk/Auth.js) הוא Overkill למשתמש יחיד.** מציע Session/API-Key פשוט ב-MVP; לשדרג ל-Clerk רק אם בפועל תרצה גישה ממספר מכשירים/דפדפנים עם Login מלא.
10. **"Local Models" דורש הבהרת חומרה.** אם הכוונה ל-Mac מקומי (Ollama/MLX) — יש לזה השלכות על איזה Providers רצים איפה (UI בענן/מקומי? API רץ מקומית?). לא חוסם MVP, אבל כדאי להחליט לפני Phase שמבוסס על זה.
11. **Idea Scoring צריך קריטריונים מוגדרים מוקדם**, לא רק "יופיע ב-Phase 3". בלי רובריקה ברורה (למשל: חדשנות, רלוונטיות לקהל שלך, זמינות מקור אמין, פוטנציאל ויזואלי) ה-Agent ינחש. מוצע להעביר הגדרת קריטריונים ל-Phase 2 (יחד עם Knowledge Agent), גם אם הציון עצמו עדיין לא "חכם".

---

## 9. שיפורים מוצעים ל-PRD (דברים שחסרים)

1. **Idea Backlog / Kanban מפורש** — `ideas.stage` כבר בסכמה, אבל כדאי שה-UI (Phase 1) יציג את זה כלוח, לא רק רשימת צ'אט. זה גם המקום הכי טבעי לראות "על מה אני עובד" (מבוקש ב-Personal Learning).
2. **Feedback Loop אחרי פרסום.** ה-PRD מדבר על למידה ממה שאתה עושה, אבל לא ממה שהקהל מגיב. מוצע (Phase 6+): משיכת Analytics בסיסי מהפלטפורמות (views/likes) כ-signal נוסף ל-Preference Engine — "מה שעבד" משפיע על "מה שנעשה הבא".
3. **Content Package אחיד.** אובייקט לוגי אחד שעובר בין כל ה-Agents (script+storyboard+assets+captions+thumbnail+metadata), במקום שכל Agent "יידע" לשלוף בנפרד מ-DB. פשוט יותר לדבג ולבדוק.
4. **Cost/Budget guardrail** כ-Agent Middleware, לא Agent נפרד — כל `AgentOutput` מדווח `cost`, ו-Orchestrator עוצר ומבקש אישור אם עוברים סף חודשי.
5. **Versioning ל-Style Guide ול-Prompt Library** — כבר בסכמה (`version`, `parent_id`) — לוודא שה-UI מציג Diff בין גרסאות, לא רק "עדכון".
6. **Ops/Debug View קטן ב-Phase 1**, לא רק Chat — טבלה של `agent_runs` עם סטטוס/עלות/זמן. ייחסך המון זמן ניפוי באגים מאוחר יותר.

---

## 10. Roadmap מפורט

### Phase 1 — Studio Foundation (ה-Loop הכי "טיפש" שעובד מקצה לקצה)
1.1 Setup monorepo (apps/web, apps/api, packages/core)
1.2 Docker Compose: Postgres + Redis + Qdrant + MinIO (S3-compatible)
1.3 Alembic migrations: projects, sources, agent_runs, agent_events, approvals
1.4 FastAPI skeleton + health check + auth (API-key פשוט)
1.5 Next.js skeleton + layout (Chat / Projects / Knowledge / Prompts / Settings)
1.6 `AgentInput`/`AgentOutput` schemas ב-`core/schemas`
1.7 Agent Registry (config-driven, לא hardcoded)
1.8 LangGraph — הגדרת ה-Graph הריק (nodes = placeholders, edges = הזרימה מסעיף 6.4)
1.9 WebSocket endpoint לסטרימינג `agent_events`
1.10 UI: מסך "פרויקט חדש" — הדבקת URL בלבד (ללא ניתוח עדיין)
1.11 UI: Timeline view לפרויקט (רשימת events)
1.12 Ops view בסיסי: טבלת `agent_runs`
1.13 Manual "Stub Agent" — Agent ריק שרק מסמן success, כדי לבדוק את כל ה-Pipeline מקצה לקצה
1.14 בדיקת קצה-לקצה: פרויקט חדש → רץ דרך כל ה-Stub Agents → מגיע ל-`published` (מזויף)

### Phase 2 — Research + Knowledge + Trend (המוח)
2.1 Provider Plugin Interface ל-LLM (`LLMProvider` abstract)
2.2 מימוש Provider ראשון (Claude, כי זה מה שאתה כבר עובד איתו)
2.3 Research Agent v1: GitHub repo → קריאת README/docs → סיכום
2.4 Research Agent v2: YouTube URL → transcript (whisper/captions) → סיכום
2.5 הגדרת קריטריוני Idea Scoring (רובריקה כתובה, לא רק prompt)
2.6 `interest_score` + Gate: מתחת לסף → `idea.rejected`, לא ממשיך
2.7 Knowledge Agent: chunking + embedding + כתיבה ל-Qdrant (`knowledge_docs`)
2.8 Knowledge Agent: semantic search endpoint (`/api/knowledge/search`)
2.9 Trend Agent v1: GitHub Trending (API חינמי)
2.10 Trend Agent v2: Hacker News + RSS feeds
2.11 Trend Agent v3: Product Hunt
2.12 (מאוחר יותר) Trend Agent v4: Reddit
2.13 (דחוי בכוונה) Trend Agent v5: Twitter/X — רק אחרי בדיקת עלות API
2.14 UI: Idea Backlog / Kanban board (`ideas.stage`)
2.15 בדיקת קצה-לקצה: Repo אמיתי → Research → Knowledge indexed → Idea scored

### Phase 3 — Script + Storyboard
3.1 `style_profile` v0 (ידני — אתה ממלא שאלון קצר פעם אחת: טון, אורך, פתיחות/סיומות אהובות)
3.2 Script Agent: Hook generator
3.3 Script Agent: Body + CTA
3.4 Script Agent: Caption + Title + Hashtags
3.5 Prompt Library UI (CRUD + versioning)
3.6 Approval Gate #1: אישור/עריכת תסריט לפני המשך
3.7 Storyboard Agent: פירוק תסריט לסצנות (JSON scenes)
3.8 UI: תצוגת Storyboard (רשימת סצנות + preview)
3.9 חיבור `personal_style` ל-Qdrant: תסריטים שאושרו נכנסים כ-signal
3.10 בדיקת קצה-לקצה: Idea מאושר → Script → Storyboard מוצג לאישור

### Phase 4 — Production (Recording / Avatar / Video / Voice)
4.1 Recording Agent v0 (**ידני**): מסך העלאת קובץ וידאו שצילמת בעצמך
4.2 Video Agent v1: חיתוך/טרימינג בסיסי (ffmpeg) לפי storyboard timing
4.3 Video Agent v2: כתוביות אוטומטיות (whisper + burn-in)
4.4 Video Agent v3: B-roll/Screenshot overlay
4.5 Video Agent v4: Zoom/Transitions/Highlight cursor
4.6 Thumbnail Agent: יצירת thumbnail מהפריימים/מ-AI image
4.7 Avatar Provider Interface + מימוש ספק ראשון (בדיקת ToS לפני!)
4.8 Recording Agent v1: מעבר ל-Avatar אוטומטי (אופציונלי, לא מחליף העלאה ידנית)
4.9 Voice Agent v1: שיפור קול (denoise/enhance)
4.10 Voice Agent v2: Voice clone (בדיקת ToS + הסכמה מפורשת לפני!)
4.11 Voice Agent v3: תרגום/דיבוב (אם רלוונטי)
4.12 Cost tracking middleware על כל Agent יקר (Video/Avatar/Voice)
4.13 Checkpointing ב-LangGraph לשלבי רינדור ארוכים (Retry בלי לאבד עבודה)
4.14 בדיקת קצה-לקצה: Storyboard מאושר → וידאו סופי עם כתוביות ו-thumbnail

### Phase 5 — Publishing + Approval
5.1 Publishing Provider Interface
5.2 מימוש ספק ראשון (למשל Instagram) + OAuth
5.3 Approval Gate #2 (חובה): מסך "סקירה סופית" — וידאו+caption+thumbnail יחד
5.4 DB constraint: `published_at` לא ניתן קביעה בלי `approved_at`
5.5 מימוש שאר הפלטפורמות (TikTok, YouTube Shorts, Facebook, LinkedIn)
5.6 Scheduling (פרסום מתוזמן, לא רק מיידי)
5.7 בדיקת קצה-לקצה מלאה: URL → ... → אישור שלך → פרסום בפועל

### Phase 6 — Self Learning
6.1 הגדרת Signals לאיסוף (Like/Save/Share/מה צילמת/מה ערכת בתסריט)
6.2 Batch Job חודשי: ניתוח signals → הצעת `style_profile` גרסה חדשה
6.3 UI: Diff view לאישור/דחיית עדכון סגנון (כמו Pull Request)
6.4 Recommendation Engine: הצעות רעיונות יומיות מבוססות Trend+Preference
6.5 Feedback Loop: משיכת Analytics מהפלטפורמות אחרי פרסום
6.6 שילוב Analytics כ-signal נוסף ב-Preference Engine
6.7 Dashboard: "מה המערכת למדה עליי החודש" — שקיפות מלאה, לא Black Box

---

## 11. Future AI/Video/Avatar Providers — כבר מכוסה ארכיטקטונית

הבחירה ב-Plugin Interface (סעיף 4, `packages/providers/*`) ועקרון ה-Provider Registry עונה ישירות על "No Vendor Lock-In" עבור LLM, Video, Avatar ו-Publishing. הוספת ספק חדש = מימוש interface אחד + רישום ב-config. לא נדרש שינוי ב-Agents שמשתמשים בו.

---

## 12. סיכום — מה מאשרים לפני כתיבת קוד

- [ ] Stack: Next.js + FastAPI + Postgres + Qdrant + Redis + S3-compatible — מאושר?
- [ ] LangGraph כ-Orchestrator (במקום CrewAI) — מאושר?
- [ ] Auth פשוט (API-key) ב-MVP במקום Clerk — מאושר?
- [ ] סדר השלבים ב-Roadmap (Research/Knowledge לפני Video/Avatar) — מאושר?
- [ ] Recording/Video Agent מתחילים **ידניים/חצי-אוטומטיים** (Phase 4.1) ולא Avatar מלא מיד — מאושר?
- [ ] גבולות Fair-Use/Originality (סעיף 8.2) — צריך לדבר על זה לפני Script Agent
- [ ] דחיית Twitter/X Trend Agent עד לבדיקת עלות API — מאושר?

לאחר אישור הסעיפים האלה — מתחילים ב-Phase 1.1.
