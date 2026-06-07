"""
多語言語音閘道 (Multilingual TTS Gateway)  —  給「語寶圖鑑」前端呼叫
=====================================================================
設計目標：語言「從後台增減」。所有語言定義在 languages.json，
前端開啟時呼叫 GET /langs 動態產生語言選單；改語言不必改程式。

每個語言用一個 provider（語音來源）：
  • browser  : 由前端用瀏覽器內建語音唸（中/英/日/韓/印尼/越/泰…）→ 不經過此後端
  • ithuan   : 意傳「鬥拍字」開源服務，支援「台語」與「客語」(腔口) → 免費
  • cloud    : Google Cloud TTS（粵語 yue-HK 等，需 API 金鑰）→ 最穩、付費

端點：
  GET  /langs                 → 回傳啟用中的語言清單（前端用它畫選單）
  GET  /tts?lang=&text=       → 回傳該語言的語音 (audio/mpeg)；browser 類不會呼叫
  GET  /admin                 → 簡單後台網頁（增減/啟停語言）
  GET  /admin/langs           → 讀全部語言設定（含未啟用）
  POST /admin/langs           → 覆寫 languages.json（需 header X-Admin-Token）

部署：
  pip install -r requirements.txt
  uvicorn tts_gateway:app --host 0.0.0.0 --port 8000
  （或丟到 Render/Railway/Fly.io）拿到網址後填回前端 TTS_BASE。

環境變數：
  ADMIN_TOKEN       後台寫入用密碼（預設 "changeme"，上線請改）
  GOOGLE_TTS_KEY    Google Cloud TTS 金鑰（粵語/雲端語言用）
  ITHUAN_BASE       意傳服務網址（預設官方站；自架可改）
"""
import base64
import hashlib
import json
import os
import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Multilingual TTS Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HERE = os.path.dirname(os.path.abspath(__file__))
LANG_FILE = os.path.join(HERE, "languages.json")
CACHE_DIR = os.environ.get("TTS_CACHE_DIR", os.path.join(HERE, "tts_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "changeme")
GOOGLE_TTS_KEY = os.environ.get("GOOGLE_TTS_KEY", "")
GOOGLE_TRANSLATE_KEY = os.environ.get("GOOGLE_TRANSLATE_KEY", "") or GOOGLE_TTS_KEY
ITHUAN_BASE = os.environ.get("ITHUAN_BASE", "https://hapsing.ithuan.tw")

# 拍照辨識（Gemini 視覺）＋ 會員碼驗證用（金鑰只放後端，絕不放前端）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
# 會員碼清單（逗號分隔，例：JAMINE2026,VIP-AAA,VIP-BBB）。在這份清單內＝無限使用、不扣免費次數。
MEMBER_CODES = set(c.strip().upper() for c in os.environ.get("MEMBER_CODES", "").split(",") if c.strip())
SCAN_PROMPT = (
    "你是兒童語言學習 App 的辨識助手。請辨識照片中「最主要的一個」物品，"
    "只回傳一個 JSON 物件，不要 markdown、不要反引號、不要任何多餘文字。"
    "鍵值：zh(繁體中文名), en(English), ja(日本語), tl(台羅拼音), "
    "emoji(一個最貼切的 emoji), cat(類別), level(固定填 \"幼兒\"), type(固定填 \"名詞\")。"
    "若無法辨識，zh 回傳 \"???\"。"
)


def verify_member(code: str) -> bool:
    """會員碼是否有效（不分大小寫、去空白）。MEMBER_CODES 為空時一律非會員。"""
    return bool(code) and code.strip().upper() in MEMBER_CODES


def load_langs():
    with open(LANG_FILE, encoding="utf-8") as f:
        return json.load(f)["languages"]


def lang_by_key(key):
    for L in load_langs():
        if L["key"] == key:
            return L
    return None


# ── 上游 provider ───────────────────────────────────────────
async def synth_ithuan(text: str, accent: str) -> bytes:
    """
    意傳「鬥拍字／媠聲」台語語音合成（開源、免費）。
    端點：GET https://hapsing.ithuan.tw/bangtsam?taibun=<台羅>
    輸入需為「台羅(KIP)拼音」；台語卡片的 tl 欄位正是台羅，直接對應。
    （注意：此端點是台語/閩南語系統，客語是另一套，不支援。）
    """
    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as c:
        r = await c.get(f"{ITHUAN_BASE}/bangtsam", params={"taibun": text})
        r.raise_for_status()
        ctype = r.headers.get("content-type", "").lower()
        if "audio" in ctype or "octet-stream" in ctype or "mpeg" in ctype:
            return r.content
        # 萬一回傳 JSON，嘗試取出音檔網址再抓一次
        try:
            data = r.json()
        except Exception:
            return r.content  # 沒有 JSON 就當作直接是音檔
        url = data.get("音檔") or data.get("audio_url") or data.get("url")
        if not url:
            raise RuntimeError("意傳回傳非預期內容（前120字）：" + r.text[:120])
        if url.startswith("/"):
            url = ITHUAN_BASE + url
        a = await c.get(url)
        a.raise_for_status()
        return a.content


async def synth_google(text: str, code: str) -> bytes:
    """Google Cloud TTS（粵語 yue-HK 等）。需 GOOGLE_TTS_KEY。已驗證的請求格式。"""
    if not GOOGLE_TTS_KEY:
        raise RuntimeError("未設定 GOOGLE_TTS_KEY")
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_KEY}",
            json={
                "input": {"text": text},
                "voice": {"languageCode": code},
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.85},
            },
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"])


