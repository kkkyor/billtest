import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 함수 정의 ---
@st.cache_data(ttl=600) # 10분마다 데이터 새로고침
def load_data_from_google_sheet():
    """
    Streamlit의 secrets를 사용하여 구글 서비스 계정으로 인증하고,
    지정된 구글 시트의 데이터를 읽어와 Pandas DataFrame으로 변환합니다.
    """
    try:
        # Streamlit secrets에서 서비스 계정 정보 불러오기
        # secrets.toml 파일의 [gcp_service_account] 섹션을 참조
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        # 구글 시트 열기
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인") # '온라인' 시트 선택

        # 데이터를 Pandas DataFrame으로 변환
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
    
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("오류: 스프레드시트를 찾을 수 없습니다.")
        st.info("1. URL이 올바른지 확인해주세요.\n2. 서비스 계정 이메일이 해당 시트에 '뷰어' 이상으로 공유되었는지 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.info("`secrets.toml` 파일이 올바르게 설정되었는지 확인해주세요.")
        return None

# --- UI 구성 ---
st.set_page_config(page_title="영업사원 수수료 현황", layout="wide")

st.title("👨‍💼 영업사원별 수수료 현황 조회")
st.markdown("---")

# 데이터 로드
df = load_data_from_google_sheet()

if df is not None:
    # '영업자' (P열) 데이터가 있는지 확인
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
            result_df = df[df['영업자'] == selected_salesperson]
            
            if not result_df.empty:
                st.success(f"**'{selected_salesperson}'** 님의 수수료 현황입니다. (총 {len(result_df)} 건)")
                st.dataframe(result_df)
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열(Column P)을 찾을 수 없습니다. 구글 시트의 열 이름이 올바른지 확인해주세요.")
