import streamlit as st
import yfinance as yf
import pandas as pd
import json

st.set_page_config(page_title="3部隊バックテスト", page_icon="🕸️", layout="wide")

st.title("🕸️ 3部隊バックテストダッシュボード")
st.caption("陣形A・B・Cの網トラップ戦略シミュレーター")

# ============================================================
# 銘柄マスタ
# ============================================================
TICKER_OPTIONS = {
    "1489 – 日経高配当50":  "1489.T",
    "1476 – JリートETF":    "1476.T",
    "2080 – PBR1倍割れ":    "2080.T",
    "2638 – GXロボ＆AI":    "2638.T",
    "513A – GX防衛テック":  "513A.T",
}
TICKER_LABELS = list(TICKER_OPTIONS.keys())

def label_from_code(code):
    for lbl, cd in TICKER_OPTIONS.items():
        if cd == code:
            return lbl
    return TICKER_LABELS[0]

# ============================================================
# デフォルト設定
# ============================================================
DEFAULT_CONFIG = {
    "start_date": "2019-01-01",
    "end_date":   "2023-12-31",
    "A": {"ticker": "1489.T", "budget": 500000,
          "k": [0.991, 0.985, 0.980, 0.975], "v": [1, 3, 3, 5]},
    "B": {"ticker": "2638.T", "budget": 300000,
          "k": [0.980, 0.975, 0.965, 0.935], "v": [1, 1, 4, 10]},
    "C": {"ticker": "1476.T", "budget": 200000,
          "k": [0.990, 0.980, 0.960, 0.940], "v": [1, 2, 4, 8]},
}

# ============================================================
# セッション初期化
# ============================================================
if "cfg" not in st.session_state:
    st.session_state.cfg = DEFAULT_CONFIG.copy()

cfg = st.session_state.cfg

# ============================================================
# 設定の保存 / 読み込み
# ============================================================
with st.expander("💾 設定の保存・読み込み"):
    col_dl, col_ul = st.columns(2)

    with col_dl:
        st.markdown("**📤 現在の設定をダウンロード**")
        # 現在のUI値ではなくcfgをそのままシリアライズ
        st.download_button(
            label="設定をJSONで保存",
            data=json.dumps(cfg, ensure_ascii=False, indent=2),
            file_name="backtest_config.json",
            mime="application/json",
        )

    with col_ul:
        st.markdown("**📥 設定ファイルを読み込む**")
        uploaded = st.file_uploader("JSONファイルをアップロード", type="json", key="upload_cfg")
        if uploaded:
            try:
                loaded = json.load(uploaded)
                st.session_state.cfg = loaded
                st.success("設定を読み込みました！ページを再読み込みします...")
                st.rerun()
            except Exception as e:
                st.error(f"読み込みエラー: {e}")

st.divider()

# ============================================================
# 📅 期間設定
# ============================================================
st.subheader("📅 バックテスト期間")
col_s, col_e = st.columns(2)
with col_s:
    start_date = st.text_input("開始日", value=cfg["start_date"], placeholder="YYYY-MM-DD", key="start_date")
with col_e:
    end_date = st.text_input("終了日", value=cfg["end_date"], placeholder="YYYY-MM-DD", key="end_date")

# 期間変更をcfgに反映
cfg["start_date"] = start_date
cfg["end_date"]   = end_date

st.divider()

