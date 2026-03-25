import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="3部隊バックテスト", page_icon="🕸️", layout="wide")

st.title("🕸️ 3部隊バックテストダッシュボード")
st.caption("陣形A（1489）・陣形B（2638）・陣形C（1476）の網トラップ戦略シミュレーター")

# ============================================================
# 📅 期間設定
# ============================================================
st.subheader("📅 バックテスト期間")
col_s, col_e = st.columns(2)
with col_s:
    start_date = st.text_input("開始日", value="2019-01-01", placeholder="YYYY-MM-DD")
with col_e:
    end_date = st.text_input("終了日", value="2023-12-31", placeholder="YYYY-MM-DD")

st.divider()

# ============================================================
# 🛠️ 陣形設定UI
# ============================================================
def formation_ui(label, emoji, default_ticker, default_k, default_v, default_budget):
    st.markdown(f"**{emoji} {label}**")
    ticker = st.text_input("銘柄コード", value=default_ticker, key=f"ticker_{label}")
    budget = st.number_input("年間予算（円）", value=default_budget, step=10000, key=f"budget_{label}")
    c1, c2 = st.columns(2)
    with c1:
        k1 = st.number_input("網1 レート", value=default_k[0], step=0.001, format="%.3f", key=f"k1_{label}")
        k2 = st.number_input("網2 レート", value=default_k[1], step=0.001, format="%.3f", key=f"k2_{label}")
        k3 = st.number_input("網3 レート", value=default_k[2], step=0.001, format="%.3f", key=f"k3_{label}")
        k4 = st.number_input("網4 レート", value=default_k[3], step=0.001, format="%.3f", key=f"k4_{label}")
    with c2:
        v1 = st.number_input("網1 株数", value=default_v[0], step=1, key=f"v1_{label}")
        v2 = st.number_input("網2 株数", value=default_v[1], step=1, key=f"v2_{label}")
        v3 = st.number_input("網3 株数", value=default_v[2], step=1, key=f"v3_{label}")
        v4 = st.number_input("網4 株数", value=default_v[3], step=1, key=f"v4_{label}")
    return ticker, budget, k1, v1, k2, v2, k3, v3, k4, v4

col_a, col_b, col_c = st.columns(3)
with col_a:
    vars_a = formation_ui("陣形 A", "🛡️", "1489.T",
                          [0.991, 0.985, 0.980, 0.975], [1, 3, 3, 5], 500000)
with col_b:
    vars_b = formation_ui("陣形 B", "⚔️", "2638.T",
                          [0.980, 0.975, 0.965, 0.935], [1, 1, 4, 10], 300000)
with col_c:
    vars_c = formation_ui("陣形 C", "🏢", "1476.T",
                          [0.990, 0.980, 0.960, 0.940], [1, 2, 4, 8], 200000)

st.divider()

# ============================================================
# 🚀 シミュレーション関数
# ============================================================
def run_simulation(name, emoji, vars_tuple, sd, ed):
    meigara, annual_budget, k1, v1, k2, v2, k3, v3, k4, v4 = vars_tuple

    if not meigara:
        return

    with st.spinner(f"{emoji} {name} データ取得中..."):
        try:
            df = yf.download(meigara, start=sd, end=ed, progress=False)
        except Exception as e:
            st.error(f"{name}: データ取得エラー - {e}")
            return

    if df.empty:
        st.error(f"{name}: {meigara} のデータが取得できませんでした")
        return

    start_date_actual = df.index[0].strftime('%Y/%m/%d')
    end_date_actual   = df.index[-1].strftime('%Y/%m/%d')

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

    # --- 画面表示 ---
    st.markdown(f"#### {emoji} {name} ― `{meigara}`")
    st.caption(f"📅 {start_date_actual} 〜 {end_date_actual}　｜　期間末終値: **{current_price:,.0f}円**")

    st.markdown(
        f"🛒 **{net_kabu}株** 取得　｜　"
        f"💰 投資総額: **{net_cost:,.0f}円**　｜　"
        f"⚖️ 平均単価: **{net_avg:,.1f}円**　｜　"
        f"✨ 損益: **{net_prof:,.0f}円**（{pct_sign}{net_pct:.1f}%）"
        + (f"　｜　⚠️ スキップ: {skip_count}回" if skip_count > 0 else "")
    )
    st.markdown(
        f"🎣 ヒット数 ― 網1: **{h1}**回　網2: **{h2}**回　網3: **{h3}**回　網4: **{h4}**回"
    )

    # 年別サマリーテーブル（網ごとヒット数付き）
    rows = []
    for y, s in sorted(yearly_stats.items()):
        if s['cost'] > 0:
            util = (s['cost'] / annual_budget) * 100 if annual_budget > 0 else 0
            fire = "🔥" if util >= 90 else ""
            rows.append({
                "年":         y,
                "投資額（円）": f"{s['cost']:,.0f}",
                "株数":        s['kabu'],
                "網1":         s['h1'],
                "網2":         s['h2'],
                "網3":         s['h3'],
                "網4":         s['h4'],
                "消化率":      f"{util:.1f}% {fire}"
            })
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

    # --- 各陣形の結果直下にコピペ用テキストボックス ---
    lines = []
    lines.append(f"【{name} / {meigara}】{start_date_actual}〜{end_date_actual} 末値{current_price:,.0f}円")
    lines.append(f"網レート: {k1}/{k2}/{k3}/{k4}　株数: {v1}/{v2}/{v3}/{v4}　予算: {annual_budget:,.0f}円/年")
    lines.append(f"取得株数: {net_kabu}株　投資総額: {net_cost:,.0f}円　平均単価: {net_avg:,.1f}円")
    lines.append(f"評価額: {net_val:,.0f}円　損益: {net_prof:,.0f}円（{pct_sign}{net_pct:.1f}%）")
    lines.append(f"ヒット数: 網1={h1}回 / 網2={h2}回 / 網3={h3}回 / 網4={h4}回")
    if skip_count > 0:
        lines.append(f"予算枯渇スキップ: {skip_count}回")
    lines.append("年別:")
    for y, s in sorted(yearly_stats.items()):
        if s['cost'] > 0:
            util = (s['cost'] / annual_budget) * 100 if annual_budget > 0 else 0
            fire = "🔥" if util >= 90 else ""
            lines.append(
                f"  {y}: {s['cost']:,.0f}円/{s['kabu']}株/消化率{util:.1f}%{fire}"
                f" | 網1={s['h1']} 網2={s['h2']} 網3={s['h3']} 網4={s['h4']}"
            )

    st.text_area(
        label="📋 AIチャット投げ込み用（Ctrl+A → Ctrl+C）",
        value="\n".join(lines),
        height=180,
        key=f"copy_{name}"
    )


# ============================================================
# 🚀 実行ボタン
# ============================================================
if st.button("🚀 3部隊一斉シミュレーション実行！", type="primary", use_container_width=True):
    st.divider()
    for label, emoji, vars_tuple in [
        ("陣形 A", "🛡️", vars_a),
        ("陣形 B", "⚔️", vars_b),
        ("陣形 C", "🏢", vars_c),
    ]:
        run_simulation(label, emoji, vars_tuple, start_date, end_date)
        st.divider()
