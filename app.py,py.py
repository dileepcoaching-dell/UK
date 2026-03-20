import streamlit as st
import pandas as pd
import io
import os
import re
import json
import sys
from collections import OrderedDict

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CA Article Toolkit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── User Store (file-backed so admin changes persist) ────────────────────────
def get_users_file_path():
    if getattr(sys, 'frozen', False):
        # Running as a bundled EXE
        return os.path.join(os.path.dirname(sys.executable), "users.json")
    else:
        # Running as a normal script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

USERS_FILE = get_users_file_path()

DEFAULT_USERS = {
    "admin":   {"password": "admin123",    "role": "admin"},
    "article": {"password": "article@2025","role": "user"},
}

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # First-time initialise
    save_users(DEFAULT_USERS)
    return DEFAULT_USERS

def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f, indent=2)

# ─── Session State Init ───────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = "user"
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"


# ─────────────────────────────────────────────────────────────────────────────
#  GSTR-2A Logic (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
MONTH_MAP = {
    '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
}

SHEET_CONFIG = OrderedDict({
    "B2B":      {"header_start": 4, "header_rows": 2},
    "B2BA":     {"header_start": 4, "header_rows": 3},
    "CDNR":     {"header_start": 4, "header_rows": 2},
    "CDNRA":    {"header_start": 4, "header_rows": 3},
    "ECO":      {"header_start": 4, "header_rows": 2},
    "ECOA":     {"header_start": 4, "header_rows": 3},
    "ISD":      {"header_start": 4, "header_rows": 2},
    "ISDA":     {"header_start": 4, "header_rows": 3},
    "TDS":      {"header_start": 4, "header_rows": 2},
    "TDSA":     {"header_start": 4, "header_rows": 2},
    "TCS":      {"header_start": 4, "header_rows": 2},
    "IMPG":     {"header_start": 4, "header_rows": 2},
    "IMPG SEZ": {"header_start": 4, "header_rows": 2},
})


def format_source_name(filename):
    basename = os.path.splitext(filename)[0]
    match = re.search(r'_(\d{6})(?:_|$)', basename)
    if match:
        mmyyyy = match.group(1)
        month = mmyyyy[:2]
        year  = mmyyyy[2:]
        if month in MONTH_MAP:
            return f"{MONTH_MAP[month]} {year}"
    return basename


def build_merged_header(df_raw, config):
    start    = config["header_start"]
    num_rows = config["header_rows"]
    header_rows = []
    for i in range(num_rows):
        row_idx = start + i
        header_rows.append(df_raw.iloc[row_idx].tolist() if row_idx < len(df_raw)
                           else [None] * len(df_raw.columns))
    merged_names = []
    for col_idx in range(len(df_raw.columns)):
        parts = []
        for row in header_rows:
            if col_idx < len(row):
                val = row[col_idx]
                if pd.notna(val):
                    v = str(val).strip()
                    if v and v not in parts:
                        parts.append(v)
        merged_names.append(" - ".join(parts) if parts else f"Column_{col_idx+1}")
    seen, unique = {}, []
    for name in merged_names:
        if name in seen:
            seen[name] += 1
            unique.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            unique.append(name)
    return unique


def extract_sheet_data(file_bytes, filename, sheet_name, config):
    try:
        df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name,
                               header=None, dtype=str)
    except Exception:
        return None
    headers    = build_merged_header(df_raw, config)
    data_start = config["header_start"] + config["header_rows"]
    if data_start >= len(df_raw):
        return None
    df_data = df_raw.iloc[data_start:].copy()
    df_data.columns = headers[:len(df_data.columns)]
    df_data = df_data.dropna(how='all')
    if df_data.empty:
        return None
    SHEETS_WITH_RATE = {"B2B","B2BA","CDNR","CDNRA","ECO","ECOA"}
    if sheet_name in SHEETS_WITH_RATE:
        rate_col = next((c for c in df_data.columns if "Rate" in str(c) and "%" in str(c)), None)
        if rate_col:
            df_data = df_data[df_data[rate_col].astype(str).str.strip() != "-"]
            df_data = df_data.reset_index(drop=True)
    if df_data.empty:
        return None
    df_data.insert(0, "Source File", format_source_name(filename))
    return df_data.reset_index(drop=True)


