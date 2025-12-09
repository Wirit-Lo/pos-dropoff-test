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

# ================= 2. System Calibration =================
def get_machine_delay_factor():
    """วัดความเร็วเครื่องเพื่อปรับ Timeout อัตโนมัติ"""
    log("...กำลังตรวจสอบประสิทธิภาพเครื่อง (Calibrating)...")
    start_time = time.time()
    count = 0
    for i in range(3000000): count += 1
    duration = end_time = time.time() - start_time
    
    if duration > 0.5:
        log(f"[System] เครื่องช้า ({duration:.2f}s) -> Timeout x2.0")
        return 2.0
    elif duration > 0.25:
        log(f"[System] เครื่องปานกลาง ({duration:.2f}s) -> Timeout x1.5")
        return 1.5
    else:
        log(f"[System] เครื่องเร็ว ({duration:.2f}s) -> Timeout x1.0")
        return 1.0

# ================= 3. Smart Functions (Adaptive) =================
def force_scroll_down(window, scroll_dist=-20):
    """เลื่อนหน้าจอลง (บังคับเลื่อน)"""
    # log(f"...เลื่อนหน้าจอ (Wheel {scroll_dist})...")
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        
        # คลิกกลางจอเพื่อ Focus
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.2)
        # สั่งเลื่อน
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(0.5)
    except:
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายชื่อ (รองรับ Deep Search)"""
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

def check_sender_popup(window, config, current_timeout):
    """
    ฟังก์ชันเช็คหน้า 'ผู้ฝากส่ง' (แก้ไขใหม่: เลื่อนหาจนกว่าจะเจอช่องเบอร์)
    """
    log(f"...เช็ค Popup ผู้ฝากส่ง (รอสูงสุด {current_timeout} วิ)...")
    
    if smart_click(window, "อ่านบัตรประชาชน", timeout=current_timeout, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        
        try:
            phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
            scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -20))
            
            log(f"...กำลังหาช่องกรอกเบอร์โทรศัพท์: {phone}")
            
            # --- LOOP SEARCH: เลื่อนหาจนกว่าจะเจอ (สูงสุด 3 รอบ) ---
            found_phone_field = False
            labels = ["หมายเลขโทรศัพท์", "เบอร์โทรศัพท์", "โทรศัพท์", "เบอร์มือถือ"]
            
            for i in range(4): # ลองเลื่อนหา 4 รอบ
                # ลองหา Label บนหน้าจอก่อน
                if smart_click(window, labels, timeout=1, optional=True):
                    # ถ้าเจอ -> กด Tab เข้าช่อง -> พิมพ์
                    window.type_keys("{TAB}")
                    time.sleep(0.2)
                    window.type_keys(str(phone), with_spaces=True)
                    log("[/] กรอกเบอร์เรียบร้อย (เจอช่องแล้ว)")
                    found_phone_field = True
                    break
                else:
                    # ถ้าไม่เจอ -> เลื่อนจอลง แล้วหาใหม่
                    log(f"...ยังไม่เจอช่องเบอร์ (รอบที่ {i+1}) -> เลื่อนจอลง...")
                    force_scroll_down(window, scroll_dist)
            
            if not found_phone_field:
                log("[!] เลื่อนหาจนสุดแล้วยังไม่เจอช่องเบอร์ -> ลองพิมพ์เลย (Blind Type)")
                window.type_keys(str(phone), with_spaces=True)
                
        except Exception as e:
            log(f"[!] Error ช่วงกรอกเบอร์: {e}")

        smart_click(window, "ถัดไป", timeout=current_timeout, optional=True)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def smart_input_weight(window, value, timeout=5):
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    # 1. ลองหา Edit Box
    try:
        start = time.time()
        while time.time() - start < timeout:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits: 
                target = edits[0]
                target.click_input()
                target.type_keys(str(value), with_spaces=True)
                log(f"[/] กรอกน้ำหนัก '{value}' (EditBox)")
                return True
            time.sleep(0.5)
    except: pass

    # 2. ลองสูตร Click Label + Tab
    try:
        if smart_click(window, "น้ำหนัก", timeout=2, optional=True):
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอกน้ำหนัก '{value}' (Label+Tab)")
            return True
    except: pass
    
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window, timeout=5):
    if not smart_click(window, "ถัดไป", timeout=timeout, optional=True):
        window.type_keys("{ENTER}")

def wait_for_text(window, text, timeout=10):
    log(f"...รอข้อความ '{text}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    log(f"[!] รอ '{text}' จนหมดเวลา")
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
        base_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))
    except: return

    speed_factor = get_machine_delay_factor()
    final_timeout = int(base_timeout * speed_factor)
    
    log(f"\n--- เริ่มต้น Scenario (ซองจดหมาย - Smart Scroll) ---")
    log(f"Timeout: {final_timeout}s (Factor {speed_factor}x)")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ", timeout=final_timeout): return
    time.sleep(step_delay)

    # --- เช็ค Popup ผู้ฝากส่ง ---
    check_sender_popup(main_window, config, final_timeout)
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย", timeout=final_timeout): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่) --> กด Enter
    log("STEP 3: กด Enter ผ่านหมวดหมู่")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight, timeout=final_timeout)
    smart_next(main_window, timeout=final_timeout)
    
    # --- รอหน้าจอเปลี่ยน ---
    wait_for_text(main_window, "รหัสไปรษณีย์", timeout=final_timeout)
    time.sleep(0.5) 

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        start = time.time()
        while time.time() - start < final_timeout:
            edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
            if edits: 
                edits[0].click_input()
                edits[0].type_keys(str(postal))
                break
            time.sleep(0.5)
    except:
        main_window.type_keys(str(postal), with_spaces=True)
    
    smart_next(main_window, timeout=final_timeout)
    time.sleep(step_delay)

    # 6. จบงาน
    log("STEP 6: จบงาน")
    if smart_click(main_window, "ดำเนินการ", timeout=5, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' (Popup ทับซ้อน) สำเร็จ")
    
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=5, optional=True)
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