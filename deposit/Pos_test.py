import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
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

# ================= 2. Helper Functions (Core Tools) =================

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    """(สำคัญ) ใช้สำหรับกรอกข้อมูล: จำนวนเงิน, รหัส ปณ., ชื่อผู้รับ"""
    try:
        if not value or str(value).strip() == "": return False
        target_elem = None
        for child in window.descendants():
            if not child.is_visible(): continue
            aid = child.element_info.automation_id
            name = child.element_info.name
            
            # 1. เช็คจากชื่อ (Name)
            if target_name and name and target_name in name:
                target_elem = child; break
            # 2. เช็คจาก ID
            if target_id_keyword and aid and target_id_keyword in aid:
                target_elem = child; break
        
        if target_elem:
            try:
                edits = target_elem.descendants(control_type="Edit")
                if edits: target_elem = edits[0]
            except: pass
            target_elem.set_focus()
            target_elem.click_input()
            target_elem.type_keys(str(value), with_spaces=True)
            return True
        else:
            log(f"[WARN] หาช่อง '{target_name}' ไม่เจอ")
            return False
    except Exception as e:
        log(f"[!] Error find_and_fill: {e}")
        return False

def click_scroll_arrow_smart(window, direction='right', repeat=5):
    """ใช้ช่วยเลื่อนหน้าจอในฟังก์ชัน Rotate Logic"""
    try:
        target_group = [c for c in window.descendants() if c.element_info.automation_id == "ShippingServiceList"]
        if target_group: target_group[0].set_focus()
        else: window.set_focus()
        
        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        window.type_keys(key_code * repeat, pause=0.2, set_foreground=False)
        return True
    except: return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    """(สำคัญ) ใช้หาปุ่มบริการ 'ธนาณัติธรรมดา' ที่อาจหลบอยู่"""
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False
        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            if rect.right < safe_limit:
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else: should_scroll = True
        else: should_scroll = True
        
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5): window.type_keys("{RIGHT}")
            time.sleep(1.0)
    log(f"[X] หาปุ่มไม่เจอ: {target_id}")
    return False

def force_scroll_down(window, scroll_dist=-5):
    """ใช้ช่วยเลื่อนหน้าจอใน Popup ข้อมูลผู้ส่ง"""
    try:
        window.set_focus()
        rect = window.rectangle()
        center_x = rect.left + int(rect.width() * 0.5)
        center_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.2)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(0.8)
    except: pass

def smart_click(window, criteria_list, timeout=5):
    """(สำคัญ) ใช้คลิกปุ่มทั่วไปตามชื่อ"""
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

def click_element_by_id(window, exact_id, timeout=5, index=0):
    """(สำคัญ) ใช้คลิกปุ่ม Fast Cash และ Settle"""
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
    """(สำคัญ) ใช้เลือกบริการเสริม (Paper/EMS/SMS)"""
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
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(1)
    return False

def wait_for_text(window, text_list, timeout=5):
    """ใช้รอหน้าจอโหลด"""
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible(): return True
        except: pass
        time.sleep(0.5)
    return False

def smart_next(window):
    """(สำคัญ) ใช้กดถัดไป"""
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def check_error_popup(window, delay=0.5):
    """เช็ค Popup และกดปิด"""
    if delay > 0: time.sleep(delay)
    try:
        # 1. เช็คหน้าต่าง Popup
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2): return True
                else: window.type_keys("{ENTER}"); return True
        # 2. เช็ค Text บนหน้าจอ
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ", "Connect failed"], timeout=0.1): 
             log("[WARN] พบข้อความ Error บนหน้าจอ")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2): return True
             window.type_keys("{ENTER}"); return True
    except: pass
    return False

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, sender_postal):
    """(สำคัญ) จัดการ Popup ข้อมูลผู้ส่ง (Step 4)"""
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input(); edit.type_keys(str(sender_postal), with_spaces=True)
                    break 
        except: pass
        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input(); edit.type_keys(str(phone), with_spaces=True)
                        found_phone = True; break
            except: pass
            if found_phone: break
            force_scroll_down(window, -5)
        smart_next(window)

def process_payment(window, payment_method, received_amount):
    """(สำคัญ) จัดการการจ่ายเงิน Fast Cash (Step 10)"""
    log("--- ขั้นตอนการชำระเงิน (โหมด Fast Cash) ---")
    log("...ค้นหาปุ่ม 'รับเงิน'...")
    time.sleep(1.5)
    
    if smart_click(window, "รับเงิน"):
        log("...เข้าสู่หน้าชำระเงิน รอโหลด 1.5s...")
        time.sleep(1.5)
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    log("...กำลังกดปุ่ม Fast Cash (ID: EnableFastCash)...")
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] กดปุ่ม Fast Cash สำเร็จ -> ระบบดำเนินการตัดเงินทันที")
    else:
        log("[WARN] ไม่เจอปุ่ม ID 'EnableFastCash' -> ลองกด Enter")
        window.type_keys("{ENTER}")

    log("...รอหน้าสรุป/เงินทอน -> กด Enter ปิดรายการ...")
    time.sleep(2.0)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main (Money Order Version) =================