# ============================================================
# 🛠️ 陣形設定UI
# ============================================================
def formation_ui(label, emoji, formation_key):
    fc = cfg[formation_key]
    st.markdown(f"**{emoji} 陣形 {formation_key}**")

    # 銘柄ドロップダウン
    current_label = label_from_code(fc["ticker"])
    selected_label = st.selectbox(
        "銘柄", TICKER_LABELS,
        index=TICKER_LABELS.index(current_label),
        key=f"ticker_{formation_key}"
    )
    fc["ticker"] = TICKER_OPTIONS[selected_label]

    fc["budget"] = st.number_input(
        "年間予算（円）", value=fc["budget"], step=10000, key=f"budget_{formation_key}"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**網レート**")
        fc["k"][0] = st.number_input("網1", value=fc["k"][0], step=0.001, format="%.3f", key=f"k1_{formation_key}")
        fc["k"][1] = st.number_input("網2", value=fc["k"][1], step=0.001, format="%.3f", key=f"k2_{formation_key}")
        fc["k"][2] = st.number_input("網3", value=fc["k"][2], step=0.001, format="%.3f", key=f"k3_{formation_key}")
        fc["k"][3] = st.number_input("網4", value=fc["k"][3], step=0.001, format="%.3f", key=f"k4_{formation_key}")
    with c2:
        st.markdown("**株数**")
        fc["v"][0] = st.number_input("網1", value=fc["v"][0], step=1, key=f"v1_{formation_key}")
        fc["v"][1] = st.number_input("網2", value=fc["v"][1], step=1, key=f"v2_{formation_key}")
        fc["v"][2] = st.number_input("網3", value=fc["v"][2], step=1, key=f"v3_{formation_key}")
        fc["v"][3] = st.number_input("網4", value=fc["v"][3], step=1, key=f"v4_{formation_key}")

    return fc["ticker"], fc["budget"], fc["k"][0], fc["v"][0], fc["k"][1], fc["v"][1], fc["k"][2], fc["v"][2], fc["k"][3], fc["v"][3]

col_a, col_b, col_c = st.columns(3)
with col_a:
    vars_a = formation_ui("陣形 A", "🛡️", "A")
with col_b:
    vars_b = formation_ui("陣形 B", "⚔️", "B")
with col_c:
    vars_c = formation_ui("陣形 C", "🏢", "C")

st.divider()

# ============================================================
# 🚀 シミュレーション関数
# ============================================================
def run_simulation(name, emoji, vars_tuple, sd, ed):
    meigara, annual_budget, k1, v1, k2, v2, k3, v3, k4, v4 = vars_tuple

    if not meigara:
        return None

    with st.spinner(f"{emoji} {name} データ取得中..."):
        try:
            df = yf.download(meigara, start=sd, end=ed, progress=False)
        except Exception as e:
            st.error(f"{name}: データ取得エラー - {e}")
            return None

    if df.empty:
        st.error(f"{name}: {meigara} のデータが取得できませんでした")
        return None

    start_actual = df.index[0].strftime('%Y/%m/%d')
    end_actual   = df.index[-1].strftime('%Y/%m/%d')

    def get_val(series, idx):
        val = series.iloc[idx]
        return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)

    current_price = get_val(df['Close'], -1)
    initial_price = get_val(df['Close'], 0)

    remaining_budget = annual_budget
    net_kabu, net_cost = 0, 0
    h1, h2, h3, h4 = 0, 0, 0, 0
    f2, f3, f4 = False, False, False
    skip_count = 0
    weekly_base = initial_price
    yearly_stats = {}

    for i in range(len(df) - 1):
        t_date  = df.index[i]
        tm_date = df.index[i + 1]
        tm_year  = tm_date.strftime('%Y')
        tm_month = tm_date.strftime('%m')

        if tm_year not in yearly_stats:
            yearly_stats[tm_year] = {
                'cost': 0, 'kabu': 0,
                'h1': 0, 'h2': 0, 'h3': 0, 'h4': 0,
                'skip': 0,
                'months': {}
            }
            remaining_budget = annual_budget

        if tm_month not in yearly_stats[tm_year]['months']:
            yearly_stats[tm_year]['months'][tm_month] = {'cost': 0, 'kabu': 0}

        t_close = get_val(df['Close'], i)
        tm_low  = get_val(df['Low'],   i + 1)

        l1 = t_close * k1
        l2, l3, l4 = weekly_base * k2, weekly_base * k3, weekly_base * k4

        def process_trap(target_price, shares, hit_count, trap_num, flag=None):
            nonlocal remaining_budget, net_kabu, net_cost, yearly_stats, skip_count
            cost = target_price * shares
            if remaining_budget >= cost:
                remaining_budget -= cost
                net_kabu += shares
                net_cost += cost
                yearly_stats[tm_year]['cost'] += cost
                yearly_stats[tm_year]['kabu'] += shares
                yearly_stats[tm_year][f'h{trap_num}'] += 1
                yearly_stats[tm_year]['months'][tm_month]['cost'] += cost
                yearly_stats[tm_year]['months'][tm_month]['kabu'] += shares
                return hit_count + 1, True if flag is not None else None
            else:
                skip_count += 1
                yearly_stats[tm_year]['skip'] += 1
                return hit_count, flag

        if tm_low <= l1:
            h1, _ = process_trap(l1, v1, h1, 1)
        if tm_low <= l2 and not f2:
            h2, f2 = process_trap(l2, v2, h2, 2, f2)
        if tm_low <= l3 and not f3:
            h3, f3 = process_trap(l3, v3, h3, 3, f3)
        if tm_low <= l4 and not f4:
            h4, f4 = process_trap(l4, v4, h4, 4, f4)

        if t_date.isocalendar().week != tm_date.isocalendar().week:
            weekly_base = t_close
            f2, f3, f4 = False, False, False

    # --- 集計 ---
    net_val  = net_kabu * current_price
    net_prof = net_val - net_cost
    net_avg  = net_cost / net_kabu if net_kabu > 0 else 0
    net_pct  = (net_prof / net_cost) * 100 if net_cost > 0 else 0
    pct_sign = "+" if net_pct >= 0 else ""

    num_years = len([y for y, s in yearly_stats.items() if s['cost'] > 0])
    avg_skip  = skip_count / num_years if num_years > 0 else 0

    # --- 画面表示 ---
    st.markdown(f"#### {emoji} {name} ― `{meigara}`")
    st.caption(f"📅 {start_actual} 〜 {end_actual}　｜　期間末終値: **{current_price:,.0f}円**")

    skip_str = f"　｜　⚠️ スキップ平均: {avg_skip:.1f}回/年" if skip_count > 0 else ""
    st.markdown(
        f"🛒 **{net_kabu}株** 取得　｜　"
        f"💰 投資総額: **{net_cost:,.0f}円**　｜　"
        f"⚖️ 平均単価: **{net_avg:,.1f}円**　｜　"
        f"✨ 損益: **{net_prof:,.0f}円**（{pct_sign}{net_pct:.1f}%）"
        + skip_str
    )
    st.markdown(
        f"🎣 ヒット数合計 ― 網1: **{h1}**回　網2: **{h2}**回　網3: **{h3}**回　網4: **{h4}**回"
    )

    # 年別サマリーテーブル（網ごとヒット数＋スキップ数）
    rows = []
    for y, s in sorted(yearly_stats.items()):
        if s['cost'] > 0:
            util = (s['cost'] / annual_budget) * 100 if annual_budget > 0 else 0
            fire = "🔥" if util >= 90 else ""
            row = {
                "年":         y,
                "投資額（円）": f"{s['cost']:,.0f}",
                "株数":        s['kabu'],
                "網1":         s['h1'],
                "網2":         s['h2'],
                "網3":         s['h3'],
                "網4":         s['h4'],
                "消化率":      f"{util:.1f}% {fire}",
            }
            if skip_count > 0:
                row["スキップ"] = s['skip']
            rows.append(row)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("月別詳細"):
        month_rows = []
        for y, s in sorted(yearly_stats.items()):
            for m, ms in sorted(s['months'].items()):
                if ms['cost'] > 0:
                    util = (ms['cost'] / annual_budget) * 100 if annual_budget > 0 else 0
                    fire = "🔥" if util >= 30 else ""
                    month_rows.append({
                        "年月":        f"{y}/{m}",
                        "投資額（円）": f"{ms['cost']:,.0f}",
                        "株数":        ms['kabu'],
                        "消化率":      f"{util:.1f}% {fire}"
                    })
        if month_rows:
            st.dataframe(pd.DataFrame(month_rows), use_container_width=True, hide_index=True)

    # --- コピペ用テキスト生成（まとめ用に返す） ---
    lines = []
    lines.append(f"【{name} / {meigara}】{start_actual}〜{end_actual} 末値{current_price:,.0f}円")
    lines.append(f"網レート: {k1}/{k2}/{k3}/{k4}　株数: {v1}/{v2}/{v3}/{v4}　予算: {annual_budget:,.0f}円/年")
    lines.append(f"取得株数: {net_kabu}株　投資総額: {net_cost:,.0f}円　平均単価: {net_avg:,.1f}円")
    lines.append(f"評価額: {net_val:,.0f}円　損益: {net_prof:,.0f}円（{pct_sign}{net_pct:.1f}%）")
    lines.append(f"ヒット数: 網1={h1}回 / 網2={h2}回 / 網3={h3}回 / 網4={h4}回")
    if skip_count > 0:
        lines.append(f"予算枯渇スキップ: 合計{skip_count}回（平均{avg_skip:.1f}回/年）")
    lines.append("年別:")
    for y, s in sorted(yearly_stats.items()):
        if s['cost'] > 0:
            util = (s['cost'] / annual_budget) * 100 if annual_budget > 0 else 0
            fire = "🔥" if util >= 90 else ""
            skip_part = f" スキップ={s['skip']}回" if skip_count > 0 else ""
            lines.append(
                f"  {y}: {s['cost']:,.0f}円/{s['kabu']}株/消化率{util:.1f}%{fire}"
                f" | 網1={s['h1']} 網2={s['h2']} 網3={s['h3']} 網4={s['h4']}{skip_part}"
            )

    return "\n".join(lines)


# ============================================================
# 🚀 実行ボタン
# ============================================================
if st.button("🚀 3部隊一斉シミュレーション実行！", type="primary", use_container_width=True):
    st.divider()

    all_texts = []
    for label, emoji, vars_tuple in [
        ("陣形 A", "🛡️", vars_a),
        ("陣形 B", "⚔️", vars_b),
        ("陣形 C", "🏢", vars_c),
    ]:
        text = run_simulation(label, emoji, vars_tuple, start_date, end_date)
        if text:
            all_texts.append(text)
        st.divider()

    # 全陣形まとめてコピペ用テキストボックス
    if all_texts:
        combined = f"=== バックテスト結果（{start_date} 〜 {end_date}）===\n\n" + "\n\n".join(all_texts)
        st.subheader("📋 AIチャット投げ込み用テキスト（全陣形まとめ）")
        st.text_area(
            label="👇 全選択してコピー（Ctrl+A → Ctrl+C）",
            value=combined,
            height=300,
            key="copy_all"
        )
