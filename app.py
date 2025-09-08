import base64
import importlib
import os
import re
import unicodedata
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import random
import streamlit as st
from pandas.errors import EmptyDataError
import streamlit.components.v1 as components  # música / sfx

# ==========================
# CONFIG
# ==========================
st.set_page_config(page_title="Terraloteos", page_icon="🦊", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

LOGO_PATH = os.path.join(ASSETS_DIR, "logo_terraloteos.png")
BG_PATH = os.path.join(ASSETS_DIR, "background.png")
LEADERBOARD_PATH = os.path.join(DATA_DIR, "leaderboard.csv")
QUESTIONS_PATH = os.path.join(DATA_DIR, "preguntas.csv")

# ==========================
# ESTILOS / FONDO
# ==========================
def load_css() -> None:
    css_path = os.path.join(ASSETS_DIR, "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def inject_background_image(path: str) -> None:
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] {{
              background-image: url("data:image/png;base64,{b64}") !important;
              background-size: cover !important;
              background-position: center center !important;
              background-attachment: fixed !important;
            }}
            [data-testid="stAppViewContainer"]::before {{ display:none !important; }}
            </style>
            """,
            unsafe_allow_html=True
        )

def get_logo_html(width: int) -> str:
    """Logo como <img> en base64 para centrarlo con columnas."""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img src="data:image/png;base64,{b64}" style="width:{width}px;max-width:100%;height:auto;display:block;margin:0 auto;" />'
    return ""

# ==========================
# FOX ROAD (GYMTONIC -> Terra)
# ==========================
def _trees_positions(n: int = 8) -> list[float]:
    if n < 1:
        return []
    step = 100 / (n + 1)
    return [round(step * (i + 1), 2) for i in range(n)]

def foxy_scene_html(progress_pct: int, trees: int = 8) -> str:
    """Escena del zorro. progress_pct en 0..100 (ligado al avance del quiz)."""
    p = max(0, min(100, int(progress_pct)))
    # margen para que no tape los endpoints
    left_pct = 2 + (p * 0.96)

    # Árboles alternando arriba/abajo
    tpos = _trees_positions(trees)
    trees_html = []
    for i, pos in enumerate(tpos):
        side = "top" if i % 2 == 0 else "bottom"
        trees_html.append(f'<div class="foxy-tree {side}" style="left:{pos}%; transform: translateX(-50%);">🌳</div>')

    return f"""
    <div class="foxy-wrap">
      <div class="foxy-title">Ayudá a Foxy a llegar a tiempo con el cliente — {p}%</div>

      <div class="foxy-endpoints">
        <!-- 2) Sin texto 'GYMTONIC', solo el emoji de ubicación -->
        <div class="foxy-left">📍</div>
        <!-- 3) Texto más grande junto al edificio -->
        <div class="foxy-right">🏢<span class="foxy-endcap label-dark big">Oficina de Terraloteos</span></div>
      </div>

      <div class="foxy-scene">
        <div class="foxy-road"></div>
        {''.join(trees_html)}
        <div class="foxy-fox" style="left:{left_pct}%;">🦊</div>
      </div>
    </div>
    """

# ==========================
# HELPERS RANGO / IMÁGENES
# ==========================
def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9\s\.-]", "", text)
    text = text.lower().strip().replace(".", "")
    text = re.sub(r"[\s_]+", "-", text)
    return text

def show_rank_meme(rank: str) -> None:
    """
    Muestra UNA imagen según el rango (busca en /assets con estos nombres EXACTOS):
      - Aprendiz Terra  ->  aprendiz-terra.jpg
      - Asesor Jr.      ->  asesor-jr.jpg
      - Asesor Senior.  ->  asesor-senior.jpg
      - Maestro Terra   ->  maestro-terra.jpg
    Si no encuentra .jpg, intenta .jpeg, .png, .webp.
    """
    mapping = {
        "Aprendiz Terra": "aprendiz-terra",
        "Asesor Jr.": "asesor-jr",
        "Asesor Senior.": "asesor-senior",
        "Maestro Terra": "maestro-terra",
    }
    base = mapping.get(rank.strip(), "")
    if not base:
        return
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = os.path.join(ASSETS_DIR, base + ext)
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            st.markdown(
                f"<div class='rank-meme'><img src='data:{mime_map[ext]};base64,{b64}' alt='Imagen {rank}'/></div>",
                unsafe_allow_html=True
            )
            return

# ==========================
# AUDIO
# ==========================
def mount_quiz_music() -> None:
    """Inserta un <audio> en el documento raíz y trata de reproducirlo."""
    path = os.path.join(ASSETS_DIR, "music_quiz.mp3")
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    components.html(
        f"""
        <script>
        (function(){{
          const root = window.parent || window;
          if (root.__terra_bgm__) return;
          const a = root.document.createElement('audio');
          a.src = "data:audio/mpeg;base64,{b64}";
          a.loop = true;
          a.autoplay = true;
          a.volume = 0.5;
          a.style.display = 'none';
          root.document.body.appendChild(a);
          root.__terra_bgm__ = a;
          function tryPlay() {{ a.play().catch(function(){{}}); }}
          tryPlay();
          ['click','touchstart','keydown'].forEach(function(ev){{
            root.addEventListener(ev, tryPlay, {{ once: true, passive: true }});
            window.addEventListener(ev, tryPlay, {{ once: true, passive: true }});
          }});
        }})();
        </script>
        """,
        height=0, width=0
    )

def stop_quiz_music() -> None:
    components.html(
        """
        <script>
        (function(){
          const root = window.parent || window;
          if (root.__terra_bgm__) {
            try { root.__terra_bgm__.pause(); root.__terra_bgm__.currentTime = 0; } catch(e){}
          }
        })();
        </script>
        """,
        height=0, width=0
    )

# 5) Pausar / reanudar música base (para últimos 10s)
def pause_quiz_music() -> None:
    components.html(
        """
        <script>
        (function(){
          const root = window.parent || window;
          const a = root.__terra_bgm__;
          if (a){ try{ a.pause(); }catch(e){} }
        })();
        </script>
        """,
        height=0, width=0
    )

def resume_quiz_music() -> None:
    components.html(
        """
        <script>
        (function(){
          const root = window.parent || window;
          const a = root.__terra_bgm__;
          if (a){ try{ a.play().catch(function(){}); }catch(e){} }
        })();
        </script>
        """,
        height=0, width=0
    )

def play_quack() -> None:
    """Reproduce un sonido corto 'cuack'."""
    path = os.path.join(ASSETS_DIR, "sfx_quack.mp3")
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    components.html(
        f"""
        <script>
        (function(){{
          const root = window.parent || window;
          const a = root.document.createElement('audio');
          a.src = "data:audio/mpeg;base64,{b64}";
          a.autoplay = true;
          a.volume = 0.8;
          a.style.display = 'none';
          root.document.body.appendChild(a);
          a.addEventListener('ended', function(){{ try{{ a.remove(); }}catch(e){{}} }});
          function tryPlay(){{ a.play().catch(function(){{}}); }}
          tryPlay();
          ['click','touchstart','keydown'].forEach(function(ev){{
            root.addEventListener(ev, tryPlay, {{ once:true, passive:true }});
          }});
        }})();
        </script>
        """,
        height=0, width=0
    )

def play_final10() -> None:
    """Reproduce una pista para los últimos 10 segundos (una sola vez por pregunta)."""
    path = os.path.join(ASSETS_DIR, "sfx_final10.mp3")
    if not os.path.exists(path):
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    components.html(
        f"""
        <script>
        (function(){{
          const root = window.parent || window;
          if (root.__terra_final10__) return;
          const a = root.document.createElement('audio');
          a.src = "data:audio/mpeg;base64,{b64}";
          a.autoplay = true;
          a.volume = 0.9;
          a.style.display = 'none';
          root.document.body.appendChild(a);
          root.__terra_final10__ = a;
          a.addEventListener('ended', function(){{
            try{{ a.remove(); root.__terra_final10__ = null; }}catch(e){{}}
          }});
          function tryPlay(){{ a.play().catch(function(){{}}); }}
          tryPlay();
          ['click','touchstart','keydown'].forEach(function(ev){{
            root.addEventListener(ev, tryPlay, {{ once:true, passive:true }});
          }});
        }})();
        </script>
        """,
        height=0, width=0
    )

def stop_final10() -> None:
    """Corta inmediatamente la música de los últimos 10s si está sonando."""
    components.html(
        """
        <script>
        (function(){
          const root = window.parent || window;
          const a = root.__terra_final10__;
          if (a){
            try { a.pause(); a.currentTime = 0; a.remove(); } catch(e){}
            try { root.__terra_final10__ = null; } catch(e){}
          }
        })();
        </script>
        """,
        height=0, width=0
    )

# cargar estilos y fondo lo antes posible
load_css()
inject_background_image(BG_PATH)

# ==========================
# CONSTANTES
# ==========================
def count_questions() -> int:
    if os.path.exists(QUESTIONS_PATH):
        try:
            df = pd.read_csv(QUESTIONS_PATH)
            return int(len(df.dropna(subset=["question"])))
        except Exception:
            return 0
    return 0

TIME_LIMIT       = 30
POINTS_CORRECT   = 10
BONUS_FAST       = 5
BONUS_FAST_THRESHOLD = 10

RANKS = [
    (0, 30, "Aprendiz Terra"),
    (31, 80, "Asesor Jr."),
    (81, 120, "Asesor Senior."),
    (121, 9999, "Maestro Terra"),
]

# nombre válido (solo letras y espacios, con acentos) 2–40
NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,40}$")

# ==========================
# UTILS
# ==========================
def _is_institutional(question: str, category_val: str) -> bool:
    if category_val:
        if str(category_val).strip().lower().startswith("inst"):
            return True
    q = (question or "").lower()
    terms = [
        "terraloteos", "terra", "institucional", "misión", "vision", "visión",
        "valores", "empresa", "oficinas", "beneficios", "plusvalía", "rentabilidad"
    ]
    return any(t in q for t in terms)

def load_questions() -> List[Dict[str, Any]]:
    questions_all: List[Dict[str, Any]] = []
    if os.path.exists(QUESTIONS_PATH) and os.path.getsize(QUESTIONS_PATH) > 0:
        try:
            df = pd.read_csv(QUESTIONS_PATH)
            for _, row in df.iterrows():
                if pd.isna(row.get("question")):
                    continue
                opts = []
                for i in range(1, 4 + 1):
                    val = row.get(f"option{i}")
                    if pd.notna(val):
                        opts.append(str(val))
                if not opts:
                    continue
                raw_idx = row.get("answer_index")
                if raw_idx is None or str(raw_idx).strip() == "":
                    continue
                try:
                    ans = int(float(str(raw_idx).strip()))
                except (ValueError, TypeError):
                    continue
                if not (0 <= ans < len(opts)):
                    continue
                category_val = ""
                if "category" in df.columns:
                    category_val = row.get("category", "")
                elif "categoria" in df.columns:
                    category_val = row.get("categoria", "")
                questions_all.append({
                    "question": str(row["question"]),
                    "options": opts,
                    "answer": ans,
                    "category": category_val
                })
        except (EmptyDataError, FileNotFoundError):
            pass

    instit, otras = [], []
    for q in questions_all:
        (instit if _is_institutional(q.get("question", ""), q.get("category", "")) else otras).append(q)
    random.shuffle(instit)
    random.shuffle(otras)
    return instit + otras

def ensure_leaderboard() -> None:
    cols = ["name", "score", "rank", "timestamp"]
    if not os.path.exists(LEADERBOARD_PATH):
        pd.DataFrame(columns=cols).to_csv(LEADERBOARD_PATH, index=False)
        return
    try:
        df = pd.read_csv(LEADERBOARD_PATH)
    except Exception:
        pd.DataFrame(columns=cols).to_csv(LEADERBOARD_PATH, index=False)
        return
    changed = False
    if "rank" not in df.columns:
        df["rank"] = ""
        changed = True
    for c in cols:
        if c not in df.columns:
            df[c] = "" if c in ("name", "rank", "timestamp") else 0
            changed = True
    if changed:
        df = df[cols]
        df.to_csv(LEADERBOARD_PATH, index=False)

def save_score(name: str, score: int, rank: str) -> None:
    """Guarda el puntaje (robusto)."""
    ensure_leaderboard()
    try:
        df = pd.read_csv(LEADERBOARD_PATH)
    except Exception:
        df = pd.DataFrame(columns=["name", "score", "rank", "timestamp"])
    ts = datetime.now().isoformat(timespec='seconds')
    new_row = {"name": name.strip()[:40], "score": int(score), "rank": rank, "timestamp": ts}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df = df.sort_values(["score", "timestamp"], ascending=[False, True]).reset_index(drop=True)
    df.to_csv(LEADERBOARD_PATH, index=False)

def get_rank(score: int) -> str:
    for lo, hi, label in RANKS:
        if lo <= score <= hi:
            return label
    return RANKS[-1][2]

def reset_quiz() -> None:
    st.session_state.questions = load_questions()
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.start_time = datetime.now()
    st.session_state.answered = False
    st.session_state.selected = None
    st.session_state.saved_pos = None
    st.session_state.final10_played = False

def _valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name.strip())) if name else False

# ==========================
# STATE
# ==========================
if "questions" not in st.session_state:
    st.session_state.questions = load_questions()
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = datetime.now()
if "answered" not in st.session_state:
    st.session_state.answered = False
if "selected" not in st.session_state:
    st.session_state.selected = None
if "name" not in st.session_state:
    st.session_state.name = ""
if "saved_pos" not in st.session_state:
    st.session_state.saved_pos = None
if "started" not in st.session_state:
    st.session_state.started = False
if "final10_played" not in st.session_state:
    st.session_state.final10_played = False

TOTAL_QUESTIONS = len(st.session_state.questions)
if TOTAL_QUESTIONS == 0:
    st.error("No hay preguntas cargadas en data/preguntas.csv")
    st.stop()

# ==========================
# LANDING
# ==========================
if not st.session_state.started:
    stop_quiz_music()
    col_l, col_c, col_r = st.columns([1, 10, 1])
    with col_c:
        st.markdown(get_logo_html(480), unsafe_allow_html=True)
        st.markdown("<h1 class='hero-title'>Bienvenidos</h1>", unsafe_allow_html=True)
        st.markdown(
            f"<p class='hero-text'>Este quiz está diseñado para evaluar y reforzar conocimientos "
            f"clave del proceso comercial y la atención a clientes en Terraloteos. Responderás {TOTAL_QUESTIONS} "
            f"preguntas con 30 segundos por pregunta. Sumás puntos por aciertos y podrás compararte "
            f"en el Ranking Top 5.</p>",
            unsafe_allow_html=True
        )
        b1, b2, b3 = st.columns([4, 2, 4])
        with b2:
            start = st.button("Comenzamos 🦊", key="start_btn")
    if start:
        st.session_state.started = True
        st.session_state.start_time = datetime.now()
        st.session_state.final10_played = False
        st.rerun()
    st.stop()

# ==========================
# QUIZ
# ==========================
mount_quiz_music()

ql, qc, qr = st.columns([1, 10, 1])
with qc:
    st.markdown(get_logo_html(360), unsafe_allow_html=True)

# KPIs
current_q = min(st.session_state.idx + 1, TOTAL_QUESTIONS)
st.markdown(
    "<div class='kpi-floating'>"
    f"<div class='pill'>Preguntas: {current_q}/{TOTAL_QUESTIONS}</div>"
    f"<div class='pill'>Puntos: <span class='score'>{st.session_state.score}</span></div>"
    "</div>",
    unsafe_allow_html=True
)

# ====== Progreso del quiz (para el zorro) ======
completed = st.session_state.idx  # preguntas finalizadas
foxy_pct = int(100 * completed / TOTAL_QUESTIONS) if TOTAL_QUESTIONS > 0 else 0

# ====== SOLO mostrar FOX ROAD durante el quiz (1) evita duplicado al final ======
if st.session_state.idx < TOTAL_QUESTIONS:
    st.markdown(foxy_scene_html(foxy_pct, trees=9), unsafe_allow_html=True)

    # ----- Timer y pregunta actual -----
    now = datetime.now()
    elapsed = (now - st.session_state.start_time).total_seconds()
    remaining = max(0, TIME_LIMIT - int(elapsed))
    try:
        st_autorefresh = importlib.import_module("streamlit_autorefresh").st_autorefresh
    except Exception:
        def st_autorefresh(*args, **kwargs): return None
    st_autorefresh(interval=1000, key=f"tick_{st.session_state.idx}")
    st.markdown(f"**Tiempo:** <span class='timer'>{remaining:02d}s</span>", unsafe_allow_html=True)

    # 5) Últimos 10s: pausar música base y reproducir suspenso
    if (remaining <= 10) and (remaining > 0) and (not st.session_state.final10_played) and (not st.session_state.answered):
        pause_quiz_music()
        play_final10()
        st.session_state.final10_played = True

    # Tiempo agotado -> avanza
    if remaining == 0 and not st.session_state.answered:
        stop_final10()
        resume_quiz_music()  # reanuda música al pasar de pregunta
        st.session_state.idx += 1
        st.session_state.start_time = datetime.now()
        st.session_state.selected = None
        st.session_state.answered = False
        st.session_state.final10_played = False
        st.rerun()

    q = st.session_state.questions[st.session_state.idx]
    st.subheader(q["question"])
    choice = st.radio(
        "Elegí una opción:",
        options=list(enumerate(q["options"])),
        format_func=lambda x: x[1],
        index=0 if st.session_state.selected is None else st.session_state.selected,
        disabled=st.session_state.answered
    )
    if not st.session_state.answered:
        st.session_state.selected = choice[0]

    # 6) Eliminar botón "Saltar" -> solo "Responder"
    submit = st.button("Responder", key=f"submit_{st.session_state.idx}", disabled=st.session_state.answered)

    if submit and not st.session_state.answered:
        st.session_state.answered = True
        is_correct = (st.session_state.selected == q["answer"])
        stop_final10()
        resume_quiz_music()  # vuelve la música normal tras responder
        if is_correct:
            pts = POINTS_CORRECT
            if (TIME_LIMIT - remaining) <= BONUS_FAST_THRESHOLD:
                pts += BONUS_FAST
            st.session_state.score += pts
            st.success(f"Correcto. Sumaste {pts} puntos.")
        else:
            st.error("Respuesta incorrecta.")
            play_quack()

        # Avanza siempre
        st.session_state.idx += 1
        st.session_state.start_time = datetime.now()
        st.session_state.selected = None
        st.session_state.answered = False
        st.session_state.final10_played = False
        st.rerun()

    if st.session_state.answered:
        if st.button("Siguiente", key=f"next_{st.session_state.idx}"):
            stop_final10()
            resume_quiz_music()
            st.session_state.idx += 1
            st.session_state.start_time = datetime.now()
            st.session_state.answered = False
            st.session_state.selected = None
            st.session_state.final10_played = False
            st.rerun()

# ==========================
# FINAL
# ==========================
if st.session_state.idx >= TOTAL_QUESTIONS:
    # zorro al 100% en pantalla final (1) solo una vez
    st.markdown(foxy_scene_html(100, trees=9), unsafe_allow_html=True)

    st.markdown("## Resultado final")
    total = st.session_state.score
    rank = get_rank(total)
    max_posible = TOTAL_QUESTIONS * (POINTS_CORRECT + BONUS_FAST)
    _ = max_posible  # calculado pero no mostrado

    st.metric(label="Puntaje", value=total)
    st.markdown(f"**Rango obtenido:** <span class='rank-chip'>{rank}</span>", unsafe_allow_html=True)

    # Imagen por rango
    show_rank_meme(rank)

    if str(rank).strip().lower() != "maestro terra":
        st.markdown(
            "<div style='text-align:center'>"
            "Falta lectura del contenido... "
            "Te dejo el material oficial para prepararte: "
            "<a href='https://drive.google.com/drive/folders/1gM21hO56URb9LMkaAz8CY_OEldqJ29pt?usp=sharing' target='_blank'>Carpeta Terraloteos</a>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div class='motivational-quote'>"
            "UN ASESOR SIN PREPARACIÓN ES UN ESPECTADOR.... Y VOS VINISTE A SER PROTAGONISTA!"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.balloons()

    # INPUT + BOTÓN (nombre obligatorio y campo BLANCO)
    col_input, col_btn = st.columns([2,1])

    with col_input:
        name = st.text_input(
            "Escribí tu nombre para el ranking:",
            value=st.session_state.name,
            placeholder="Nombre y apellido"
        )
        name_valid = _valid_name(name)
        if name and not name_valid:
            st.caption("Usá solo letras y espacios (2 a 40 caracteres).")

    with col_btn:
        st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)
        if st.button("Guardar en Ranking", key="save_rank_btn", disabled=not _valid_name(name)):
            if _valid_name(name):
                try:
                    save_score(name, total, rank)
                    st.success("Puntaje guardado en el ranking.")
                    st.session_state.name = name
                    st.session_state.saved_pos = True
                    st.rerun()  # refresca la tabla inmediatamente
                except Exception as e:
                    st.error(f"No se pudo guardar el ranking: {e}")
            else:
                st.error("El nombre no es válido. Solo letras y espacios.")

    # Ranking
    ensure_leaderboard()
    try:
        df = pd.read_csv(LEADERBOARD_PATH)
    except Exception:
        df = pd.DataFrame(columns=["name", "rank", "score", "timestamp"])

    if not df.empty:
        st.markdown("### 🏆 Ranking")
        df = df.sort_values(["score", "timestamp"], ascending=[False, True]).reset_index(drop=True)

        rows_html = []
        for pos, (_, row) in enumerate(df.iterrows(), start=1):
            name = str(row.get("name", ""))
            rango = str(row.get("rank", ""))
            puntaje = int(row.get("score", 0))
            info = str(row.get("timestamp", ""))
            cls = "leaderboard-row top5" if pos <= 5 else "leaderboard-row"
            rows_html.append(
                f"<tr class='{cls}'>"
                f"<td class='pos'>#{pos}</td>"
                f"<td>{name}</td>"
                f"<td>{rango}</td>"
                f"<td class='score-cell'>{puntaje}</td>"
                f"<td class='ts'>{info}</td>"
                f"</tr>"
            )

        table_html = (
            "<div class='leaderboard-box'>"
            "<table class='leaderboard-table'>"
            "<thead><tr>"
            "<th>#</th><th>Nombre</th><th>Rango</th><th>Puntaje</th><th>Información</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table>"
            "</div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("Aún no hay puntajes guardados.")
