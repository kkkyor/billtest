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

# --- 구글 시트 연결 및 데이터 로드 ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    """
    gspread 클라이언트 객체를 생성하고 캐시합니다.
    (최종 수정) gspread.Client()에 Credentials 객체를 직접 전달합니다.
    """
    # 1. google-auth 라이브러리를 사용하여 자격 증명(Credentials) 객체 생성
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

    # 2. gspread.authorize() 대신, 생성한 자격 증명(creds)을 직접 주입하여 클라이언트 초기화
    #    이렇게 하면 gspread가 내부적으로 올바른 인증 세션을 생성하여 사용합니다.
    client = gspread.Client(auth=creds)
    
    return client

@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    """구글 시트에서 데이터를 로드하고 실제 시트의 행 번호를 포함한 DataFrame으로 변환합니다."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        # ❗ 변경점 1: 실제 시트의 행 번호를 추적하기 위한 열 추가 (헤더가 1행이므로 데이터는 2행부터 시작)
        df['sheet_row_number'] = range(2, len(df) + 2)
        return worksheet, df
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None, None
        
def update_rows_in_sheet(edited_df):
    """
    (신규) google-api-python-client를 사용하여 수정된 행을 구글 시트에 업데이트합니다.
    """
    try:
        # 1. 자격 증명 및 API 클라이언트 서비스 빌드
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://www.googleapis.com/auth/spreadsheets'] # 쓰기 권한 스코프
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)

        spreadsheet_id = "1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo" # 스프레드시트 ID
        sheet_name = "온라인" # 시트 이름

        # 2. 업데이트 요청 데이터(data) 구성
        data = []
        for index, row in edited_df.iterrows():
            row_number = int(row['sheet_row_number'])
            
            # DataFrame의 모든 값을 문자열로 변환 (API 오류 방지)
            values = [str(val) for val in row.drop('sheet_row_number').values]
            
            data.append({
                'range': f"{sheet_name}!A{row_number}", # '온라인'!A2 와 같은 형식
                'values': [values]
            })

        # 3. API 요청 본문(body) 구성
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }

        # 4. spreadsheets.values.batchUpdate API 호출
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()
        
        st.write(result) # 디버깅용: API 호출 결과 확인
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
                        # ❗ 변경점 3: 사용자에게 보일 필요 없는 행 번호 열은 숨김 처리
                        "sheet_row_number": None, 
                        "수수료율입력": st.column_config.NumberColumn(
                            "✍️ 수수료율", help="수수료 **비율(%)**을 입력해주세요. 예: 3.5"
                        ),
                        "수수료금액입력": st.column_config.NumberColumn(
                            "✍️ 수수료금액", help="계산된 **수수료 총액**을 입력해주세요."
                        ),
                        "전화번호": st.column_config.TextColumn(
                            "✍️ 전화번호", help="고객의 연락처를 입력해주세요."
                        ),
                        "전기차보조금": st.column_config.NumberColumn(
                            "✍️ 전기차보조금", help="전기차 보조금이 있는 경우 **금액**을 입력해주세요."
                        )
                    },
                    num_rows="dynamic",
                    key=f"editor_{selected_salesperson}"
                )

                st.markdown("---")
                
                # ❗ 변경점 4: 새로운 업데이트 함수를 호출하도록 버튼 로직 수정
                if st.button("💾 변경사항 구글 시트에 저장하기", type="primary"):
                    with st.spinner("저장 중..."):
                        # Pandas의 `compare` 기능을 사용하여 실제로 변경된 행만 필터링
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
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열을 찾을 수 없습니다. 구글 시트의 열 이름을 확인해주세요.")