async def synthesize(L: dict, text: str) -> bytes:
    if L["provider"] == "ithuan":
        return await synth_ithuan(text, L.get("accent", "閩南語"))
    if L["provider"] == "cloud":
        return await synth_google(text, L.get("code", ""))
    raise RuntimeError(f"provider {L['provider']} 由前端瀏覽器處理，不應呼叫後端")


# ── 對外端點 ────────────────────────────────────────────────
@app.get("/langs")
def langs():
    return {"languages": [L for L in load_langs() if L.get("enabled", True)]}


@app.get("/tts")
async def tts(lang: str, text: str):
    text = (text or "").strip()
    if not text:
        raise HTTPException(400, "缺少 text")
    L = lang_by_key(lang)
    if not L:
        raise HTTPException(404, f"未知語言 {lang}")
    if L["provider"] == "browser":
        raise HTTPException(400, f"{lang} 由前端瀏覽器發音，不需呼叫後端")
    if len(text) > 60:
        text = text[:60]
    cache = os.path.join(CACHE_DIR, hashlib.md5((lang + ":" + text).encode()).hexdigest() + ".mp3")
    if os.path.exists(cache):
        return Response(open(cache, "rb").read(), media_type="audio/mpeg")
    try:
        audio = await synthesize(L, text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"{lang} 語音合成失敗：{e}")
    with open(cache, "wb") as f:
        f.write(audio)
    return Response(audio, media_type="audio/mpeg")


# ── 後台 ────────────────────────────────────────────────────
@app.get("/admin/langs")
def admin_get():
    with open(LANG_FILE, encoding="utf-8") as f:
        return JSONResponse(json.load(f))


@app.post("/admin/langs")
async def admin_set(req: Request, x_admin_token: str = Header(default="")):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "後台密碼錯誤")
    body = await req.json()
    if "languages" not in body or not isinstance(body["languages"], list):
        raise HTTPException(400, "格式需為 {languages: [...]}")
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
    return {"ok": True, "count": len(body["languages"])}


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return ADMIN_HTML


@app.get("/health")
def health():
    return {"ok": True}


