import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# 데이터가 저장된 GitHub CSV 압축 파일 주소
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "simjiyong1207/content/main/population_ts_yearly_gender.zip"
)

# 따뜻하고 편안한 색상
COLOR_MALE = "#6488B8"
COLOR_FEMALE = "#D98276"
COLOR_BACKGROUND = "#FFF9F2"
COLOR_TEXT = "#51463F"

# 나이 라벨을 반드시 0세부터 100세 이상까지 순서대로 생성
AGE_LABELS = [f"{age}세" for age in range(100)] + ["100세 이상"]

# 성별 인구 컬럼 이름
MALE_COLUMNS = [f"남_{age}" for age in AGE_LABELS]
FEMALE_COLUMNS = [f"여_{age}" for age in AGE_LABELS]
POPULATION_COLUMNS = MALE_COLUMNS + FEMALE_COLUMNS


# --------------------------------------------------
# 2. 데이터 불러오기
# --------------------------------------------------
@st.cache_data(show_spinner="최신 인구 데이터를 불러오는 중입니다...")
def load_data():
    # pandas가 ZIP 압축 파일을 직접 읽도록 설정합니다.
    df = pd.read_csv(
        DATA_URL,
        compression="zip",
        low_memory=False,
    )

    # 컬럼명 앞뒤에 공백이 있으면 제거합니다.
    df.columns = df.columns.astype(str).str.strip()

    # 지역 및 연도 컬럼이 있는지 확인합니다.
    required_columns = ["연도", "시도", "시군구", "동"]
    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"필수 컬럼을 찾을 수 없습니다: {missing_columns}"
        )

    # 0세부터 100세 이상까지 남녀 인구 컬럼을 확인합니다.
    missing_population_columns = [
        col for col in POPULATION_COLUMNS if col not in df.columns
    ]

    if missing_population_columns:
        raise ValueError(
            "인구 컬럼을 찾을 수 없습니다. "
            f"누락된 컬럼 예시: {missing_population_columns[:10]}"
        )

    # 연도에 숫자 이외의 문자가 포함되어도 연도 숫자를 추출합니다.
    # 예: '2026년' -> 2026
    df["_연도숫자"] = pd.to_numeric(
        df["연도"].astype(str).str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    # 연도를 읽을 수 없는 행은 제외합니다.
    df = df.dropna(subset=["_연도숫자"]).copy()

    if df.empty:
        raise ValueError("유효한 연도 데이터가 없습니다.")

    # 데이터에 실제로 존재하는 가장 최신 연도만 선택합니다.
    latest_year = int(df["_연도숫자"].max())
    df = df[df["_연도숫자"] == latest_year].copy()

    # 지역명이 비어 있으면 드롭다운에서 혼란을 주지 않도록 제외합니다.
    for col in required_columns[1:]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[
        (df["시도"] != "")
        & (df["시군구"] != "")
        & (df["동"] != "")
    ].copy()

    # 인구 데이터에 쉼표가 들어 있어도 숫자로 변환할 수 있도록 처리합니다.
    # 숫자로 변환할 수 없는 값과 결측값은 0으로 처리합니다.
    for col in POPULATION_COLUMNS:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ).fillna(0)

        # 인구는 음수가 될 수 없으므로 음수 값은 0으로 처리합니다.
        df[col] = df[col].clip(lower=0)

    return df, latest_year


