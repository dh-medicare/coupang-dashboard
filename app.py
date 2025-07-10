import streamlit as st
import pandas as pd
import os
import glob
import plotly.graph_objects as go

# ✅ GitHub 기준 상대경로로 수정
DATA_DIR = "data"

def load_data(directory):
    files = glob.glob(os.path.join(directory, "*_집계버전.csv"))
    all_data = []
    for file in files:
        df = pd.read_csv(file)
        all_data.append(df)
    if all_data:
        full_df = pd.concat(all_data)
        full_df['날짜'] = pd.to_datetime(full_df['날짜'])
        full_df['구매전환율'] = full_df['구매전환율'].astype(str).str.replace('%', '').astype(float)
        return full_df
    return pd.DataFrame()

st.set_page_config(page_title="일별 데이터 분석 대시보드", layout="wide")
st.title("📊 일별 상품별 데이터 분석 대시보드")

df = load_data(DATA_DIR)
if df.empty:
    st.warning("❗ 집계 데이터가 없습니다. 먼저 create_summary.py를 실행해주세요.")
    st.stop()

df = df.sort_values('날짜')

# 🔔 알림 시스템 개선
def generate_alerts(df, product):
    alerts = []
    prod_df = df[df['통일상품명'] == product].sort_values('날짜', ascending=False)
    if prod_df.empty or len(prod_df) < 2:
        return alerts

    recent = prod_df.head(7).copy()
    today = recent.iloc[0]
    avg = recent.iloc[1:].mean(numeric_only=True)

    for col in ['매출', '주문', '판매량', '방문자', '조회', '장바구니', '총 매출', '총 판매수', '총 취소 금액', '총 취소된 상품수', '구매전환율']:
        today_val = today.get(col, None)
        avg_val = avg.get(col, None)
        if pd.isna(today_val) or pd.isna(avg_val):
            continue

        diff = today_val - avg_val
        if today_val == 0:
            alerts.append(f"⚠️ **{col}**: 0 (📉 평균 {avg_val:.1f})")
        elif diff < 0:
            alerts.append(f"❗ **{col}**: {today_val:.1f} (📉 {abs(diff):.1f})")
        elif diff > 0:
            alerts.append(f"✅ **{col}**: {today_val:.1f} (📈 {diff:.1f})")
    return alerts

# ✅ 우선순위 정렬 및 컬러 매핑
priority = ['아이씰6p', '아이씰12p', '노비어', '리필', 'DH리프팅', '닥터코링+', '턱밴드', '신방스']
product_sales = df.groupby('통일상품명')['매출'].sum().sort_values(ascending=False)
df['우선순위'] = df['통일상품명'].apply(lambda x: priority.index(x) if x in priority else 999)
df['매출총합'] = df['통일상품명'].map(product_sales)
df = df.sort_values(by=['우선순위', '매출총합'], ascending=[True, False])
product_order = df['통일상품명'].drop_duplicates().tolist()

color_map = {
    '아이씰6p': '#e3f2fd', '아이씰12p': '#e3f2fd',
    '노비어': '#fff9c4', '리필': '#fff9c4',
    'DH리프팅': '#fbeaf1', '닥터코링+': '#b2dfdb',
    '턱밴드': '#b2dfdb', '신방스': '#f0f4c3'
}
metrics = ['매출', '주문', '판매량', '방문자', '조회', '장바구니', '총 매출', '총 판매수', '총 취소 금액', '총 취소된 상품수', '구매전환율']
color_seq = ['#ff6b6b', '#4ecdc4', '#ffa600', '#6a89cc', '#f78fb3', '#38ada9', '#f8c291']

# 🗂 탭 구성
tab1, tab2 = st.tabs(["📋 날짜별 상품 표 보기", "📊 상품별 일자 비교 그래프"])

# 📋 날짜별 표 보기
with tab1:
    st.subheader("📋 날짜별 상품 테이블")
    all_dates = df['날짜'].dt.strftime('%Y-%m-%d').unique().tolist()
    selected_date = st.selectbox("📅 날짜 선택", all_dates, index=len(all_dates)-1)
    table_df = df[df['날짜'].dt.strftime('%Y-%m-%d') == selected_date]
    st.dataframe(table_df.reset_index(drop=True))

# 📊 상품별 그래프
with tab2:
    for product in product_order:
        product_df = df[df['통일상품명'] == product].copy()
        product_df['날짜'] = pd.to_datetime(product_df['날짜'])
        product_df = product_df.sort_values('날짜')
        bg_color = color_map.get(product, "#ffffff")

        st.markdown(f"<h3 style='font-weight:bold; margin-bottom:10px'>{product}</h3>", unsafe_allow_html=True)

        col_left, col_right = st.columns([5, 2])
        with col_right:
            available_dates = product_df['날짜'].dt.strftime('%Y-%m-%d').unique().tolist()
            selected_dates = st.multiselect("📅 날짜 선택", available_dates, default=available_dates[-7:], key=f"{product}_dates")
            selected_metrics = st.multiselect("📌 지표 선택", metrics, default=['매출', '구매전환율'], key=f"{product}_metrics")

            # 📍 알림 박스 (스크롤 포함)
            alerts = generate_alerts(df, product)
            st.markdown(
                f"""
                <div style="border:1px solid #ddd; border-radius:8px; padding:10px; margin-top:10px;
                            max-height:230px; overflow-y:auto; background-color:#FFFAFA	;">
                    {"".join(f"<div style='margin-bottom:6px;'>{a}</div>" for a in alerts)}
                </div>
                """, unsafe_allow_html=True
            )

        if not selected_dates:
            continue

        plot_df = product_df[product_df['날짜'].dt.strftime('%Y-%m-%d').isin(selected_dates)].copy()
        plot_df['날짜'] = plot_df['날짜'].dt.strftime('%Y-%m-%d')
        fig = go.Figure()

        if '매출' in selected_metrics:
            fig.add_trace(go.Bar(
                x=plot_df['날짜'], y=plot_df['매출'], name='매출',
                marker_color='lightskyblue', width=0.4, yaxis='y'
            ))
            selected_metrics.remove('매출')

        for i, metric in enumerate(selected_metrics):
            fig.add_trace(go.Scatter(
                x=plot_df['날짜'], y=plot_df[metric],
                name=metric, mode='lines+markers',
                marker=dict(color=color_seq[i % len(color_seq)]),
                line=dict(width=3), yaxis='y2'
            ))

        fig.update_layout(
            plot_bgcolor=bg_color,
            paper_bgcolor=bg_color,
            xaxis=dict(title="날짜", type='category'),
            yaxis=dict(title="매출", side='left'),
            yaxis2=dict(title="기타 지표", overlaying='y', side='right', showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            height=450,
            margin=dict(t=30, b=40)
        )

        with col_left:
            st.plotly_chart(fig, use_container_width=True)