ADMIN_HTML = """<!doctype html><meta charset=utf-8>
<title>語言後台</title>
<style>body{font-family:system-ui;max-width:760px;margin:24px auto;padding:0 16px}
table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px;font-size:14px}
input{width:100%;border:none;font-size:14px}button{padding:8px 14px;border:0;border-radius:8px;background:#FF7A59;color:#fff;font-weight:700;cursor:pointer}
.row-add{background:#f7f7f7}</style>
<h2>🌐 語言後台（增減 / 啟停）</h2>
<p>欄位：key(代碼) label(顯示名) flag(旗) provider(browser/ithuan/cloud) code(BCP-47) accent(腔口) field(讀哪個欄位) enabled(啟用)</p>
<input id=tok placeholder="後台密碼 (X-Admin-Token)" style="width:260px;border:1px solid #ccc;padding:6px;border-radius:8px">
<table id=t></table>
<p><button onclick=addRow()>＋ 新增一列</button> <button onclick=save()>💾 儲存</button> <span id=msg></span></p>
<script>
let data={languages:[]};
const cols=["key","label","flag","provider","code","accent","field","enabled"];
async function load(){data=await (await fetch('/admin/langs')).json();render();}
function render(){const t=document.getElementById('t');
 t.innerHTML='<tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'<th></th></tr>'+
 data.languages.map((L,i)=>'<tr>'+cols.map(c=>'<td><input data-i='+i+' data-c="'+c+'" value="'+(L[c]??'')+'"></td>').join('')+'<td><button onclick=del('+i+')>✕</button></td></tr>').join('');
 t.querySelectorAll('input').forEach(inp=>inp.onchange=e=>{const i=e.target.dataset.i,c=e.target.dataset.c;let v=e.target.value;if(c==='enabled')v=(v==='true'||v==='1');data.languages[i][c]=v;});}
function addRow(){data.languages.push({key:'',label:'',flag:'🏳️',provider:'browser',code:'',accent:'',field:'',enabled:true});render();}
function del(i){data.languages.splice(i,1);render();}
async function save(){const r=await fetch('/admin/langs',{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Token':document.getElementById('tok').value},body:JSON.stringify(data)});
 document.getElementById('msg').textContent=r.ok?'✅ 已儲存':'❌ '+(await r.text());}
load();
</script>"""

# ---------------------------------------------------------------------------
# 拍照辨識代理：前端把照片(base64)送來，後端用你的 Gemini 金鑰辨識，
# 並驗證會員碼。回傳 {raw: <JSON文字>, member: true/false}。
# 金鑰只存在後端環境變數，永不外露。
# ---------------------------------------------------------------------------
@app.post("/scan")
async def scan(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "請傳 JSON")
    image = body.get("image", "")
    media_type = body.get("media_type", "image/jpeg")
    code = body.get("code", "") or ""
    is_member = verify_member(code)

    if not GEMINI_API_KEY:
        return JSONResponse({"error": "尚未設定 GEMINI_API_KEY", "member": is_member}, status_code=500)
    if not image:
        return JSONResponse({"error": "缺少 image (base64)", "member": is_member}, status_code=400)

    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + GEMINI_MODEL + ":generateContent?key=" + GEMINI_API_KEY)
    payload = {
        "contents": [{
            "parts": [
                {"text": SCAN_PROMPT},
                {"inline_data": {"mime_type": media_type, "data": image}},
            ]
        }],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256},
    }
    try:
        async with httpx.AsyncClient(timeout=60) as cli:
            r = await cli.post(url, json=payload)
    except Exception as e:
        return JSONResponse({"error": f"連線 Gemini 失敗：{e}", "member": is_member}, status_code=502)
    if r.status_code != 200:
        return JSONResponse({"error": f"Gemini 回應 {r.status_code}: {r.text[:200]}", "member": is_member}, status_code=502)

    data = r.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raw = '{"zh":"???"}'
    return JSONResponse({"raw": raw, "member": is_member})

# ---------------------------------------------------------------------------
# 線上翻譯：把裝置端辨識到的英文標籤，翻成各語言（Google Cloud Translation v2）。
# 用於「拍照辨識」命名正確化。免費額度每月 50 萬字元，幾乎用不完。
# 需在 Google Cloud 開啟「Cloud Translation API」，並讓金鑰可使用該 API。
# ---------------------------------------------------------------------------
TRANSLATE_TARGETS = {"zh": "zh-TW", "ja": "ja", "ko": "ko", "ind": "id", "vi": "vi", "th": "th"}

@app.get("/translate")
async def translate(text: str, targets: str = "zh,ja,ko,ind,vi,th"):
    if not GOOGLE_TRANSLATE_KEY:
        raise HTTPException(503, "未設定 GOOGLE_TRANSLATE_KEY / GOOGLE_TTS_KEY")
    want = [t.strip() for t in targets.split(",") if t.strip() in TRANSLATE_TARGETS]
    out = {}
    async with httpx.AsyncClient(timeout=20) as c:
        for k in want:
            try:
                r = await c.post(
                    f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_TRANSLATE_KEY}",
                    json={"q": text, "source": "en", "target": TRANSLATE_TARGETS[k], "format": "text"},
                )
                if r.status_code == 200:
                    out[k] = r.json()["data"]["translations"][0]["translatedText"]
            except Exception:
                pass
    return JSONResponse(out)
