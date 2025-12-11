import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. ส่วนจัดการ Config & Log =================
def load_config(filename='config.ini'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def debug_dump_ui(window):
    log("!!! หาไม่เจอ -> กำลังลิสต์ ID (Debug) !!!")
    try:
        visible_items = []
        for child in window.descendants():
            if child.is_visible():
                aid = child.element_info.automation_id
                if aid: visible_items.append(f"ID: {aid}")
        log(f"Items: {list(set(visible_items))[:10]}...")
    except: pass

# ================= 2. ฟังก์ชันช่วยเหลือ =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        window.set_focus()
        rect = window.rectangle()
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.2)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.8)
    except: pass

def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text().strip():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.3)
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    log(f"...ค้นหา '{criteria}' (Scroll)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found = child
                    break
        except: pass

        if found:
            try:
                elem_rect = found.rectangle()
                win_rect = window.rectangle()
                if elem_rect.bottom >= win_rect.bottom - 70:
                    force_scroll_down(window, -3)
                    time.sleep(0.5)
                    continue 
                found.click_input()
                log(f"   [/] เจอและกด '{criteria}' สำเร็จ")
                return True
            except: pass
        
        if i < max_scrolls:
            force_scroll_down(window, scroll_dist)
    return False

def click_element_by_id(window, exact_id, timeout=5, index=0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if len(found) > index:
                found[index].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except: pass
        time.sleep(0.5)
    return False

def click_element_by_fuzzy_id(window, keyword, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                aid = child.element_info.automation_id
                if child.is_visible() and aid and keyword in aid:
                    child.click_input()
                    log(f"[/] เจอ Fuzzy ID: '{aid}' -> กดสำเร็จ")
                    return True
        except: pass
        time.sleep(0.5)
    return False

def wait_until_id_appears(window, exact_id, timeout=10):
    log(f"...รอโหลด ID: {exact_id}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible():
                    return True
        except: pass
        time.sleep(1)
    return False

def wait_for_text(window, text, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

# ================= 3. ฟังก์ชัน Input =================
def smart_input_weight(window, value):
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window):
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def process_sender_info_popup(window, phone, postal):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input()
                        edit.type_keys(str(postal), with_spaces=True)
                    break 
        except: pass
        
        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input()
                        edit.type_keys(str(phone), with_spaces=True)
                        found_phone = True
                        break
            except: pass
            if found_phone: break
            force_scroll_down(window, -5)
        smart_next(window)

def handle_prohibited_items(window):
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}")
                    return
        except: pass
        time.sleep(0.5)

# --- ฟังก์ชันใหม่ (New Steps) ---

def process_special_services(window, services_str):
    log("--- หน้า: บริการพิเศษ ---")
    if wait_for_text(window, "บริการพิเศษ", timeout=5):
        if services_str.strip():
            for s in services_str.split(','):
                if s: smart_click(window, s.strip())
    smart_next(window)

def process_sender_info_page(window):
    log("--- หน้า: ข้อมูลผู้ส่ง (ข้าม) ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    smart_next(window)

def process_receiver_address_selection(window, address_keyword):
    """กรอกคำค้นหา และเลือกที่อยู่รายการแรก"""
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        time.sleep(1)
        # 1. กรอกคำค้นหา
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    edit.click_input()
                    edit.type_keys(str(address_keyword), with_spaces=True)
                    filled = True
                    break
            if not filled and len(edits) > 1:
                edits[1].click_input()
                edits[1].type_keys(str(address_keyword), with_spaces=True)
        except: pass
        
        # 2. รอรายการเด้งขึ้นมา แล้วเลือกอันแรก
        log("...รอกล่องรายการที่อยู่...")
        time.sleep(2) # รอโหลดรายการ
        try:
            # หา ListItem ตัวแรกที่มองเห็น
            list_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible()]
            if list_items:
                log(f"[/] เจอรายการ {len(list_items)} รายการ -> เลือกอันแรก")
                list_items[0].click_input()
            else:
                log("[!] ไม่เจอรายการที่อยู่ -> ข้ามการเลือก")
        except: pass
        
        # 3. หลังจากเลือกแล้ว มันมักจะเด้งไปหน้าถัดไปเอง หรือต้องกดถัดไป
        # แต่ใน Flow ปกติ ถ้าเลือกจาก List มันจะไปหน้า Detail เลย
        time.sleep(1)

def process_receiver_details_form(window, fname, lname, phone):
    """หน้า: กรอกรายละเอียดผู้รับ (ชื่อ, นามสกุล, เบอร์)"""
    log("--- หน้า: รายละเอียดผู้รับ ---")
    # รอให้แน่ใจว่าอยู่หน้านี้
    if not wait_for_text(window, "คำนำหน้า", timeout=5):
        log("[WARN] อาจจะยังไม่เข้าหน้ากรอกรายละเอียด")

    time.sleep(1)
    try:
        # กรอกชื่อ (FirstName)
        edits = window.descendants(control_type="Edit")
        # เดาว่าช่องแรกๆ คือ ชื่อ/นามสกุล
        # ปกติ: [0]=คำนำหน้า(ถ้ามี), [1]=ชื่อ, [2]=กลาง, [3]=นามสกุล
        # ลองหาจาก AutomationID หรือ Label ถ้าทำได้ แต่ถ้าไม่มีใช้ Index
        
        # กลยุทธ์: หา Edit ที่ว่างอยู่
        empty_edits = [e for e in edits if e.is_visible()] # เอาทั้งหมดก่อน
        
        # พยายามใส่ชื่อ (ช่องที่ 2 หรือหาที่มีคำว่า Name)
        # สมมติช่องแรกเป็นคำนำหน้า ข้ามไป
        if len(empty_edits) >= 2:
            log(f"...กรอกชื่อ: {fname}")
            empty_edits[0].click_input() # ลองช่องแรกก่อน (บางทีไม่มีคำนำหน้าแบบ Textbox)
            empty_edits[0].type_keys(fname, with_spaces=True)
            
            log(f"...กรอกนามสกุล: {lname}")
            # ช่องถัดไป หรือช่องที่ 3
            # ถ้ามีช่องกลาง (Middle Name) อาจจะเป็น index 2
            # ลองกด Tab ไปเรื่อยๆ หรือใช้ Index
            empty_edits[0].type_keys("{TAB}") # ไปช่องกลาง
            empty_edits[0].type_keys("{TAB}") # ไปช่องนามสกุล
            window.type_keys(lname, with_spaces=True)
        
        # เลื่อนลงหาเบอร์โทร
        log("...เลื่อนหาเบอร์โทร...")
        force_scroll_down(window, -10)
        
        # หาช่องที่มีคำว่า 'โทร' หรือช่องท้ายๆ
        found_phone = False
        for _ in range(3):
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "โทร" in edit.element_info.name or "Phone" in edit.element_info.automation_id:
                    log(f"...กรอกเบอร์: {phone}")
                    edit.click_input()
                    edit.type_keys(phone, with_spaces=True)
                    found_phone = True
                    break
            if found_phone: break
            force_scroll_down(window, -5)
            
        if not found_phone:
            log("[!] หาช่องเบอร์ไม่เจอ -> ลองกด Tab ไปเรื่อยๆ แล้วพิมพ์")
            window.type_keys("{TAB}"*3)
            window.type_keys(phone, with_spaces=True)

    except Exception as e:
        log(f"[!] Error กรอกรายละเอียด: {e}")

    smart_next(window)

def process_receipt_info(window):
    """หน้า: คำแนะนำใบเสร็จ (กด Enter 2 ครั้ง)"""
    log("--- หน้า: คำแนะนำใบเสร็จ ---")
    wait_for_text(window, "ใบเสร็จ", timeout=5)
    log("...กด Enter x2...")
    window.type_keys("{ENTER}")
    time.sleep(0.5)
    window.type_keys("{ENTER}")
    time.sleep(1)

def process_repeat_transaction(window, should_repeat):
    """หน้า: ทำรายการซ้ำ (ใช่/ไม่)"""
    log("--- หน้า: ทำรายการซ้ำ ---")
    if wait_for_text(window, "ทำรายการซ้ำ", timeout=5) or wait_for_text(window, "ซ้ำ", timeout=2):
        target = "ใช่" if should_repeat.lower() in ['true', 'yes', 'on'] else "ไม่"
        log(f"...เลือก: {target}...")
        
        # ลองหาปุ่มที่มีคำว่า ใช่/ไม่
        if not smart_click(window, target):
            # Fallback: ใช้ลูกศรซ้ายขวาเลือก (ปกติ "ใช่" คือ Default หรืออยู่ขวา?)
            # ถ้าเลือก "ไม่" ลองกด ESC หรือลูกศร
            if target == "ไม่":
                window.type_keys("{LEFT}{ENTER}")
            else:
                window.type_keys("{ENTER}")
    else:
        log("[WARN] ไม่พบหน้าทำรายการซ้ำ")

# ================= 4. Workflow หลัก =================
def run_smart_scenario(main_window, config):
    try:
        # Config เดิม
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        
        # Config ใหม่
        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        
        rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', 'A')
        rcv_lname = config['RECEIVER_DETAILS'].get('LastName', 'B')
        rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '081')
        
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
        
    except: 
        log("[Error] อ่าน Config ไม่สำเร็จ")
        return

    log(f"--- เริ่มต้นการทำงาน ---")
    time.sleep(0.5)

    # 1-7 ขั้นตอนเดิม (รับฝาก -> ผู้ส่ง -> ซอง -> ของต้องห้าม -> น้ำหนัก -> ปลายทาง -> Popup)
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    process_sender_info_popup(main_window, phone, postal) 
    time.sleep(step_delay)
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): return
    time.sleep(step_delay)
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)
    handle_prohibited_items(main_window)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    time.sleep(1)
    try: main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ")
                found = True; break
        if found: break
        time.sleep(0.5)

    # 8-10 เลือก EMS & ประกัน
    log("...รอหน้าบริการหลัก...")
    wait_until_id_appears(main_window, "ShippingService_EMSServices", timeout=10)
    if not click_element_by_id(main_window, "ShippingService_EMSServices"):
        if not click_element_by_fuzzy_id(main_window, "EMSS"): return

    time.sleep(step_delay) 
    inner_ems_id = "ShippingService_2572" 
    if not click_element_by_id(main_window, inner_ems_id):
        click_element_by_fuzzy_id(main_window, "ShippingService")
    time.sleep(1)

    if add_insurance_flag.lower() in ['true', 'yes']:
        log(f"...ใส่วงเงิน {insurance_amt}...")
        if click_element_by_id(main_window, "CoverageButton"):
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
                for child in main_window.descendants():
                    if child.element_info.automation_id == "CoverageAmount":
                        child.click_input(); child.type_keys(str(insurance_amt), with_spaces=True); break
                time.sleep(0.5)
                submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
                submits.sort(key=lambda x: x.rectangle().top)
                if submits: submits[0].click_input()
                else: main_window.type_keys("{ENTER}")
    
    time.sleep(1)
    smart_next(main_window) # ออกจากหน้าบริการ
    time.sleep(step_delay)

    # --- 11. หน้าบริการพิเศษ ---
    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    # --- 12. หน้าข้อมูลผู้ส่ง (ข้าม) ---
    process_sender_info_page(main_window)
    time.sleep(step_delay)

    # --- 13. หน้าข้อมูลผู้รับ (เลือกรายการ + กรอกรายละเอียด) ---
    # 13.1 ค้นหาและเลือกรายการบนสุด
    process_receiver_address_selection(main_window, addr_keyword)
    time.sleep(step_delay)
    
    # 13.2 กรอกชื่อ-นามสกุล-เบอร์ (หน้าถัดมา)
    process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone)
    time.sleep(step_delay)

    # --- 14. หน้าคำแนะนำใบเสร็จ (Enter x2) ---
    process_receipt_info(main_window)
    time.sleep(step_delay)

    # --- 15. หน้าทำรายการซ้ำ ---
    process_repeat_transaction(main_window, repeat_flag)

    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

# ================= 5. เริ่มต้นโปรแกรม =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=wait)
            
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS หรือยัง")
    
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")