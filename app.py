import streamlit as st
import yfinance as yf
import math

st.set_page_config(
    page_title="指値計算",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── スマホ向けCSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    /* 更新ボタンを大きく */
    [data-testid="stButton"] > button {
        font-size: 1.1rem;
        height: 3.2rem;
    }
    /* 段階ヘッダー */
    .stage-header {
        font-size: 0.8rem;
        color: #888;
        margin-bottom: 2px;
    }
    /* 指値金額を大きく */
    .limit-price {
        font-size: 1.4rem;
        font-weight: bold;
        color: #4fc3f7;
    }
    /* 終値 */
    .close-price {
        font-size: 1.0rem;
        color: #aaa;
    }
</style>
""", unsafe_allow_html=True)

# ── デフォルト設定（ここを書き換えてもOK） ────────────────────────
DEFAULT_CONFIG = [
    {
        "code": "1489",
        "name": "NF日本高配当株",
        "stages": [
            {"ratio": 0.991, "shares": 1},
            {"ratio": 0.985, "shares": 3},
            {"ratio": 0.975, "shares": 5},
            {"ratio": 0.965, "shares": 10},
        ]
    },
    {
        "code": "1478",
        "name": "銘柄B（変更してください）",
        "stages": [
            {"ratio": 0.995, "shares": 1},
            {"ratio": 0.990, "shares": 2},
            {"ratio": 0.980, "shares": 4},
            {"ratio": 0.970, "shares": 8},
        ]
    },
    {
        "code": "2513",
        "name": "銘柄C（変更してください）",
        "stages": [
            {"ratio": 0.995, "shares": 1},
            {"ratio": 0.990, "shares": 2},
            {"ratio": 0.980, "shares": 4},
            {"ratio": 0.970, "shares": 8},
        ]
    },
]

# ── セッション初期化 ──────────────────────────────────────────────
if "config" not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG
if "prices" not in st.session_state:
    st.session_state.prices = {}


# ── 株価取得関数 ──────────────────────────────────────────────────
def fetch_prices():
    results = {}
    for etf in st.session_state.config:
        try:
            ticker = yf.Ticker(f"{etf['code']}.T")
            hist = ticker.history(period="3d")
            if not hist.empty:
                close = float(hist["Close"].iloc[-1])
                date = str(hist.index[-1].date())
                results[etf["code"]] = {"price": close, "date": date}
            else:
                results[etf["code"]] = None
        except Exception:
            results[etf["code"]] = None
    st.session_state.prices = results


# ── タブ構成 ─────────────────────────────────────────────────────
tab_main, tab_settings = st.tabs(["📈 指値確認", "⚙️ 設定"])


# ════════════════════════════════════════════════════════════════
#  メインタブ
# ════════════════════════════════════════════════════════════════
with tab_main:
    st.title("指値計算")

    if st.button("🔄　株価を取得・更新", use_container_width=True, type="primary"):
        with st.spinner("取得中..."):
            fetch_prices()

    st.markdown("---")

    for etf in st.session_state.config:
        code = etf["code"]
        price_data = st.session_state.prices.get(code)

        st.subheader(f"{code}　{etf['name']}")

        if price_data and price_data.get("price"):
            price = price_data["price"]
            date = price_data["date"]

            st.markdown(
                f'<span class="close-price">終値 ¥{price:,.0f}　（{date}）</span>',
                unsafe_allow_html=True
            )

            # 4段階の指値を表示
            cols_header = st.columns([1, 3, 2, 2])
            cols_header[0].markdown('<span class="stage-header">段階</span>', unsafe_allow_html=True)
            cols_header[1].markdown('<span class="stage-header">指値（円）</span>', unsafe_allow_html=True)
            cols_header[2].markdown('<span class="stage-header">割合</span>', unsafe_allow_html=True)
            cols_header[3].markdown('<span class="stage-header">株数</span>', unsafe_allow_html=True)

            for i, stage in enumerate(etf["stages"]):
                limit = math.floor(price * stage["ratio"])  # 切り捨て
                cols = st.columns([1, 3, 2, 2])
                cols[0].write(f"第{i+1}")
                cols[1].markdown(
                    f'<span class="limit-price">¥{limit:,}</span>',
                    unsafe_allow_html=True
                )
                cols[2].write(f"×{stage['ratio']:.3f}")
                cols[3].write(f"{stage['shares']}株")

        else:
            st.caption("↑「株価を取得・更新」を押してください")

        st.markdown("---")


# ════════════════════════════════════════════════════════════════
#  設定タブ
# ════════════════════════════════════════════════════════════════
with tab_settings:
    st.title("設定")
    st.caption("銘柄コード・銘柄名・割合・株数を自由に変更できます。変更後は「保存」を押してください。")
    st.markdown("---")

    new_config = []

    for idx, etf in enumerate(st.session_state.config):
        with st.expander(f"銘柄 {idx + 1}：{etf['code']}　{etf['name']}", expanded=False):
            col_code, col_name = st.columns([1, 2])
            code = col_code.text_input("証券コード", value=etf["code"], key=f"code_{idx}")
            name = col_name.text_input("銘柄名", value=etf["name"], key=f"name_{idx}")

            stages = []
            st.markdown("**段階別 割合 / 株数**")
            for s_idx, stage in enumerate(etf["stages"]):
                c1, c2 = st.columns(2)
                ratio = c1.number_input(
                    f"第{s_idx + 1}段　割合",
                    value=float(stage["ratio"]),
                    min_value=0.800,
                    max_value=1.000,
                    step=0.001,
                    format="%.3f",
                    key=f"ratio_{idx}_{s_idx}"
                )
                shares = c2.number_input(
                    f"株数",
                    value=int(stage["shares"]),
                    min_value=1,
                    step=1,
                    key=f"shares_{idx}_{s_idx}"
                )
                stages.append({"ratio": round(ratio, 3), "shares": int(shares)})

            new_config.append({"code": code, "name": name, "stages": stages})

    st.markdown("---")
    if st.button("💾　設定を保存", use_container_width=True, type="primary"):
        st.session_state.config = new_config
        st.session_state.prices = {}  # 銘柄変わったら価格リセット
        st.success("✅ 保存しました！「指値確認」タブで更新してください。")
