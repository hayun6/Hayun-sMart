import uuid
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
import qrcode
import streamlit as st

st.set_page_config(page_title="장보기 알림메모", page_icon="🛒", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:650px;padding:0.65rem 0.7rem 1rem}
header[data-testid="stHeader"]{display:none}
[data-testid="stVerticalBlock"]{gap:0.35rem}
[data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:0.4rem}
[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
[data-testid="stForm"]{padding:0.45rem;border-radius:12px}
[data-testid="stWidgetLabel"] p{font-size:12px}
.stButton button,.stFormSubmitButton button{min-height:2rem;padding:0.15rem 0.4rem}
h3{padding:0.1rem 0;font-size:1.25rem!important}
[data-testid="stCaptionContainer"] p{font-size:11px}
</style>""", unsafe_allow_html=True)

CATEGORIES = ["🥬 야채", "🍎 과일", "🥩 육류", "🐟 수산", "🥛 유제품", "🍞 빵·곡류", "🥫 가공식품", "🧴 생활용품", "📦 기타"]
PRIORITIES = {1: "1 꼭 필요", 2: "2 가격 보고", 3: "3 저렴할 때"}
for key, default in [("items", []), ("cart", []), ("notice", "")]:
    if key not in st.session_state:
        st.session_state[key] = default


def money(value):
    return f"{value:,}원"


def notify(text):
    st.session_state["notice"] = text
    st.rerun()


st.markdown("### 🛒 장보기 알림메모")
total = sum(x["unit_price"] * x["quantity"] for x in st.session_state["cart"])
quantity_total = sum(x["quantity"] for x in st.session_state["cart"])
st.markdown(f"**카트 {money(total)}** · {quantity_total}개 담음 · 남은 메모 {len(st.session_state['items'])}건")
st.caption("1 꼭 필요 · 2 가격이 괜찮으면 · 3 저렴할 때만 / 가격 기준은 개당")
if st.session_state["notice"]:
    st.toast(st.session_state["notice"])
    st.session_state["notice"] = ""

with st.form("add", clear_on_submit=True):
    c1, c2 = st.columns([1, 2])
    category = c1.selectbox("분류", CATEGORIES, label_visibility="collapsed")
    name = c2.text_input("상품명", placeholder="상품명 (예: 방울토마토)", max_chars=60, label_visibility="collapsed")
    c1, c2, c3 = st.columns([1, 1.6, 1])
    priority = c1.selectbox("중요도", [1, 2, 3], format_func=lambda x: PRIORITIES[x], label_visibility="collapsed")
    target = c2.number_input("개당 희망 상한가 · 0=미설정", min_value=0, max_value=100000000, step=100, value=0)
    submitted = c3.form_submit_button("＋ 추가", use_container_width=True)
    if submitted:
        if not name.strip():
            st.warning("상품명을 입력해 주세요.")
        else:
            st.session_state["items"].append({"id": uuid.uuid4().hex, "name": name.strip(), "category": category, "priority": priority, "target": target})
            notify("장보기 메모에 추가했어요.")

items = sorted(st.session_state["items"], key=lambda x: x["priority"])
# A fixed-height list keeps long shopping lists inside a compact, single-page layout.
with st.container(height=135, border=True):
    if not items:
        st.caption("목록이 비었어요. 위에서 장볼 상품을 추가해 주세요.")
    for item in items:
        limit = f" · ≤{money(item['target'])}" if item["target"] else ""
        st.markdown(f"**{item['priority']} · {item['name']}** · {item['category']}{limit}")

if items:
    lookup = {x["id"]: x for x in items}
    selected_id = st.selectbox("처리할 상품", list(lookup), format_func=lambda k: f"{lookup[k]['priority']} · {lookup[k]['name']}", label_visibility="collapsed")
    selected = lookup[selected_id]
    with st.form("purchase", clear_on_submit=False):
        c1, c2 = st.columns(2)
        unit_price = c1.number_input("실제 단가(원)", min_value=0, max_value=100000000, value=0, step=100)
        quantity = c2.number_input("구매 수량", min_value=1, max_value=10000, value=1, step=1)
        st.caption("비싸면 ‘보류’하세요. 희망 상한가를 넘겨도 확인 후 구매할 수 있어요.")
        confirmed = st.checkbox("상한가 초과여도 구매", value=False)
        c1, c2 = st.columns(2)
        bought = c1.form_submit_button("🛒 카트에 담기", type="primary", use_container_width=True)
        skip = c2.form_submit_button("비싸서 보류", use_container_width=True)
        if bought:
            if selected["target"] and unit_price > selected["target"] and not confirmed:
                st.warning(f"희망 상한가 {money(selected['target'])} 초과입니다. 보류하거나 구매 확인에 체크해 주세요.")
            else:
                st.session_state["cart"].append({**selected, "unit_price": int(unit_price), "quantity": int(quantity), "purchased_at": datetime.now().isoformat(timespec="seconds")})
                st.session_state["items"] = [x for x in st.session_state["items"] if x["id"] != selected_id]
                notify(f"{selected['name']} {quantity}개 · {money(int(unit_price) * int(quantity))} 담았어요.")
        if skip:
            notify("구매하지 않고 메모에 남겨뒀어요. 다른 상품을 선택하세요.")

with st.expander(f"🧾 카트 내역 · {money(total)} / 구매 취소"):
    if st.session_state["cart"]:
        with st.container(height=150):
            for entry in st.session_state["cart"]:
                st.write(f"{entry['name']} · {money(entry['unit_price'])} × {entry['quantity']} = {money(entry['unit_price'] * entry['quantity'])}")
        cart_lookup = {x["id"]: x for x in st.session_state["cart"]}
        undo_id = st.selectbox("되돌릴 상품", list(cart_lookup), format_func=lambda k: cart_lookup[k]["name"])
        if st.button("구매 취소 → 메모로 복원", use_container_width=True):
            entry = cart_lookup[undo_id]
            st.session_state["items"].append({k: entry[k] for k in ["id", "name", "category", "priority", "target"]})
            st.session_state["cart"] = [x for x in st.session_state["cart"] if x["id"] != undo_id]
            notify("카트 금액을 취소하고 메모로 복원했어요.")
    else:
        st.caption("아직 카트에 담은 상품이 없어요.")

with st.expander("📱 QR로 앱 열기 · QR 다운로드"):
    st.caption("배포한 앱의 공개 HTTPS 주소를 입력하세요. QR은 앱 접속용이며, 현재 메모나 카트를 공유하지 않습니다.")
    app_url = st.text_input("배포된 앱 주소", placeholder="https://your-app.streamlit.app", key="public_app_url").strip()
    if app_url:
        parsed = urlparse(app_url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not hostname or hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
            st.warning("스마트폰에서 접속할 수 있는 공개 HTTPS 주소를 입력해 주세요.")
        else:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
            qr.add_data(app_url)
            try:
                qr.make(fit=True)
                image = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                png = buffer.getvalue()
                st.image(png, width=180)
                st.download_button("QR 이미지 다운로드", data=png, file_name="shopping_app_qr.png", mime="image/png")
                st.link_button("앱 주소 열기", app_url)
                st.caption("휴대폰 기본 카메라로 QR을 찍으면 이 주소로 이동합니다. 배포 주소가 바뀌면 QR도 다시 만들어 주세요.")
            except qrcode.exceptions.DataOverflowError:
                st.warning("주소가 너무 길어요. 짧은 앱 배포 주소를 입력해 주세요.")

st.caption("현재 접속 세션에만 저장됩니다. QR로 다른 기기에서 열면 별도 목록입니다. 새로고침·연결 종료 시 초기화될 수 있어요. 화면 크기·키보드에 따라 스크롤이 생길 수 있습니다.")

# GitHub / Streamlit Community Cloud deployment:
# 1. Upload app.py and requirements.txt to the same GitHub repository.
# 2. In Streamlit Community Cloud, create an app using that repository.
# 3. Set the main file path to app.py and deploy.
# Local run: python -m pip install -r requirements.txt
#            streamlit run app.py
# 4. Open the deployed app, expand the QR section, paste its public HTTPS URL.
# 5. Download the QR PNG and scan it with a phone camera to open the app.
# QR codes link to the app; they do not transfer session-specific shopping data.
# No API keys are required.
