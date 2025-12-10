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

# ================= 2. Helper Functions (Scroll & Search) =================
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
    """คลิกปุ่มตามรายการชื่อ (รองรับหลายชื่อ)"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
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
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            log(f"[/] เจอ Edit Box และกรอก '{value}' สำเร็จ")
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
                    log(f"[/] กรอก {label_text} สำเร็จ")
                    return True
            
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True
        except Exception as e:
            log(f"[!] Error finding input: {e}")

        if i < scroll_times:
            log(f"[Rotate {i+1}] หาช่องไม่เจอ... เลื่อนจอลง...")
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)
    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number):
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        log("...ข้อมูลครบถ้วน กดถัดไป...")
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def handle_postal_overlap(window):
    """จัดการ Popup รหัสไปรษณีย์ทับซ้อน"""
    log("...ตรวจสอบ Popup รหัสไปรษณีย์ทับซ้อน...")
    time.sleep(1) # รอ Popup เด้ง
    
    # เช็คว่ามีข้อความ "พื้นที่รหัสไปรษณีย์ทับซ้อน" หรือปุ่ม "ดำเนินการ" หรือไม่
    if check_exists(window, "พื้นที่รหัสไปรษณีย์ทับซ้อน") or check_exists(window, "ดำเนินการ"):
        log("[Popup] เจอแจ้งเตือนรหัสไปรษณีย์ทับซ้อน -> กด Enter/ดำเนินการ")
        # กดปุ่มดำเนินการ หรือ Enter
        if not smart_click(window, "ดำเนินการ", timeout=2, optional=True):
            window.type_keys("{ENTER}")
        time.sleep(1)
    else:
        log("[Info] ไม่เจอ Popup ทับซ้อน (หรือผ่านไปแล้ว)")

def wait_for_text(window, text, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if check_exists(window, text): return True
        time.sleep(0.5)
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        add_insurance = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('InsuranceAmount', '0')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except Exception as e: 
        log(f"[Error] Config ผิดพลาด: {e}")
        return

    log(f"\n--- เริ่มต้น Scenario (Postal: {postal}) ---")
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

    # เลือกหมวดหมู่
    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        for opt in options:
            if opt:
                smart_click(main_window, opt, timeout=2, optional=True)
                time.sleep(0.5)

    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    wait_for_text(main_window, "รหัสไปรษณีย์")
    time.sleep(0.5) 

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(postal))
        else:
            main_window.type_keys(str(postal), with_spaces=True)
    except:
        main_window.type_keys(str(postal), with_spaces=True)
    
    # กดถัดไป (อาจจะเจอ Popup ทับซ้อนที่นี่)
    smart_next(main_window)
    
    # [NEW] จัดการ Popup ทับซ้อน
    handle_postal_overlap(main_window)
    
    time.sleep(step_delay)

    # =========================================================
    # --- STEP 5.5: เลือกบริการ (EMS) ---
    # =========================================================
    log("STEP 5.5: เข้าสู่หน้าเลือกบริการหลัก (EMS)")
    
    # คำที่ใช้ค้นหาปุ่ม EMS
    ems_keywords = ["บริการอีเอ็มเอส", "EMS", "E", "บริการด่วนพิเศษ"]
    
    # 1. พยายามกดปุ่ม EMS
    if smart_click(main_window, ems_keywords, timeout=5, optional=False):
        log("[/] กดเลือก EMS แล้ว... กำลังตรวจสอบการเปลี่ยนหน้า")
        time.sleep(2) 

        # 2. ตรวจสอบว่าหน้าจอเปลี่ยนเป็นหน้าสรุป (เหมือนในรูป) หรือไม่
        # คีย์เวิร์ดที่ควรเจอเมื่อเปลี่ยนหน้าสำเร็จ: "EMS ในประเทศ", "รับประกัน", หรือ "1-2 วันทำการ" (ที่อยู่ในกล่องสรุป)
        success_markers = ["EMS ในประเทศ", "รับประกัน", "1-2 วันทำการ", "เพิ่ม:", "Expected"]
        
        is_page_updated = False
        for marker in success_markers:
            if check_exists(main_window, marker):
                is_page_updated = True
                log(f"[/] พบข้อความยืนยัน: '{marker}' -> หน้าจอเปลี่ยนสำเร็จ")
                break
        
        # 3. ถ้ายังไม่เปลี่ยน -> ลองกดปุ่ม "ถัดไป" หรือ "Enter" ย้ำอีกที
        # เพราะบางทีการกดการ์ดแค่เลือก (Select) แต่ต้องกด Next เพื่อไปต่อ
        if not is_page_updated:
            log("[!] หน้าจอยังไม่เปลี่ยนเป็นหน้าสรุป... กำลังกดปุ่ม 'ถัดไป' หรือ 'Enter' เพื่อยืนยัน")
            smart_next(main_window) # สั่งกด Next หรือ Enter
            time.sleep(3) # รอโหลด
            
            # เช็คอีกรอบ
            for marker in success_markers:
                if check_exists(main_window, marker):
                    is_page_updated = True
                    log(f"[/] พบข้อความยืนยันหลังกดถัดไป: '{marker}'")
                    break
        
        # 4. ถ้ายังไม่เปลี่ยนจริงๆ ให้หยุดทำงาน
        if not is_page_updated:
             log("\n[STOP] หยุดการทำงาน: เลือก EMS แล้วแต่หน้าจอไม่เปลี่ยนไปหน้าสรุป (ไม่พบคำว่า 'EMS ในประเทศ')")
             raise RuntimeError("Selected EMS but page did not update to Summary state.")

        # --- ส่วนประกัน (ทำงานต่อเมื่อหน้าจอเปลี่ยนสำเร็จแล้ว) ---
        if add_insurance.lower() == 'true':
            log(f"...ตรวจสอบประกันภัย (วงเงิน: {insurance_amt})")
            # เช็คว่ามีปุ่มให้กดเพิ่มประกันไหม (บางทีมันอาจจะอยู่ในกล่องสรุป)
            if smart_click(main_window, ["+", "AddService", "รับประกัน"], timeout=3, optional=True):
                time.sleep(1)
                smart_input_with_scroll(main_window, "วงเงิน", insurance_amt)
                smart_click(main_window, ["ตกลง", "OK"], timeout=2, optional=True)
            else:
                log("[Info] หาปุ่มกดเพิ่มประกันไม่เจอ (อาจจะถูกเพิ่มแล้ว หรือไม่มีปุ่ม)")

    else:
        # ถ้าหาปุ่ม EMS ไม่เจอตั้งแต่แรก
        log("[!] หาปุ่มเลือกบริการ EMS ไม่เจอ")
        raise RuntimeError("Cannot find EMS service button.")

    # 6. จบงาน
    log("STEP 6: จบงาน")
    # กดดำเนินการ/เสร็จสิ้น
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' สำเร็จ")
    
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=3, optional=True)
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
    else:
        log("[Error] ไม่พบไฟล์ config.ini")