import streamlit as st
import yfinance as yf
import math
import json
import base64

st.set_page_config(
    page_title="指値計算",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
html, body, [class*="css"] { font-size: 15px; }

/* PC：2列グリッド / スマホ：1列 */
.etf-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}
@media (max-width: 640px) {
    .etf-grid { grid-template-columns: 1fr; }
}

.etf-card {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid #333;
}
.etf-title { font-size: 1.0rem; font-weight: bold; color: #ffffff; margin-bottom: 2px; }
.etf-close { font-size: 0.78rem; color: #888; margin-bottom: 8px; }
.stage-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.stage-cell { background: #2a2a3e; border-radius: 8px; padding: 7px 9px; }
.stage-label { font-size: 0.68rem; color: #888; margin-bottom: 1px; }
.stage-price { font-size: 1.25rem; font-weight: bold; color: #4fc3f7; line-height: 1.1; }
.stage-sub { font-size: 0.68rem; color: #aaa; margin-top: 2px; }
[data-testid="stButton"] > button { font-size: 1rem; height: 2.8rem; border-radius: 10px; }

/* PCでボタンを小さく */
@media (min-width: 641px) {
    [data-testid="stButton"] > button { max-width: 300px; }
}
</style>
""", unsafe_allow_html=True)

DEFAULT_CONFIG = [
    {
        "code": "1489",
        "name": "NF高配当株50",
        "stages": [
            {"ratio": 0.991, "shares": 1},
            {"ratio": 0.985, "shares": 2},
            {"ratio": 0.980, "shares": 3},
            {"ratio": 0.975, "shares": 5},
        ]
    },
    {
        "code": "1476",
        "name": "ISコアJリート",
        "stages": [
            {"ratio": 0.995, "shares": 1},
            {"ratio": 0.990, "shares": 1},
            {"ratio": 0.985, "shares": 2},
            {"ratio": 0.980, "shares": 3},
        ]
    },
    {
        "code": "2638",
        "name": "GXロボ&AI",
        "stages": [
            {"ratio": 0.980, "shares": 1},
            {"ratio": 0.975, "shares": 1},
            {"ratio": 0.965, "shares": 2},
            {"ratio": 0.935, "shares": 6},
        ]
    },
    {
        "code": "435A",
        "name": "日本株配当ローテーション",
        "stages": [
            {"ratio": 0.995, "shares": 1},
            {"ratio": 0.985, "shares": 1},
            {"ratio": 0.975, "shares": 3},
            {"ratio": 0.965, "shares": 3},
        ]
    },
]

def load_config_from_params():
    params = st.query_params
    if "cfg" in params:
        try:
            decoded = base64.urlsafe_b64decode(params["cfg"] + "==").decode("utf-8")
            return json.loads(decoded)
        except Exception:
            pass
    return None

def encode_config(config):
    raw = json.dumps(config, ensure_ascii=False)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

def make_card(etf, price_data):
    code = etf["code"]
    if price_data and price_data.get("price"):
        price = price_data["price"]
        date = price_data["date"]
        stages_html = ""
        for i, stage in enumerate(etf["stages"]):
            limit = math.floor(price * stage["ratio"])
            stages_html += (
                f'<div class="stage-cell">'
                f'<div class="stage-label">第{i+1}段　{stage["shares"]}株</div>'
                f'<div class="stage-price">¥{limit:,}</div>'
                f'<div class="stage-sub">×{stage["ratio"]:.3f}</div>'
                f'</div>'
            )
        return (
            f'<div class="etf-card">'
            f'<div class="etf-title">{code}　{etf["name"]}</div>'
            f'<div class="etf-close">終値 ¥{price:,.0f}　{date}</div>'
            f'<div class="stage-grid">{stages_html}</div>'
            f'</div>'
        )
    else:
        return (
            f'<div class="etf-card">'
            f'<div class="etf-title">{code}　{etf["name"]}</div>'
            f'<div class="etf-close">↑「株価を取得・更新」を押してください</div>'
            f'</div>'
        )

if "config" not in st.session_state:
    loaded = load_config_from_params()
    st.session_state.config = loaded if loaded else DEFAULT_CONFIG

if "prices" not in st.session_state:
    st.session_state.prices = {}

def fetch_prices():
    results = {}
    for etf in st.session_state.config:
        try:
            ticker = yf.Ticker(f"{etf['code']}.T")
            hist = ticker.history(period="3d", auto_adjust=False)
            if not hist.empty:
                close = float(hist["Close"].iloc[-1])
                date = str(hist.index[-1].date())
                results[etf["code"]] = {"price": close, "date": date}
            else:
                results[etf["code"]] = None
        except Exception:
            results[etf["code"]] = None
    st.session_state.prices = results

tab_main, tab_settings = st.tabs(["📈 指値確認", "⚙️ 設定"])

with tab_main:
    if st.button("🔄　株価を取得・更新", type="primary"):
        with st.spinner("取得中..."):
            fetch_prices()

    cfg = st.session_state.config
    prices = st.session_state.prices

    # 4銘柄を2列×2行のグリッドで表示
    cards_html = '<div class="etf-grid">'
    for etf in cfg:
        cards_html += make_card(etf, prices.get(etf["code"]))
    cards_html += '</div>'

    st.markdown(cards_html, unsafe_allow_html=True)

with tab_settings:
    st.caption("変更後「保存してURLを生成」→ 表示されたURLをブックマーク登録。次回そのURLを開けば設定が引き継がれます。")
    st.markdown("---")
    new_config = []

    for idx, etf in enumerate(st.session_state.config):
        with st.expander(f"銘柄 {idx+1}：{etf['code']}　{etf['name']}", expanded=True):
            col_code, col_name = st.columns([1, 2])
            code = col_code.text_input("証券コード", value=etf["code"], key=f"code_{idx}")
            name = col_name.text_input("銘柄名", value=etf["name"], key=f"name_{idx}")
            stages = []
            for s_idx, stage in enumerate(etf["stages"]):
                c1, c2 = st.columns(2)
                ratio = c1.number_input(
                    f"第{s_idx+1}段　割合",
                    value=float(stage["ratio"]),
                    min_value=0.800, max_value=1.000, step=0.001, format="%.3f",
                    key=f"ratio_{idx}_{s_idx}"
                )
                shares = c2.number_input(
                    "株数", value=int(stage["shares"]), min_value=1, step=1,
                    key=f"shares_{idx}_{s_idx}"
                )
                stages.append({"ratio": round(ratio, 3), "shares": int(shares)})
            new_config.append({"code": code, "name": name, "stages": stages})

    st.markdown("---")
    if st.button("💾　保存してURLを生成", use_container_width=True, type="primary"):
        st.session_state.config = new_config
        st.session_state.prices = {}
        encoded = encode_config(new_config)
        base_url = "https://etf-sashine-hq5l6fj7skdh7tuftpp4l2.streamlit.app"
        full_url = f"{base_url}/?cfg={encoded}"
        st.success("✅ 保存しました！下のURLをブックマーク登録してください。")
        st.code(full_url, language=None)
