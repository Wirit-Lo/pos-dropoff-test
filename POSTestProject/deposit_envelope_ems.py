import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): 
        # Create Dummy config if not exists for testing
        return {'DEPOSIT_ENVELOPE': {}, 'TEST_DATA': {}, 'SETTINGS': {}, 'APP': {'WindowTitle': 'Riposte POS Application'}} 
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

def debug_current_screen(window):
    log("!!! DEBUG: ตรวจสอบหน้าจอปัจจุบัน !!!")
    try:
        texts = [child.window_text() for child in window.descendants(control_type="Text") if child.is_visible() and child.window_text()]
        log(f"ข้อความที่พบบนหน้าจอ: {texts[:20]}...")
    except Exception as e:
        log(f"Debug Error: {e}")

# ================= 2. Helper Functions (Scroll & Search) =================
def force_scroll_down(window, scroll_dist=-5):
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except: pass

def smart_click(window, criteria_list, timeout=5, optional=False):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                # 1. ลองหาแบบ Exact Match ก่อน
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.5)
    
    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def smart_click_by_text_location(window, target_text, y_offset=0):
    """
    [NEW] ฟังก์ชันสำหรับคลิกปุ่มที่ไม่มีชื่อ (Nameless Button)
    โดยการหา Text Label ภายในปุ่มนั้น แล้วคลิกที่ Text หรือคลิกต่ำลงมา
    """
    log(f"...พยายามหา Text: '{target_text}' เพื่อคลิก...")
    try:
        # หา Element ประเภท Text ที่มีชื่อตรงกับที่ต้องการ
        text_elements = window.descendants(control_type="Text")
        for txt in text_elements:
            if target_text in txt.window_text() and txt.is_visible():
                # เจอข้อความแล้ว
                rect = txt.rectangle()
                click_x = rect.mid_point().x
                click_y = rect.mid_point().y + y_offset # บวก Offset เพื่อคลิกต่ำลงมา (เผื่อข้อความอยู่ขอบบน)
                
                log(f"[/] เจอข้อความ '{target_text}' -> คลิกที่พิกัด ({click_x}, {click_y})")
                mouse.click(button='left', coords=(click_x, click_y))
                return True
    except Exception as e:
        log(f"[!] Error smart_click_by_text_location: {e}")
    return False

def click_screen_percentage(window, pct_x, pct_y):
    """คลิกโดยอ้างอิง % ของขนาดหน้าต่าง (Fallback สุดท้าย)"""
    try:
        rect = window.rectangle()
        x = rect.left + int(rect.width() * pct_x)
        y = rect.top + int(rect.height() * pct_y)
        log(f"...Force Click ที่พิกัด {pct_x*100}% , {pct_y*100}%")
        mouse.click(button='left', coords=(x, y))
        return True
    except: return False

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value):
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")
    # (โค้ดเดิม) ...
    for i in range(scroll_times + 1):
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    return True
            
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass
        if i < scroll_times:
            force_scroll_down(window)
    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง")
        time.sleep(1)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้าม")

def wait_for_text(window, text, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False').lower() == 'true'
        insurance_amount = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except:
        weight, postal, special_options_str, add_insurance, insurance_amount, phone, step_delay = '10', '10110', '', False, '0', '0812345678', 1

    log(f"\n--- เริ่มต้น Scenario (New Fix) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # ผู้ฝากส่ง
    process_sender_info(main_window, phone)
    time.sleep(step_delay)

    # 2. ซองจดหมาย
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. เลือกหมวดหมู่
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            smart_click(main_window, opt.strip(), timeout=2, optional=True)
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    wait_for_text(main_window, "รหัสไปรษณีย์")

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    main_window.type_keys(str(postal), with_spaces=True)
    smart_next(main_window)
    time.sleep(2)

    # Check Popup ทับซ้อน
    if smart_click(main_window, "ดำเนินการ", timeout=2, optional=True):
        time.sleep(1)
    else:
        main_window.type_keys("{ENTER}")

    # ================= [FIXED STEP 6 START] =================
    # หน้าเลือกบริการ EMS / ลงทะเบียน / พัสดุ
    log("STEP 6: เลือกบริการ (Fixed Logic)")
    
    # รอให้หน้าจอโหลด Text คำว่า "บริการหลัก" หรือ "EMS" ก่อน
    if wait_for_text(main_window, "บริการหลัก", timeout=10) or wait_for_text(main_window, "อีเอ็มเอส", timeout=10):
        time.sleep(1)
        main_window.set_focus()

        # วิธีที่ 1: หา Text "บริการอีเอ็มเอส" แล้วคลิกที่ตัวมัน หรือต่ำกว่ามัน 30px
        # (จากรูป Screenshot จะเห็นคำว่า 'บริการอีเอ็มเอส' อยู่ในกรอบ)
        success = smart_click_by_text_location(main_window, "บริการอีเอ็มเอส", y_offset=40)
        
        if not success:
            # วิธีที่ 2: ลองหาคำว่า "EMS ในประเทศ"
            success = smart_click_by_text_location(main_window, "EMS ในประเทศ", y_offset=0)

        if not success:
            # วิธีที่ 3 (Fallback): ถ้าหา Text ไม่เจอเลย ให้คลิกตำแหน่ง Grid แรก
            # สมมติว่า EMS อยู่ตำแหน่งแรกซ้ายมือเสมอ (ประมาณ 20% จากซ้าย, 40% จากบน)
            log("[!] หา Text ไม่เจอ -> ใช้ Coordinate Click ที่ตำแหน่งบริการแรก")
            click_screen_percentage(main_window, 0.20, 0.40)
        
        time.sleep(1.5)
        
        # กด 0 เพื่อเลือกประเภท (ถ้าจำเป็นต้องเลือก Sub-type)
        log("...กด 0 (เพื่อเลือกประเภทสิ่งของถ้ามี)...")
        main_window.type_keys("0") 
        time.sleep(step_delay)

    else:
        log("[X] ไม่เจอหน้าบริการหลัก (Timeout)")
        debug_current_screen(main_window)
        return
    # ================= [FIXED STEP 6 END] =================

    # 7. เพิ่มประกัน
    if add_insurance:
        log(f"STEP 7: เพิ่มประกัน {insurance_amount}")
        if not smart_click(main_window, ["+", "เพิ่ม"], timeout=3, optional=True):
            main_window.type_keys("+")
        
        if wait_for_text(main_window, "วงเงินประกัน", timeout=5):
            main_window.type_keys(str(insurance_amount))
            time.sleep(1)
            main_window.type_keys("{ENTER}")
            time.sleep(2)
    
    main_window.type_keys("{ENTER}") # ไปหน้าบริการพิเศษ

    # 8. บริการพิเศษ
    if wait_for_text(main_window, "บริการพิเศษ", timeout=10):
        log("STEP 8: บริการพิเศษ -> กด A")
        main_window.type_keys("A")
    
    log("[SUCCESS] จบการทำงาน")

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            # ปรับ Timeout ให้ Connect นานขึ้น
            app = Application(backend="uia").connect(title_re=".*POS.*", timeout=15)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")