def run_smart_scenario(main_window, config):
    try:
        # --- 1. อ่าน Config สำหรับธนาณัติ ---
        # ข้อมูลผู้ส่ง (ใช้จาก TEST_DATA เดิม)
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        sender_phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        
        # ข้อมูลธุรกรรมธนาณัติ (อ่านจาก Section [MONEY_ORDER])
        mo_config = config['MONEY_ORDER'] if 'MONEY_ORDER' in config else {}
        
        amount = mo_config.get('Amount', '100')
        dest_postal = mo_config.get('DestinationPostalCode', '10110')
        rcv_fname = mo_config.get('ReceiverFirstName', 'TestName')
        rcv_lname = mo_config.get('ReceiverLastName', 'TestLast')
        options_str = mo_config.get('Options', '') # เช่น "Paper,EMS,SMS"
        
        # การตั้งค่าทั่วไป
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        
        # Payment Config
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'

    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log("--- เริ่มต้นการทำงาน (โหมดธนาณัติในประเทศ) ---")
    time.sleep(1.0)

    # Step 1: เลือกเมนู "ธนาณัติในประเทศ"
    if not smart_click(main_window, "ธนาณัติในประเทศ"): 
        log("[Error] หาเมนู 'ธนาณัติในประเทศ' ไม่เจอ")
        return
    time.sleep(step_delay)

    # Step 2: เลือกเมนู "รับฝากธนาณัติ"
    if not smart_click(main_window, "รับฝากธนาณัติ"): return
    time.sleep(step_delay)

    # Step 3: เลือกบริการ "101 - ธนาณัติธรรมดา"
    target_service_id = "PayOutDomesticSendMoneyNormal101"
    log(f"...เลือกบริการ ID: {target_service_id}...")
    
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] ไม่เจอปุ่มบริการ {target_service_id}")
        return
    time.sleep(step_delay)

    # Step 4: Popup ข้อมูลผู้ส่ง (อ่านบัตร/กรอกเลข ปณ/เบอร์)
    log("--- ขั้นตอนข้อมูลผู้ส่ง ---")
    process_sender_info_popup(main_window, sender_phone, sender_postal)
    time.sleep(step_delay)

    # Step 5: หน้าส่งเงิน (กรอกจำนวนเงิน และ ปณ.ปลายทาง)
    log(f"--- หน้าส่งเงิน (จำนวน: {amount}, ปลายทาง: {dest_postal}) ---")
    
    if not find_and_fill_smart(main_window, "จำนวนเงิน", "CurrencyAmount", amount):
        log("[WARN] กรอกจำนวนเงินไม่ได้")
    
    if not find_and_fill_smart(main_window, "ปลายทาง", "SpecificPostOfficeFilter", dest_postal):
         log("[WARN] กรอกรหัสไปรษณีย์ปลายทางไม่ได้")
    
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 6: เลือกบริการเสริม (Services Option)
    log(f"--- หน้าเลือกบริการเสริม ({options_str}) ---")
    
    if options_str:
        opts = [o.strip().lower() for o in options_str.split(',')]
        
        if 'paper' in opts or 'ธรรมดา' in opts:
            click_element_by_fuzzy_id(main_window, "TransferOption_PaperNotice")
        if 'ems' in opts or 'ด่วน' in opts:
            click_element_by_fuzzy_id(main_window, "TransferOption_EMSNotice")
        if 'sms' in opts or 'sms' in opts:
            click_element_by_fuzzy_id(main_window, "TransferOption_SMSNotice")

    smart_next(main_window)
    time.sleep(step_delay)

    # Step 7: หน้าข้อมูลผู้ส่ง (กดถัดไปตามโจทย์)
    log("--- หน้าข้อมูลผู้ส่ง (ยืนยัน) ---")
    time.sleep(0.5) 
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 8: หน้าข้อมูลผู้รับ (กรอกชื่อ-นามสกุล)
    log(f"--- หน้าข้อมูลผู้รับ ({rcv_fname} {rcv_lname}) ---")
    find_and_fill_smart(main_window, "ชื่อ", "CustomerFirstName", rcv_fname)
    find_and_fill_smart(main_window, "นามสกุล", "CustomerLastName", rcv_lname)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 9: กดรับเงิน
    log("--- ขั้นตอนการรับเงิน ---")
    if smart_click(main_window, "รับเงิน"):
        log("...กดปุ่ม 'รับเงิน' แล้ว...")
        time.sleep(1.5)
    else:
        smart_next(main_window) # ลองกดถัดไปเผื่อเข้าหน้า Payment
        time.sleep(1.0)

    # Step 10: ชำระเงินแบบไม่มีเงินทอน (Fast Cash)
    process_payment(main_window, pay_method, pay_amount)

    log("\n[SUCCESS] จบการทำงานธนาณัติครบทุกขั้นตอน")

# ================= 5. Start App =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to Title: {app_title} (Wait: {wait}s)")
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")