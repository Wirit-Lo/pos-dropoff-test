import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    if not os.path.exists(filename): return None
    config = configparser.ConfigParser()
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Smart System (วัดความเร็วเครื่อง) =================
def calibrate_system():
    """
    วัดความเร็ว CPU เพื่อปรับเวลาการรอ (Timeout) ให้เหมาะสม
    เครื่องเร็ว -> รอน้อย / เครื่องช้า -> รอนาน
    """
    log("...ตรวจสอบความเร็วเครื่อง (Calibration)...")
    start = time.time()
    for _ in range(3000000): pass # Test Loop
    duration = time.time() - start
    
    # คำนวณ Factor: ถ้าใช้เวลา > 0.5 วิ ถือว่าช้า ให้คูณเวลาเพิ่ม 2 เท่า
    factor = 2.0 if duration > 0.5 else (1.5 if duration > 0.25 else 1.0)
    log(f"[System] Speed Factor: x{factor} (Test Time: {duration:.2f}s)")
    return factor

# ================= 3. Smart Actions (ค้นหา / เลื่อน / พิมพ์) =================
def smart_click(window, criteria_list, timeout=5):
    """หาปุ่มจากรายชื่อแล้วกด (รองรับ Deep Search)"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                # 1. หาแบบปกติ
                if window.child_window(title=criteria).exists():
                    window.child_window(title=criteria).click_input()
                    log(f"[/] Click '{criteria}'")
                    return True
                
                # 2. หาแบบ Deep Search (สแกนลูกหลาน)
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text():
                        try:
                            child.click_input()
                            log(f"[/] Click '{criteria}' (Deep)")
                            return True
                        except:
                            child.click_input(double=True)
                            log(f"[/] Double Click '{criteria}'")
                            return True
            except: pass
        time.sleep(0.3) # รอสักครู่แล้วหาใหม่
    return False

def force_scroll(window, dist=-20):
    """เลื่อนหน้าจอลง (คลิกกลางจอก่อนเลื่อน)"""
    try:
        rect = window.rectangle()
        center_x = rect.left + 300
        center_y = rect.top + 300
        mouse.click(coords=(center_x, center_y)) # Focus
        time.sleep(0.2)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=dist)
        time.sleep(0.5)
    except:
        window.type_keys("{PGDN}") # ถ้า Mouse ไม่ไป ใช้ PageDown

def smart_input_phone(window, phone, scroll_dist):
    """
    Logic การกรอกเบอร์: เลื่อนจอลง -> หา Label -> กด Tab -> พิมพ์
    """
    log(f"...ค้นหาช่องเบอร์โทรศัพท์ ({phone})...")
    labels = ["หมายเลขโทรศัพท์", "เบอร์โทรศัพท์", "โทรศัพท์", "เบอร์มือถือ"]
    
    for i in range(3): # ให้โอกาสหาและเลื่อน 3 รอบ
        # ลองหา Label ก่อน
        if smart_click(window, labels, timeout=1):
            # เจอ Label! กด Tab เข้าช่อง Input
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(phone), with_spaces=True)
            log("[/] กรอกเบอร์สำเร็จ (Label+Tab)")
            return True
        
        # ถ้าหาไม่เจอ ให้เลื่อนจอลง
        log(f"...ไม่เจอช่องเบอร์ (รอบ {i+1}) -> เลื่อนจอลง...")
        force_scroll(window, scroll_dist)
        
    log("[!] หาไม่เจอจนสุดทาง -> ลองพิมพ์เลย (Blind Type)")
    window.type_keys(str(phone), with_spaces=True)

def check_sender_popup(window, config, speed_factor):
    """
    เช็ค Popup ผู้ฝากส่ง:
    ถ้าเจอ -> อ่านบัตร -> กรอกเบอร์ -> ถัดไป
    """
    popup_wait = int(3 * speed_factor)
    log(f"...เช็ค Popup ผู้ฝากส่ง (รอสูงสุด {popup_wait}s)...")
    
    if smart_click(window, "อ่านบัตรประชาชน", timeout=popup_wait):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> อ่านบัตรแล้ว")
        time.sleep(1) # รอข้อมูลโหลด
        
        # --- ขั้นตอนกรอกเบอร์ ---
        try:
            phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
            scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -20))
            smart_input_phone(window, phone, scroll_dist)
        except:
            log("[!] กรอกเบอร์ผิดพลาด")

        # กดถัดไป
        smart_click(window, "ถัดไป", timeout=int(5*speed_factor))
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ไปต่อทันที")

def smart_input_weight(window, value, timeout):
    """กรอกน้ำหนัก: หา EditBox หรือ Click Label+Tab"""
    log(f"...กรอกน้ำหนัก: {value}")
    
    # 1. ลองหา Edit Box โดยตรง
    start = time.time()
    while time.time() - start < timeout:
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                edits[0].click_input()
                edits[0].type_keys(str(value), with_spaces=True)
                log(f"[/] กรอกน้ำหนัก (EditBox)")
                return True
        except: pass
        time.sleep(0.5)

    # 2. ลอง Click Label + Tab
    if smart_click(window, "น้ำหนัก", timeout=2):
        window.type_keys("{TAB}")
        time.sleep(0.2)
        window.type_keys(str(value), with_spaces=True)
        log(f"[/] กรอกน้ำหนัก (Label+Tab)")
        return True

    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window, timeout):
    if not smart_click(window, "ถัดไป", timeout=timeout):
        window.type_keys("{ENTER}")

def wait_for_text(window, text, timeout):
    log(f"...รอข้อความ '{text}'...")
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
def run_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
        base_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))
    except: 
        log("[Error] อ่าน Config ผิดพลาด")
        return

    # 1. วัดความเร็วเครื่อง
    speed_factor = calibrate_system()
    final_timeout = int(base_timeout * speed_factor)
    
    log(f"\n--- เริ่ม Scenario (ซองจดหมาย) Timeout: {final_timeout}s ---")
    time.sleep(1)

    # Step 1: รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ", timeout=final_timeout): return
    time.sleep(step_delay)

    # --- Check Popup (ด้วยความเร็วที่แม่นยำ) ---
    check_sender_popup(main_window, config, speed_factor)
    time.sleep(step_delay)

    # Step 2: ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย", timeout=final_timeout): return
    time.sleep(step_delay)

    # Step 3: หมวดหมู่ -> กด Enter ผ่าน
    log("STEP 3: กด Enter ผ่านหมวดหมู่")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # Step 4: น้ำหนัก
    smart_input_weight(main_window, weight, timeout=final_timeout)
    smart_next(main_window, timeout=final_timeout)
    
    # รอหน้าเปลี่ยน
    wait_for_text(main_window, "รหัสไปรษณีย์", timeout=final_timeout)
    time.sleep(0.5)

    # Step 5: รหัสไปรษณีย์
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
        
    smart_next(main_window, timeout=final_timeout)
    time.sleep(step_delay)

    # Step 6: จบงาน
    log("STEP 6: จบงาน")
    if smart_click(main_window, "ดำเนินการ", timeout=5):
        log("[/] กดปุ่ม 'ดำเนินการ'")
    
    smart_click(main_window, ["เสร็จสิ้น", "Settle", "ยืนยัน"], timeout=5)
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
            run_scenario(win, conf)
        except Exception as e:
            log(f"Error: {e}")