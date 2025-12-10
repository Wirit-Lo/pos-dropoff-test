import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions =================
def force_scroll_down(window, scroll_dist=-5):
    """ฟังก์ชันช่วยเลื่อนหน้าจอลงโดยใช้ Mouse Wheel"""
    log(f"...กำลังเลื่อนหน้าจอลง (Mouse Wheel {scroll_dist})...")
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except Exception as e:
        log(f"[!] Mouse scroll failed: {e}")
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            # วาดกรอบสีแดงให้เห็นว่ากำลังจะกดปุ่มไหน
                            child.draw_outline(colour='red')
                            child.click_input()
                            log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                            return True
                        except:
                            child.click_input(double=True)
                            log(f"[/] Double Click '{criteria}'")
                            return True
            except: pass
        time.sleep(0.5)

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def check_exists(window, text):
    """เช็คว่ามีข้อความปรากฏบนหน้าจอหรือไม่"""
    try:
        for child in window.descendants():
            if child.is_visible() and text in child.window_text():
                return True
    except: pass
    return False

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
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)
    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง (ข้าม)")

def handle_postal_overlap(window):
    """จัดการ Popup รหัสไปรษณีย์ทับซ้อน"""
    time.sleep(1)
    if check_exists(window, "พื้นที่รหัสไปรษณีย์ทับซ้อน") or check_exists(window, "ดำเนินการ"):
        log("[Popup] เจอแจ้งเตือนรหัสไปรษณีย์ทับซ้อน -> กด Enter/ดำเนินการ")
        if not smart_click(window, "ดำเนินการ", timeout=2, optional=True):
            window.type_keys("{ENTER}")
        time.sleep(1)

def wait_for_text(window, text, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if check_exists(window, text): return True
        time.sleep(0.5)
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        # Load Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '').split(',')
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: return

    log(f"\n--- เริ่มต้นทำงาน ---")
    time.sleep(1)

    # [SKIP LOGIC] ตรวจสอบว่าตอนนี้อยู่หน้า "บริการหลัก" แล้วหรือยัง?
    # ถ้าอยู่แล้ว จะข้ามขั้นตอนแรกๆ เพื่อให้คุณเทสแค่กด E ได้เลย
    is_already_at_service = check_exists(main_window, "บริการหลัก")
    
    if is_already_at_service:
        log("\n[SKIP] ตรวจพบว่าอยู่หน้า 'บริการหลัก' แล้ว -> ข้ามไปขั้นตอนกด EMS ทันที!\n")
    else:
        # --- ขั้นตอนปกติ (ถ้ายังไม่ถึงหน้าบริการ) ---
        if not smart_click(main_window, "รับฝากสิ่งของ"): return
        time.sleep(step_delay)
        process_sender_info(main_window, phone)
        time.sleep(step_delay)
        if not smart_click(main_window, "ซองจดหมาย"): return
        time.sleep(step_delay)
        
        # Options
        for opt in special_options:
            if opt.strip(): smart_click(main_window, opt.strip(), timeout=2, optional=True)
        
        main_window.type_keys("{ENTER}")
        time.sleep(step_delay)
        smart_input_weight(main_window, weight)
        smart_next(main_window)
        wait_for_text(main_window, "รหัสไปรษณีย์")
        
        # Postal Code
        log(f"...กรอกรหัสไปรษณีย์: {postal}")
        smart_input_with_scroll(main_window, "รหัสไปรษณีย์", postal)
        smart_next(main_window)
        handle_postal_overlap(main_window)
        time.sleep(step_delay)


    # =========================================================
    # --- STEP 5.5: เลือกบริการ (EMS) --- (จุดที่คุณต้องการเทส)
    # =========================================================
    log("STEP 5.5: หน้าเลือกบริการหลัก -> พยายามเข้าหน้า EMS")
    
    # วนลูปพยายามกดจนกว่าจะผ่าน (Retry Logic)
    max_retries = 3
    for attempt in range(max_retries):
        log(f"...ความพยายามครั้งที่ {attempt+1}")
        
        # 1. กดที่การ์ด EMS
        ems_keywords = ["บริการอีเอ็มเอส", "EMS", "E", "บริการด่วนพิเศษ"]
        if smart_click(main_window, ems_keywords, timeout=5):
            log("[/] กดการ์ด EMS แล้ว")
        
        # 2. [สำคัญ] กดปุ่ม "ถัดไป" หรือ "Enter" เพื่อยืนยันการเลือก
        # จากรูป UI การกดการ์ดอาจจะแค่ Select แต่ไม่ไปต่อ ต้องกด Next
        log("...กำลังกดปุ่ม 'ถัดไป' หรือ 'Enter' เพื่อยืนยันการเลือก")
        if not smart_click(main_window, ["ถัดไป", "Next", "ดำเนินการ"], timeout=3, optional=True):
            main_window.type_keys("{ENTER}")
        
        time.sleep(3) # รอโหลดหน้าใหม่

        # 3. เช็คว่าเปลี่ยนหน้าสำเร็จไหม?
        # หน้าใหม่ต้องมีคำว่า: "EMS ในประเทศ" (ในรายการขวา), "รับประกัน", "เพิ่ม:", หรือ "Expected"
        success_markers = ["EMS ในประเทศ", "รับประกัน", "1-2 วันทำการ", "เพิ่ม:", "Expected"]
        is_success = False
        
        for marker in success_markers:
            if check_exists(main_window, marker):
                is_success = True
                log(f"[/] สำเร็จ! พบข้อความ '{marker}' -> อยู่หน้าสรุปแล้ว")
                break
        
        if is_success:
            break # ออกจากลูป Retry
        else:
            log("[!] หน้าจอยังไม่เปลี่ยน... ลองใหม่")
            
            # ถ้ายังเห็นคำว่า "บริการหลัก" แสดงว่ายังอยู่ที่เดิม
            if check_exists(main_window, "บริการหลัก"):
                log("    -> ยังติดอยู่ที่หน้าบริการหลัก")

    if not is_success:
        log("\n[FAIL] ไม่สามารถเข้าสู่หน้า EMS ได้หลังจากพยายามหลายครั้ง")
        return # หยุดการทำงานถ้าไปต่อไม่ได้

    # --- ส่วนประกัน (ทำงานต่อเมื่อหน้าจอเปลี่ยนสำเร็จแล้ว) ---
    if add_insurance.lower() == 'true':
        log(f"...ตรวจสอบประกันภัย (วงเงิน: {insurance_amt})")
        if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
            time.sleep(1)
            smart_input_with_scroll(main_window, "วงเงิน", insurance_amt)
            smart_click(main_window, ["ตกลง", "OK"], timeout=2, optional=True)

    # 6. จบงาน
    log("STEP 6: จบงาน")
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' สำเร็จ")
    
    smart_click(main_window, ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"], timeout=3, optional=True)
    main_window.type_keys("{ENTER}")
    log("\n[SUCCESS] จบการทำงาน")

# ================= 5. Execution =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            connect_wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app = Application(backend="uia").connect(title_re=conf['APP']['WindowTitle'], timeout=connect_wait)
            win = app.top_window()
            win.set_focus()
            run_smart_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")