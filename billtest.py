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
        return worksheet, df # 워크시트 객체와 데이터프레임을 함께 반환
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
            # 선택된 영업사원의 데이터만 필터링 (수정을 위해 원본 인덱스 유지)
            result_df = df[df['영업자'] == selected_salesperson].copy()
            
            if not result_df.empty:
                # 📢 1. 개선된 강조 방식: 경고 메시지
                st.warning("아래 표에서 ✍️ 표시가 된 항목들은 **필수 입력 항목**입니다. 내용을 수정하거나 입력해주세요.")

                # 데이터 편집기
                edited_df = st.data_editor(
                    result_df,
                    column_config={
                        # 📢 2. 개선된 강조 방식: 컬럼 제목에 이모지 추가
                        "수수료율입력": st.column_config.NumberColumn("✍️ 수수료율", required=True),
                        "수수료금액입력": st.column_config.NumberColumn("✍️ 수수료금액", required=True),
                        "전화번호": st.column_config.TextColumn("✍️ 전화번호", required=True),
                        "전기차보조금": st.column_config.NumberColumn("✍️ 전기차보조금", required=True)
                    },
                    num_rows="dynamic",
                    key=f"editor_{selected_salesperson}"
                )

                st.markdown("---")
                
                # 💾 3. 구글 시트 저장 기능
                if st.button("💾 변경사항 구글 시트에 저장하기", type="primary"):
                    with st.spinner("저장 중... 잠시만 기다려주세요."):
                        # 원본 데이터프레임(df)에서 수정된 부분만 업데이트
                        # edited_df의 인덱스는 df의 인덱스와 동일하므로 update 함수 사용 가능
                        df.update(edited_df)
                        
                        # 구글 시트 업데이트
                        if update_google_sheet(worksheet, df):
                            st.success("🎉 성공적으로 구글 시트에 저장되었습니다!")
                            # 캐시를 지워 데이터를 새로고침
                            st.cache_data.clear()
                            # st.experimental_rerun() # 필요 시 즉시 새로고침
                        else:
                            st.error("저장에 실패했습니다. 다시 시도해주세요.")
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열을 찾을 수 없습니다. 구글 시트의 열 이름을 확인해주세요.")