def consolidate_files(uploaded_files, selected_sheets, progress_bar=None, status_text=None):
    consolidated = {s: [] for s in selected_sheets}
    file_stats   = {}
    total_steps  = len(uploaded_files) * len(selected_sheets)
    step = 0
    for file in uploaded_files:
        file_bytes = file.read()
        file.seek(0)
        fname = file.name
        file_stats[fname] = {}
        for sheet_name in selected_sheets:
            step += 1
            if progress_bar: progress_bar.progress(step / total_steps)
            if status_text:  status_text.text(f"Processing: {fname} → {sheet_name}")
            df = extract_sheet_data(file_bytes, fname, sheet_name, SHEET_CONFIG[sheet_name])
            if df is not None and not df.empty:
                consolidated[sheet_name].append(df)
                file_stats[fname][sheet_name] = len(df)
            else:
                file_stats[fname][sheet_name] = 0
    result = {}
    for sn in selected_sheets:
        dfs = consolidated[sn]
        result[sn] = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return result, file_stats


def create_output_excel(consolidated_data):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        hfmt = wb.add_format({'bold':True,'bg_color':'#4F46E5','font_color':'#FFFFFF',
                               'border':1,'text_wrap':True,'valign':'vcenter','align':'center','font_size':10})
        sfmt = wb.add_format({'bold':True,'bg_color':'#059669','font_color':'#FFFFFF',
                               'border':1,'text_wrap':True,'valign':'vcenter','align':'center','font_size':10})
        for sn, df in consolidated_data.items():
            if df.empty:
                pd.DataFrame({"Note":[f"No data for {sn}"]}).to_excel(writer,sheet_name=sn,index=False)
                continue
            df.to_excel(writer, sheet_name=sn, index=False, startrow=1, header=False)
            ws = writer.sheets[sn]
            for ci, cn in enumerate(df.columns):
                ws.write(0, ci, cn, sfmt if cn=="Source File" else hfmt)
            for ci, cn in enumerate(df.columns):
                mlen = max(len(str(cn)),
                           df.iloc[:,ci].astype(str).str.len().max() if len(df) else 0)
                ws.set_column(ci, ci, min(max(mlen+2,10),40))
            ws.freeze_panes(1,1)
            if len(df.columns):
                ws.autofilter(0,0,len(df),len(df.columns)-1)
    output.seek(0)
    return output


# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL CSS  (dark theme for logged-in views)
# ─────────────────────────────────────────────────────────────────────────────
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --primary:#2563eb; --primary-dk:#1d4ed8; --primary-lt:#3b82f6;
    --accent:#06b6d4; --success:#10b981;
    --bg-dark:#0f172a; --bg-card:#1e293b; --bg-hover:#334155;
    --txt:#f1f5f9; --txt2:#94a3b8; --border:#334155;
    --grad:linear-gradient(135deg,#2563eb,#06b6d4);
}
.stApp { background:var(--bg-dark)!important; font-family:'Inter',sans-serif!important; }
#MainMenu,footer,header{visibility:hidden;}
section[data-testid="stSidebar"]{background:#0d1526!important;border-right:1px solid var(--border);}
section[data-testid="stSidebar"] *{color:var(--txt)!important;}

/* Buttons */
.stButton>button{
    background:var(--grad)!important;color:white!important;border:none!important;
    border-radius:10px!important;padding:.6rem 2rem!important;font-weight:600!important;
    font-size:.95rem!important;transition:all .3s ease!important;
    box-shadow:0 4px 15px rgba(37,99,235,.3)!important;width:100%;
}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(37,99,235,.45)!important;}

/* Download */
.stDownloadButton>button{
    background:var(--grad)!important;color:white!important;border:none!important;
    border-radius:10px!important;font-weight:600!important;
    box-shadow:0 4px 15px rgba(37,99,235,.3)!important;
}

