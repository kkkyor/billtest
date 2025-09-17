import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="영업사원 수수료 현황",
    page_icon="👨‍💼",
    layout="wide"
)

# --- 구글 시트 연결 (기존과 동일) ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.Client(auth=creds)
    return client

@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df['sheet_row_number'] = range(2, len(df) + 2)
        return df
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None

# --- 구글 시트 업데이트 (기존과 동일) ---
def update_rows_in_sheet(edited_df):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet_id = "1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo"
        sheet_name = "온라인"
        
        # DataFrame의 헤더를 가져와 업데이트 순서 맞추기
        client = get_gspread_client()
        worksheet = client.open_by_url(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}").worksheet(sheet_name)
        headers = worksheet.row_values(1)

        data = []
        for index, row in edited_df.iterrows():
            row_number = int(row['sheet_row_number'])
            
            # 시트의 헤더 순서에 맞게 행 데이터 정렬 및 문자열 변환
            ordered_row_values = [str(row.get(h, '')) for h in headers]
            
            data.append({
                'range': f"{sheet_name}!A{row_number}",
                'values': [ordered_row_values]
            })
        
        body = {'valueInputOption': 'USER_ENTERED', 'data': data}
        service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        return True
    except Exception as e:
        st.error(f"시트 업데이트 중 오류 발생: {e}")
        return False

# --- 🎈 신규: 로그인 로직 ---
def check_login():
    """로그인 폼을 표시하고 입력된 정보를 검증합니다."""
    st.title("👨‍💼 수수료 현황 로그인")
    
    with st.form("login_form"):
        username = st.text_input("이름")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

        if submitted:
            # st.secrets에 저장된 user 정보와 비교
            if username in st.secrets.users and st.secrets.users[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun() # 로그인 성공 시 즉시 페이지 새로고침
            else:
                st.error("이름 또는 비밀번호가 정확하지 않습니다.")

# --- 메인 앱 로직 ---

# 1. 로그인 상태 확인: 로그인되지 않았으면 로그인 페이지 표시
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    check_login()

# 2. 로그인 성공 시 메인 앱 표시
else:
    # --- UI 구성 ---

    # ✅ 기존 st.title... 부분을 아래 코드로 교체하세요

    # --- 헤더 UI 구성 ---
    col1, col2 = st.columns([0.8, 0.2])  # 화면을 8:2 비율로 분할
    
    with col1:
        st.title("👨‍💼 수수료 현황 조회 및 편집")
        st.markdown(f"**{st.session_state.username}** 님, 환영합니다.")
    
    with col2:
        st.write("") # 버튼을 수직으로 가운데 정렬하기 위한 빈 공간
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    
    st.markdown("---") # 헤더와 본문을 나누는 선

    df = load_data_from_google_sheet()

    if df is not None:
        if '영업자' in df.columns:
            
            selected_salesperson = st.session_state.username # 로그인한 사용자의 이름 사용
            st.header(f"📋 '{selected_salesperson}' 님 데이터 편집")
            
            result_df = df[df['영업자'] == selected_salesperson].copy()
            
            if not result_df.empty:
                st.info("✍️ 표시가 된 항목들은 **입력을 권장**하는 주요 항목입니다. 셀을 더블클릭하여 수정해주세요.")

                edited_df = st.data_editor(
                    result_df,
                    column_config={
                        "sheet_row_number": None,
                        "수수료율입력": st.column_config.NumberColumn("✍️ 수수료율", help="수수료 **비율(%)**을 입력해주세요. 예: 3.5"),
                        "수수료금액입력": st.column_config.NumberColumn("✍️ 수수료금액", help="계산된 **수수료 총액**을 입력해주세요."),
                        "전화번호": st.column_config.TextColumn("✍️ 전화번호", help="고객의 연락처를 입력해주세요."),
                        "전기차보조금": st.column_config.NumberColumn("✍️ 전기차보조금", help="전기차 보조금이 있는 경우 **금액**을 입력해주세요.")
                    },
                    num_rows="dynamic",
                    key=f"editor_{selected_salesperson}"
                )

                st.markdown("---")
                
                if st.button("💾 변경사항 구글 시트에 저장하기", type="primary"):
                    with st.spinner("저장 중..."):
                        changes = result_df.compare(edited_df)
                        if not changes.empty:
                            changed_indices = changes.index
                            rows_to_update = edited_df.loc[changed_indices]
                            
                            if update_rows_in_sheet(rows_to_update):
                                st.success("🎉 성공적으로 구글 시트에 저장되었습니다!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("저장에 실패했습니다.")
                        else:
                            st.info("변경된 내용이 없습니다.")
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다. 구글 시트의 '영업자' 이름을 확인해주세요.")
        else:
            st.error("'영업자' 열을 찾을 수 없습니다. 구글 시트의 열 이름을 확인해주세요.")