# --------------------------------------------------
# 3. 화면 제목과 안내
# --------------------------------------------------
st.markdown(
    """
    <div style="
        background-color: #F6E8D8;
        padding: 24px 28px;
        border-radius: 16px;
        margin-bottom: 18px;
    ">
        <h1 style="color: #51463F; margin: 0;">
            🏘️ 동네별 인구 피라미드
        </h1>
        <p style="
            color: #76675B;
            font-size: 16px;
            margin: 10px 0 0 0;
        ">
            우리 동네의 연령별 인구를 남녀별로 살펴보세요.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "남성은 왼쪽, 여성은 오른쪽에 표시합니다. "
    "막대 위에 마우스를 올리면 인구수를 확인할 수 있습니다."
)


# --------------------------------------------------
# 4. 데이터 로딩 및 오류 처리
# --------------------------------------------------
try:
    df, latest_year = load_data()

except Exception as e:
    st.error(
        "인구 데이터를 불러오지 못했습니다. "
        "인터넷 연결, 데이터 주소, CSV 컬럼명을 확인해 주세요."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("선택할 수 있는 지역 데이터가 없습니다.")
    st.stop()

st.success(f"현재 표시 중인 데이터 기준 연도: {latest_year}년")


# --------------------------------------------------
# 5. 시도 -> 시군구 -> 동 드롭다운
# --------------------------------------------------
st.subheader("📍 지역 선택")

# 첫 번째 드롭다운: 시도
sido_options = sorted(df["시도"].unique().tolist())

selected_sido = st.selectbox(
    "① 시도",
    options=sido_options,
    key="selected_sido",
)

# 선택한 시도에 속하는 시군구만 남깁니다.
sido_df = df[df["시도"] == selected_sido]
sigungu_options = sorted(sido_df["시군구"].unique().tolist())

# 두 번째 드롭다운: 시군구
selected_sigungu = st.selectbox(
    "② 시군구",
    options=sigungu_options,
    key="selected_sigungu",
)

# 선택한 시도와 시군구에 속하는 동만 남깁니다.
sigungu_df = sido_df[
    sido_df["시군구"] == selected_sigungu
]
dong_options = sorted(sigungu_df["동"].unique().tolist())

# 세 번째 드롭다운: 동
selected_dong = st.selectbox(
    "③ 동",
    options=dong_options,
    key="selected_dong",
)


# --------------------------------------------------
# 6. 선택한 동네의 인구 데이터 준비
# --------------------------------------------------
selected_df = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]

if selected_df.empty:
    st.warning("선택한 지역의 인구 데이터를 찾을 수 없습니다.")
    st.stop()

# 같은 지역에 여러 행이 있으면 나이별 인구를 합산합니다.
# 나이 컬럼의 순서는 위에서 만든 AGE_LABELS를 그대로 사용합니다.
population = selected_df[POPULATION_COLUMNS].sum()

male_population = [
    int(population[col]) for col in MALE_COLUMNS
]
female_population = [
    int(population[col]) for col in FEMALE_COLUMNS
]

# 남성은 왼쪽에 나타나도록 음수로 변환합니다.
male_values = [-value for value in male_population]

# 여성은 양수 그대로 오른쪽에 나타나도록 합니다.
female_values = female_population


# --------------------------------------------------
# 7. 요약 정보
# --------------------------------------------------
total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female

st.markdown("---")
st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_dong} "
    f"인구 피라미드"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("전체 인구", f"{total_population:,}명")

with col2:
    st.metric("남성 인구", f"{total_male:,}명")

with col3:
    st.metric("여성 인구", f"{total_female:,}명")


# --------------------------------------------------
# 8. Plotly 가로 막대그래프 만들기
# --------------------------------------------------
fig = go.Figure()

# 남성 막대: 음수이므로 중앙의 0을 기준으로 왼쪽에 표시됩니다.
fig.add_trace(
    go.Bar(
        name="남성",
        y=AGE_LABELS,
        x=male_values,
        orientation="h",
        marker=dict(
            color=COLOR_MALE,
            line=dict(width=0),
        ),
        customdata=male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
    )
)

# 여성 막대: 양수이므로 중앙의 0을 기준으로 오른쪽에 표시됩니다.
fig.add_trace(
    go.Bar(
        name="여성",
        y=AGE_LABELS,
        x=female_values,
        orientation="h",
        marker=dict(
            color=COLOR_FEMALE,
            line=dict(width=0),
        ),
        customdata=female_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
    )
)

# 좌우 막대가 나이별로 중앙에서 펼쳐지도록 설정합니다.
fig.update_layout(
    title=dict(
        text=f"{latest_year}년 연령별 남녀 인구",
        x=0.5,
        xanchor="center",
        font=dict(size=20, color=COLOR_TEXT),
    ),
    barmode="overlay",
    bargap=0.12,
    height=1150,
    plot_bgcolor=COLOR_BACKGROUND,
    paper_bgcolor=COLOR_BACKGROUND,
    font=dict(
        family="Arial, sans-serif",
        size=12,
        color=COLOR_TEXT,
    ),
    margin=dict(l=75, r=45, t=85, b=65),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="center",
        x=0.5,
        font=dict(size=13),
    ),
    hovermode="closest",
)

# 핵심: 나이 라벨의 순서를 직접 지정합니다.
# categoryorder='array'는 값의 크기나 알파벳 순으로 정렬하지 않습니다.
# categoryarray에 지정한 순서대로 범주를 배치합니다.
# Y축을 뒤집는 autorange='reversed'는 사용하지 않습니다.
fig.update_yaxes(
    title_text="나이",
    type="category",
    categoryorder="array",
    categoryarray=AGE_LABELS,
    tickmode="array",
    tickvals=AGE_LABELS,
    ticktext=AGE_LABELS,
    showgrid=False,
    ticks="outside",
    ticklen=4,
    automargin=True,
)

# X축은 대칭으로 설정하고, 왼쪽 숫자도 양수로 읽히게 표시합니다.
max_population = max(
    max(male_population, default=0),
    max(female_population, default=0),
)

# 인구가 모두 0인 경우에도 그래프가 정상적으로 표시되게 합니다.
axis_max = max(1, math.ceil(max_population / 100) * 100)

# 눈금은 좌우 대칭으로 만들고 중복되는 값은 제거합니다.
tickvals = sorted(
    set(
        [
            -axis_max,
            -axis_max / 2,
            0,
            axis_max / 2,
            axis_max,
        ]
    )
)

# 왼쪽 남성 인구의 음수 부호는 감추고 실제 인구수로 읽게 합니다.
ticktext = [f"{abs(value):,.0f}" for value in tickvals]

fig.update_xaxes(
    title_text="인구수 (명)",
    range=[-axis_max * 1.08, axis_max * 1.08],
    tickmode="array",
    tickvals=tickvals,
    ticktext=ticktext,
    zeroline=True,
    zerolinewidth=2,
    zerolinecolor="#B8A89A",
    showgrid=True,
    gridcolor="#E9DED2",
    gridwidth=1,
)


# --------------------------------------------------
# 9. 그래프 표시 및 나이 축 순서 확인
# --------------------------------------------------
st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "동네별_인구_피라미드",
            "scale": 2,
        },
    },
)

# 축에 지정된 순서를 코드에서도 확인합니다.
# 첫 번째 범주는 맨 아래, 마지막 범주는 맨 위에 위치해야 합니다.
if (
    list(fig.layout.yaxis.categoryarray) == AGE_LABELS
    and AGE_LABELS[0] == "0세"
    and AGE_LABELS[-1] == "100세 이상"
):
    st.caption(
        "✅ 나이 축 순서 확인 완료: "
        "맨 아래 0세 → 맨 위 100세 이상"
    )
else:
    st.error("나이 축 순서를 확인해 주세요.")


# --------------------------------------------------
# 10. 연령별 상세 데이터
# --------------------------------------------------
with st.expander("📋 연령별 인구 데이터 보기"):
    detail_df = pd.DataFrame(
        {
            "나이": AGE_LABELS,
            "남성 인구": male_population,
            "여성 인구": female_population,
            "전체 인구": [
                male + female
                for male, female in zip(
                    male_population,
                    female_population,
                )
            ],
        }
    )

    st.dataframe(
        detail_df,
        hide_index=True,
        use_container_width=True,
    )

    # 선택한 동네의 결과를 CSV로 내려받을 수 있습니다.
    csv_data = detail_df.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        label="연령별 인구 CSV 다운로드",
        data=csv_data,
        file_name=(
            f"{selected_sido}_{selected_sigungu}_{selected_dong}_"
            f"{latest_year}_인구.csv"
        ),
        mime="text/csv",
    )

st.caption(
    "데이터 출처: 제공된 GitHub 인구 데이터. "
    "표시 연도는 데이터에 실제로 존재하는 가장 최신 연도입니다."
)