/* Inputs */
.stTextInput>div>div>input{
    background:#1e293b!important;color:var(--txt)!important;
    border:1px solid var(--border)!important;border-radius:10px!important;
}
.stTextInput>div>div>input:focus{border-color:var(--primary)!important;box-shadow:0 0 0 2px rgba(37,99,235,.25)!important;}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:var(--bg-card);border-radius:12px;padding:4px;border:1px solid var(--border);}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:var(--txt2);font-weight:500;padding:8px 16px;}
.stTabs [aria-selected="true"]{background:var(--grad)!important;color:white!important;}
.stProgress>div>div>div>div{background:var(--grad)!important;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:var(--bg-dark);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--primary);}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: LOGIN  — clean Instagram-style
# ═══════════════════════════════════════════════════════════════════════════════
def show_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    .stApp{background:#fafafa!important;font-family:'Inter',sans-serif!important;}
    .main .block-container{padding:0!important;max-width:100%!important;}
    section[data-testid="stSidebar"]{display:none!important;}
    #MainMenu,footer,header{visibility:hidden;}

    /* ── input fields ── */
    .stTextInput>label{display:none!important;}
    .stTextInput>div>div>input{
        background:#fafafa!important;border:1px solid #dbdbdb!important;
        border-radius:4px!important;color:#262626!important;
        font-size:.9rem!important;padding:10px 12px!important;height:40px!important;
    }
    .stTextInput>div>div>input:focus{border-color:#a8a8a8!important;background:#fff!important;box-shadow:none!important;}
    .stTextInput>div>div>input::placeholder{color:#aaa!important;font-size:.85rem!important;}

    /* ── checkbox ── */
    .stCheckbox>label{color:#262626!important;font-size:.83rem!important;}

    /* ── login button ── */
    .stButton>button{
        background:#0095f6!important;color:#fff!important;border:none!important;
        border-radius:8px!important;font-weight:600!important;font-size:.9rem!important;
        padding:.55rem 1rem!important;width:100%!important;
        transition:background .2s!important;box-shadow:none!important;
    }
    .stButton>button:hover{background:#1877f2!important;transform:none!important;box-shadow:none!important;}

    /* ── divider ── */
    .ig-divider{display:flex;align-items:center;gap:12px;margin:18px 0;}
    .ig-divider-line{flex:1;height:1px;background:#dbdbdb;}
    .ig-divider-text{color:#8e8e8e;font-size:.78rem;font-weight:600;letter-spacing:.8px;}

    /* ── links ── */
    .ig-links{display:flex;flex-direction:column;align-items:center;gap:10px;margin-top:4px;}
    .ig-link{color:#0095f6;font-size:.83rem;font-weight:500;text-decoration:none;}
    .ig-link:hover{color:#0065d0;text-decoration:underline;}
    .ig-link.wa{color:#25d366;}.ig-link.wa:hover{color:#128c7e;}

    /* ── bottom card ── */
    .ig-bottom{
        background:#fff;border:1px solid #dbdbdb;border-radius:4px;
        padding:18px;width:100%;max-width:380px;text-align:center;
        margin-top:10px;font-size:.85rem;color:#262626;box-sizing:border-box;
    }
    .ig-bottom a{color:#0095f6;font-weight:700;text-decoration:none;}
    .ig-bottom a:hover{text-decoration:underline;}
    .stAlert{border-radius:4px!important;font-size:.85rem!important;}
    @media(max-width:480px){.ig-card{border:none;}.ig-bottom{border:none;}}
    </style>
    """, unsafe_allow_html=True)

    # ─── Centered card header (pure HTML) ────────────────────────────────────
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # White card box
        st.markdown("""
        <div style="background:#fff;border:1px solid #dbdbdb;border-radius:4px;
                    padding:36px 36px 24px;box-sizing:border-box;">
            <!-- UK Logo -->
            <div style="text-align:center;margin-bottom:14px;">
                <span style="font-size:2.6rem;font-weight:900;color:#1a1a2e;
                             letter-spacing:-2px;font-family:'Inter',sans-serif;">
                    UK
                </span>
            </div>
            <div style="text-align:center;font-size:1rem;color:#8e8e8e;
                        margin-bottom:22px;font-size:.82rem;">
                Sign in to CA Article Toolkit
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Widgets ──
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        username = st.text_input("u", placeholder="Username", key="login_user",
                                 label_visibility="collapsed")
        password = st.text_input("p", placeholder="Password",
                                 type="password", key="login_pass",
                                 label_visibility="collapsed")
        st.checkbox("Remember Me", key="login_remember")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("Log in", key="login_btn", use_container_width=True):
            users = load_users()
            if username in users and users[username]["password"] == password:
                st.session_state.logged_in   = True
                st.session_state.username    = username
                st.session_state.role        = users[username].get("role", "user")
                st.session_state.current_page = "dashboard"
                st.rerun()
            else:
                st.error("The username or password you entered is incorrect.")

        st.markdown("""
        <div class="ig-divider">
            <div class="ig-divider-line"></div>
            <div class="ig-divider-text">OR</div>
            <div class="ig-divider-line"></div>
        </div>
        <div class="ig-links">
            <a class="ig-link" href="#"
               onclick="alert('Please contact your admin to reset your password.'); return false;">
               🔑 Forgot password?
            </a>
            <a class="ig-link wa"
               href="https://wa.me/918555954024?text=Hello%20Admin%2C%20I%20need%20access%20to%20the%20CA%20Article%20Toolkit"
               target="_blank">
               💬 Contact Admin
            </a>
        </div>
        """, unsafe_allow_html=True)

    _, col2, _ = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="ig-bottom">
            Don't have an account?
            <a href="https://wa.me/918555954024?text=Hello%20Admin%2C%20I%20need%20access%20to%20the%20CA%20Article%20Toolkit"
               target="_blank">Contact admin.</a>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════
def show_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:.8rem 0 .5rem;text-align:center;">
            <span style="font-size:1.8rem;font-weight:900;color:#f1f5f9;letter-spacing:-2px;">UK</span><br>
            <span style="font-size:.75rem;background:linear-gradient(135deg,#2563eb,#06b6d4);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                         background-clip:text;font-weight:700;">CA Article Toolkit</span>
        </div>
        <div style="text-align:center;color:#64748b;font-size:.72rem;margin-bottom:.6rem;">
            Welcome, <b style="color:#94a3b8;">{st.session_state.username}</b>
            {"&nbsp;🛡️" if st.session_state.role=="admin" else ""}
        </div>
        <hr style="border-color:#334155;margin:.5rem 0;"/>
        """, unsafe_allow_html=True)

        st.markdown("**Navigation**")

        pages = {
            "dashboard": ("🏠", "Dashboard"),
            "gstr2a":    ("📊", "GSTR-2A Consolidator"),
        }
        if st.session_state.role == "admin":
            pages["admin"] = ("🔧", "Admin Panel")

        for page_key, (icon, label) in pages.items():
            is_active = st.session_state.current_page == page_key
            if st.button(f"{icon} {label}", key=f"nav_{page_key}",
                         use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.current_page = page_key
                st.rerun()

        st.markdown("<hr style='border-color:#334155;margin:.8rem 0;'/>", unsafe_allow_html=True)

        # ── Logout ──
        if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True):
            keys_to_keep = []
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.session_state.logged_in    = False
            st.session_state.username     = ""
            st.session_state.role         = "user"
            st.session_state.current_page = "dashboard"
            st.rerun()

        st.markdown("""
        <div style="margin-top:1rem;text-align:center;color:#334155;font-size:.68rem;">
            CA Article Toolkit v1.0
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="padding:.6rem 0 .4rem;">
        <h1 style="font-size:1.7rem;font-weight:800;
                   background:linear-gradient(135deg,#2563eb,#06b6d4);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;margin:0;">
            📊 CA Article Toolkit
        </h1>
        <p style="color:#64748b;font-size:.83rem;margin:.2rem 0 0;">
            Your professional CA firm management dashboard
        </p>
    </div>
    <hr style="border-color:#334155;margin:.6rem 0 1.5rem;"/>
    <div style="background:linear-gradient(135deg,rgba(37,99,235,.13),rgba(6,182,212,.08));
                border:1px solid rgba(37,99,235,.22);border-radius:14px;
                padding:1.2rem 1.6rem;margin-bottom:1.8rem;">
        <h2 style="color:#f1f5f9;margin:0;font-size:1.25rem;">
            👋 Welcome back,
            <span style="color:#3b82f6;">{st.session_state.username.capitalize()}</span>!
        </h2>
        <p style="color:#64748b;margin:.3rem 0 0;font-size:.85rem;">
            Select a tool below or use the sidebar to navigate.
        </p>
    </div>
    <h3 style="color:#f1f5f9;font-weight:700;font-size:1.05rem;margin-bottom:1rem;">
        🛠️ Available Tools
    </h3>
    """, unsafe_allow_html=True)

    tools = [
        {"key":"gstr2a","icon":"📊","title":"GSTR-2A Consolidator","badge":"GST","color":"#2563eb",
         "desc":"Upload multiple GSTR-2A files and consolidate them into one Excel file with source tracking."},
    ]

    cols = st.columns(3)
    for i, tool in enumerate(tools):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background:#1e293b;border:1px solid #334155;border-radius:14px;
                        padding:1.4rem;margin-bottom:.8rem;position:relative;overflow:hidden;">
                <div style="position:absolute;top:0;left:0;right:0;height:3px;
                            background:linear-gradient(90deg,{tool['color']},{tool['color']}88);"></div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.7rem;">
                    <span style="font-size:2rem;">{tool['icon']}</span>
                    <span style="background:rgba(37,99,235,.15);color:#3b82f6;
                                 font-size:.68rem;font-weight:700;padding:.2rem .55rem;
                                 border-radius:20px;">{tool['badge']}</span>
                </div>
                <div style="font-weight:700;color:#f1f5f9;font-size:.95rem;margin-bottom:.4rem;">{tool['title']}</div>
                <div style="color:#64748b;font-size:.8rem;line-height:1.5;margin-bottom:.9rem;">{tool['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open {tool['title']} →", key=f"open_{tool['key']}", use_container_width=True):
                st.session_state.current_page = tool["key"]
                st.rerun()

    with cols[1]:
        st.markdown("""
        <div style="background:#1e293b;border:1px dashed #334155;border-radius:14px;
                    padding:1.4rem;text-align:center;opacity:.55;margin-bottom:.8rem;">
            <div style="font-size:2rem;margin-bottom:.4rem;">⏳</div>
            <div style="font-weight:600;color:#64748b;font-size:.88rem;">More Tools Coming Soon</div>
            <div style="color:#475569;font-size:.75rem;margin-top:.3rem;">Sampling, Reconciliation & more</div>
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown("""
        <a href="https://wa.me/918555954024?text=Hello%20Admin%2C%20I%20have%20a%20tool%20request"
           target="_blank" style="text-decoration:none;">
            <div style="background:linear-gradient(135deg,#075e54,#128c7e);color:white;
                        text-align:center;padding:.8rem;border-radius:12px;font-size:.83rem;
                        font-weight:600;cursor:pointer;">
                💬 Request a Tool via WhatsApp
            </div>
        </a>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════════
def show_admin():
    st.markdown(DARK_CSS, unsafe_allow_html=True)

    st.markdown("""
    <h1 style="font-size:1.7rem;font-weight:800;
               background:linear-gradient(135deg,#2563eb,#06b6d4);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;margin:0 0 .3rem;">
        🔧 Admin Panel
    </h1>
    <p style="color:#64748b;font-size:.83rem;margin:0 0 1.2rem;">
        Manage users and access credentials
    </p>
    <hr style="border-color:#334155;margin-bottom:1.5rem;"/>
    """, unsafe_allow_html=True)

    users = load_users()

    # ── Current Users Table ──────────────────────────────────────────────────
    st.markdown("### 👥 Current Users")
    user_data = [{"Username": u, "Role": d["role"], "Password": "••••••••"}
                 for u, d in users.items()]
    st.dataframe(pd.DataFrame(user_data), use_container_width=True, hide_index=True)

    st.markdown("<hr style='border-color:#334155;margin:1.2rem 0;'/>", unsafe_allow_html=True)

    # ── Add New User ─────────────────────────────────────────────────────────
    st.markdown("### ➕ Add New User")
    c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1])
    with c1:
        new_user = st.text_input("Username", key="new_username", placeholder="Enter username")
    with c2:
        new_pass = st.text_input("Password", key="new_password", placeholder="Enter password")
    with c3:
        new_role = st.selectbox("Role", ["user", "admin"], key="new_role")
    with c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("➕ Add User", key="add_user_btn", use_container_width=True):
            if not new_user.strip():
                st.error("Username cannot be empty.")
            elif new_user in users:
                st.error(f"User **{new_user}** already exists.")
            elif len(new_pass) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                users[new_user] = {"password": new_pass, "role": new_role}
                save_users(users)
                st.success(f"✅ User **{new_user}** added successfully!")
                st.rerun()

    st.markdown("<hr style='border-color:#334155;margin:1.2rem 0;'/>", unsafe_allow_html=True)

    # ── Change Password ───────────────────────────────────────────────────────
    st.markdown("### 🔑 Change Password")
    cp_c1, cp_c2, cp_c3 = st.columns([2, 2, 1.5])
    with cp_c1:
        chg_user = st.selectbox("Select User", list(users.keys()), key="chg_user")
    with cp_c2:
        chg_pass = st.text_input("New Password", key="chg_pass", placeholder="New password")
    with cp_c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔑 Update Password", key="chg_pass_btn", use_container_width=True):
            if len(chg_pass) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                users[chg_user]["password"] = chg_pass
                save_users(users)
                st.success(f"✅ Password for **{chg_user}** updated!")
                st.rerun()

    st.markdown("<hr style='border-color:#334155;margin:1.2rem 0;'/>", unsafe_allow_html=True)

    # ── Delete User ───────────────────────────────────────────────────────────
    st.markdown("### 🗑️ Remove User")
    del_c1, del_c2 = st.columns([3, 1.5])
    removable = [u for u in users.keys() if u != st.session_state.username]
    with del_c1:
        del_user = st.selectbox("Select User to Remove",
                                removable if removable else ["(none)"],
                                key="del_user")
    with del_c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if removable and st.button("🗑️ Remove User", key="del_user_btn", use_container_width=True):
            del users[del_user]
            save_users(users)
            st.success(f"✅ User **{del_user}** removed.")
            st.rerun()
    if not removable:
        st.info("No other users to remove.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: GSTR-2A CONSOLIDATOR
# ═══════════════════════════════════════════════════════════════════════════════
def show_gstr2a():
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.markdown("""
    <style>
    .stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin:1.2rem 0;}
    .stat-card{background:#1e293b;border:1px solid #334155;border-radius:14px;padding:1.2rem 1.5rem;
               text-align:center;position:relative;overflow:hidden;}
    .stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
                       background:linear-gradient(135deg,#2563eb,#06b6d4);}
    .stat-card .sv{font-size:1.9rem;font-weight:700;color:#f1f5f9;line-height:1;}
    .stat-card .sl{font-size:.73rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;
                   margin-top:.4rem;font-weight:500;}
    .file-card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:.75rem 1.1rem;
               margin:.4rem 0;display:flex;align-items:center;gap:.7rem;}
    .fn{color:#f1f5f9;font-weight:500;font-size:.88rem;}
    .fs{color:#64748b;font-size:.73rem;margin-left:auto;}
    .sbadge{display:inline-block;background:rgba(37,99,235,.14);border:1px solid rgba(37,99,235,.3);
            color:#60a5fa;padding:.23rem .65rem;border-radius:20px;font-size:.75rem;font-weight:500;margin:.2rem;}
    .sbadge.hd{background:rgba(16,185,129,.14);border-color:rgba(16,185,129,.3);color:#34d399;}
    .ok-banner{background:linear-gradient(135deg,rgba(16,185,129,.11),rgba(6,182,212,.07));
               border:1px solid rgba(16,185,129,.28);border-radius:14px;padding:1.3rem 1.8rem;
               text-align:center;margin:1.2rem 0;}
    </style>
    """, unsafe_allow_html=True)

    bcol, _ = st.columns([1, 9])
    with bcol:
        if st.button("← Back", key="back_to_dash"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:.8rem 1rem 0;">
        <h1 style="font-size:2.2rem;font-weight:800;
                   background:linear-gradient(135deg,#2563eb,#06b6d4);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;margin-bottom:.2rem;">
            📊 GSTR-2A Consolidator
        </h1>
        <p style="color:#64748b;font-size:.9rem;">
            Upload multiple GSTR-2A Excel files and consolidate into a single workbook
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 📋 Sheets to Consolidate")
        all_sheets = list(SHEET_CONFIG.keys())
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ All", use_container_width=True, key="sel_all"):
                st.session_state["selected_sheets"] = all_sheets
        with c2:
            if st.button("❌ Clear", use_container_width=True, key="clr_all"):
                st.session_state["selected_sheets"] = []
        if "selected_sheets" not in st.session_state:
            st.session_state["selected_sheets"] = all_sheets
        selected_sheets = []
        for s in all_sheets:
            if st.checkbox(s, value=s in st.session_state["selected_sheets"], key=f"sheet_{s}"):
                selected_sheets.append(s)
        st.session_state["selected_sheets"] = selected_sheets
        st.markdown("---")
        st.markdown("### 📖 About")
        st.markdown("Consolidates GSTR-2A Excel returns into one workbook.\n"
                    "- Multi-file upload\n- All 13 sheet types\n- Source tracking\n- Auto-filter & freeze")

    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(37,99,235,.07),rgba(6,182,212,.06));
                border:2px dashed #2563eb;border-radius:14px;padding:1.8rem;
                text-align:center;margin:1rem 0 1.3rem;">
        <div style="font-size:2.8rem;margin-bottom:.4rem;">📂</div>
        <div style="font-size:1.05rem;font-weight:600;color:#f1f5f9;">Upload GSTR-2A Excel Files</div>
        <div style="font-size:.8rem;color:#64748b;margin-top:.25rem;">
            Drag &amp; drop or browse • .xlsx • Multiple files
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload GSTR-2A Files", type=["xlsx"],
        accept_multiple_files=True, label_visibility="collapsed", key="file_uploader"
    )

    if uploaded_files:
        st.markdown("**📁 Uploaded Files**")
        html = ""
        for f in uploaded_files:
            sz = f.size/1024
            ss = f"{sz:.1f} KB" if sz<1024 else f"{sz/1024:.2f} MB"
            html += f'<div class="file-card"><span style="font-size:1.2rem;">📄</span><span class="fn">{f.name}</span><span class="fs">{ss}</span></div>'
        st.markdown(html, unsafe_allow_html=True)

        total_sz = sum(f.size for f in uploaded_files)/1024
        st.markdown(f"""
        <div class="stat-grid">
            <div class="stat-card"><div class="sv">{len(uploaded_files)}</div><div class="sl">Files Uploaded</div></div>
            <div class="stat-card"><div class="sv">{len(selected_sheets)}</div><div class="sl">Sheets Selected</div></div>
            <div class="stat-card"><div class="sv">{total_sz:.0f} KB</div><div class="sl">Total Size</div></div>
        </div>
        """, unsafe_allow_html=True)

        if selected_sheets:
            st.markdown("".join([f'<span class="sbadge">{s}</span>' for s in selected_sheets]),
                        unsafe_allow_html=True)

        if st.button("🚀 Consolidate Files", use_container_width=True,
                     type="primary", key="consolidate_btn"):
            if not selected_sheets:
                st.error("⚠️ Select at least one sheet.")
            else:
                pb = st.progress(0)
                st_txt = st.empty()
                con_data, fstats = consolidate_files(uploaded_files, selected_sheets, pb, st_txt)
                pb.progress(1.0)
                st_txt.text("✅ Done!")
                st.session_state["consolidated_data"] = con_data
                st.session_state["file_stats"]        = fstats

        if "consolidated_data" in st.session_state:
            con_data = st.session_state["consolidated_data"]
            fstats   = st.session_state["file_stats"]
            total_r  = sum(len(d) for d in con_data.values())
            non_empty = sum(1 for d in con_data.values() if not d.empty)

            st.markdown(f"""
            <div class="ok-banner">
                <h3 style="color:#10b981;margin:.3rem 0;">✅ Consolidation Complete!</h3>
                <p style="color:#64748b;font-size:.88rem;margin:0;">
                    {total_r:,} records · {non_empty} sheets · {len(fstats)} files
                </p>
            </div>
            <div class="stat-grid">
                <div class="stat-card"><div class="sv">{total_r:,}</div><div class="sl">Total Records</div></div>
                <div class="stat-card"><div class="sv">{non_empty}</div><div class="sl">Sheets w/ Data</div></div>
                <div class="stat-card"><div class="sv">{len(fstats)}</div><div class="sl">Files Processed</div></div>
            </div>
            """, unsafe_allow_html=True)

            tabs_data = [s for s in selected_sheets if not con_data.get(s, pd.DataFrame()).empty]
            if tabs_data:
                tabs = st.tabs([f"{s} ({len(con_data[s])})" for s in tabs_data])
                for tab, sn in zip(tabs, tabs_data):
                    with tab:
                        df = con_data[sn]
                        if "Source File" in df.columns:
                            fc = df["Source File"].value_counts().to_dict()
                            st.markdown("".join([
                                f'<span class="sbadge hd">{fn}: {cnt}</span>'
                                for fn, cnt in fc.items()
                            ]), unsafe_allow_html=True)
                        st.dataframe(df, use_container_width=True, height=380,
                                     column_config={"Source File": st.column_config.TextColumn(
                                         "Source File", width="medium")})
            else:
                st.info("No data found in selected sheets.")

            with st.expander("📋 File × Sheet Breakdown", expanded=False):
                rows = []
                for fn, stats in fstats.items():
                    row = {"File": os.path.splitext(fn)[0]}
                    for s in selected_sheets: row[s] = stats.get(s, 0)
                    row["Total"] = sum(stats.get(s,0) for s in selected_sheets)
                    rows.append(row)
                tot = {"File":"TOTAL"}
                for s in selected_sheets: tot[s] = sum(r.get(s,0) for r in rows)
                tot["Total"] = sum(r["Total"] for r in rows)
                rows.append(tot)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("**📥 Download**")
            out = create_output_excel(con_data)
            st.download_button("📥 Download Consolidated Excel", data=out,
                               file_name="GSTR2A_Consolidated.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
                               use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#64748b;">
            <div style="font-size:3.5rem;opacity:.35;margin-bottom:.8rem;">📂</div>
            <h3 style="color:#475569;font-weight:500;">No files uploaded yet</h3>
            <p style="font-size:.88rem;">Upload your GSTR-2A Excel files above to get started</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='text-align:center;padding:1.5rem 0 .8rem;margin-top:2.5rem;"
                "border-top:1px solid #334155;color:#334155;font-size:.76rem;'>"
                "GSTR-2A Consolidator · CA Article Toolkit</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    show_login()
else:
    show_sidebar()
    page = st.session_state.current_page
    if page == "dashboard":
        show_dashboard()
    elif page == "gstr2a":
        show_gstr2a()
    elif page == "admin" and st.session_state.role == "admin":
        show_admin()
    else:
        show_dashboard()
