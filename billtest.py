import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="영업사원 수수료 현황",
    page_icon="👨‍💼",
    layout="wide"
)

# --- 구글 시트 연결 및 데이터 로드 ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    """gspread 클라이언트 객체를 생성하고 캐시합니다."""
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    """구글 시트에서 데이터를 로드하고 DataFrame으로 변환합니다."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return worksheet, df
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None, None

def update_google_sheet(worksheet, df):
    """DataFrame의 내용으로 구글 시트 전체를 업데이트합니다."""
    try:
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        return True
    except Exception as e:
        st.error(f"시트 업데이트 중 오류 발생: {e}")
        return False

# --- UI 구성 ---
st.title("👨‍💼 영업사원별 수수료 현황 조회 및 편집")
st.markdown("---")

worksheet, df = load_data_from_google_sheet()

if df is not None:
    if '영업자' in df.columns:
        salespeople = sorted(df['영업자'].dropna().unique())

        with st.sidebar:
            st.header("🔍 검색 옵션")
            selected_salesperson = st.selectbox(
                "영업자 이름을 선택하세요:",
                options=[""] + salespeople,
                index=0,
                key="salesperson_selector"
            )
            st.info("조회할 영업자의 이름을 목록에서 선택하세요.")

        st.header(f"📋 '{selected_salesperson}' 님 데이터 편집")

        if selected_salesperson:
            result_df = df[df['영업자'] == selected_salesperson].copy()
            
            if not result_df.empty:
                st.info("✍️ 표시가 된 항목들은 **입력을 권장**하는 주요 항목입니다. 셀을 더블클릭하여 수정해주세요.")

                edited_df = st.data_editor(
                    result_df,
                    column_config={
                        # 'required'를 빼고 'help' 파라미터를 추가하여 강조
                        "수수료율입력": st.column_config.NumberColumn(
                            "✍️ 수수료율",
                            help="수수료 **비율(%)**을 입력해주세요. 예: 3.5"
                        ),
                        "수수료금액입력": st.column_config.NumberColumn(
                            "✍️ 수수료금액",
                            help="계산된 **수수료 총액**을 입력해주세요."
                        ),
                        "전화번호": st.column_config.TextColumn(
                            "✍️ 전화번호",
                            help="고객의 연락처를 입력해주세요."
                        ),
                        "전기차보조금": st.column_config.NumberColumn(
                            "✍️ 전기차보조금",
                            help="전기차 보조금이 있는 경우 **금액**을 입력해주세요."
                        )
                    },
                    num_rows="dynamic",
                    key=f"editor_{selected_salesperson}"
                )

                st.markdown("---")
                
                if st.button("💾 변경사항 구글 시트에 저장하기", type="primary"):
                    with st.spinner("저장 중..."):
                        df.update(edited_df)
                        if update_google_sheet(worksheet, df):
                            st.success("🎉 성공적으로 구글 시트에 저장되었습니다!")
                            st.cache_data.clear()
                            # st.experimental_rerun() # 주석 처리. 사용자가 원할 때 새로고침 하도록 유도
                        else:
                            st.error("저장에 실패했습니다.")
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열을 찾을 수 없습니다. 구글 시트의 열 이름을 확인해주세요.")
