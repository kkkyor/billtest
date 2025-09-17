import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 페이지 기본 설정 ---
# st.set_page_config는 스크립트에서 가장 먼저 호출되어야 합니다.
st.set_page_config(
    page_title="영업사원 수수료 현황",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 함수 정의 ---
@st.cache_data(ttl=600) # 10분마다 데이터 새로고침
def load_data_from_google_sheet():
    """
    Streamlit의 secrets를 사용하여 구글 서비스 계정으로 인증하고,
    지정된 구글 시트의 데이터를 읽어와 Pandas DataFrame으로 변환합니다.
    """
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인")

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
    
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("오류: 스프레드시트를 찾을 수 없습니다.")
        st.info("1. URL이 올바른지 확인해주세요.\n2. 서비스 계정 이메일이 해당 시트에 '뷰어' 이상으로 공유되었는지 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.info("`.streamlit/secrets.toml` 파일이 올바르게 설정되었는지 확인해주세요.")
        return None

# --- UI 구성 ---
st.title("👨‍💼 영업사원별 수수료 현황 조회 (편집 가능)")
st.markdown("---")

# 데이터 로드
df = load_data_from_google_sheet()

if df is not None:
    if '영업자' in df.columns:
        salespeople = sorted(df['영업자'].dropna().unique())

        with st.sidebar:
            st.header("🔍 검색 옵션")
            selected_salesperson = st.selectbox(
                "영업자 이름을 선택하세요:",
                options=[""] + salespeople,
                index=0
            )
            st.info("조회하고 싶은 영업자의 이름을 목록에서 선택하세요.")

        st.header("📋 조회 결과")

        if selected_salesperson:
            result_df = df[df['영업자'] == selected_salesperson].copy() # 편집을 위해 .copy() 사용
            
            if not result_df.empty:
                st.success(f"**'{selected_salesperson}'** 님의 수수료 현황입니다. (총 {len(result_df)} 건)")
                
                # 데이터 편집기(data_editor) 사용
                edited_df = st.data_editor(
                    result_df,
                    # 특정 열의 속성을 설정
                    column_config={
                        "수수료율입력": st.column_config.NumberColumn("수수료율 입력", required=True),
                        "수수료금액입력": st.column_config.NumberColumn("수수료금액 입력", required=True),
                        "전화번호": st.column_config.TextColumn("전화번호", required=True),
                        "전기차보조금": st.column_config.NumberColumn("전기차보조금", required=True)
                    },
                    num_rows="dynamic", # 행 추가/삭제 기능 활성화
                    key=f"editor_{selected_salesperson}" # 영업사원 변경 시 편집기 초기화
                )

                st.info("표의 셀을 더블클릭하여 내용을 직접 수정할 수 있습니다.")

                # (선택) 수정된 내용을 확인하거나 다른 작업 수행
                # if st.button("수정 내용 저장하기"):
                #     st.write("수정된 데이터:")
                #     st.dataframe(edited_df)
                #     # 여기에 수정된 데이터를 구글 시트에 다시 쓰는 로직을 추가할 수 있습니다.
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열(Column P)을 찾을 수 없습니다. 구글 시트의 열 이름이 올바른지 확인해주세요.")
