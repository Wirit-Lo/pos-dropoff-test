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
    log("...ตรวจสอบความเร็วเครื่อง (Calibration)...")
    start = time.time()
    for _ in range(3000000): pass 
    duration = time.time() - start
    factor = 2.0 if duration > 0.5 else (1.5 if duration > 0.25 else 1.0)
    log(f"[System] Speed Factor: x{factor} (Test Time: {duration:.2f}s)")
    return factor

# ================= 3. Smart Actions =================
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
                
                # 2. หาแบบ Deep Search
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
        time.sleep(0.3)
    return False

def force_scroll(window):
    """เลื่อนหน้าจอลง (ใช้ PageDown เพื่อความชัวร์)"""
    log("...สั่งเลื่อนหน้าจอลง (PageDown)...")
    try:
        # คลิกกลางจอก่อนเพื่อให้ Focus อยู่ที่เนื้อหา
        rect = window.rectangle()
        mouse.click(coords=(rect.left + 300, rect.top + 300))
        time.sleep(0.2)
        # กด PageDown 2 ครั้ง เพื่อให้ลงมาถึงข้างล่างแน่ๆ
        window.type_keys("{PGDN}")
        time.sleep(0.5)
        window.type_keys("{PGDN}")
        time.sleep(0.5)
    except:
        log("[!] Scroll Error")

def smart_input_phone_popup_logic(window, phone):
    """
    Logic เฉพาะสำหรับหน้า Popup:
    เลื่อนจอ -> หา Label เบอร์ -> กด Tab -> พิมพ์
    """
    # 1. เลื่อนจอก่อนเลย เพราะเบอร์อยู่ข้างล่างแน่นอน
    force_scroll(window)
    
    log(f"...ค้นหาช่องเบอร์โทรศัพท์ ({phone})...")
    labels = ["หมายเลขโทรศัพท์", "เบอร์โทรศัพท์", "โทรศัพท์", "เบอร์มือถือ"]
    
    # พยายามหา Label ให้เจอ
    if smart_click(window, labels, timeout=3):
        # เจอ Label! กด Tab เข้าช่อง Input
        window.type_keys("{TAB}")
        time.sleep(0.5) # รอ Focus ย้าย
        window.type_keys(str(phone), with_spaces=True)
        log("[/] กรอกเบอร์สำเร็จ (Label+Tab)")
        return True
    
    log("[!] หา Label เบอร์ไม่เจอ (Scroll แล้วก็ยังไม่เจอ) -> ข้ามการกรอก")
    return False

def check_sender_popup(window, config, speed_factor):
    """
    เช็ค Popup ผู้ฝากส่ง:
    ถ้าเจอ -> อ่านบัตร -> เลื่อนจอ -> กรอกเบอร์ -> ถัดไป
    ถ้าไม่เจอ -> ผ่านเลย
    """
    # รอนานหน่อยเผื่อเครื่องช้า (3วิ x factor)
    popup_wait = int(3 * speed_factor)
    log(f"...เช็ค Popup ผู้ฝากส่ง (รอสูงสุด {popup_wait}s)...")
    
    # ถ้าเจอปุ่ม "อ่านบัตรประชาชน" แสดงว่า Popup เด้ง
    if smart_click(window, "อ่านบัตรประชาชน", timeout=popup_wait):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> อ่านบัตรแล้ว")
        time.sleep(2) # รอข้อมูลบัตรโหลด
        
        # --- เริ่มขั้นตอนกรอกเบอร์ (เฉพาะเมื่อเจอ Popup) ---
        try:
            phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
            smart_input_phone_popup_logic(window, phone)
        except Exception as e:
            log(f"[!] Error กรอกเบอร์: {e}")

        # กดถัดไป
        smart_click(window, "ถัดไป", timeout=int(5*speed_factor))
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ไปต่อทันที")

def smart_input_weight(window, value, timeout):
    log(f"...กรอกน้ำหนัก: {value}")
    start = time.time()
    while time.time() - start < timeout:
        # ลองหา Edit Box โดยตรง
        try:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                edits[0].click_input()
                edits[0].type_keys(str(value), with_spaces=True)
                log(f"[/] กรอกน้ำหนัก (EditBox)")
                return True
        except: pass
        
        # ลอง Click Label + Tab
        if smart_click(window, "น้ำหนัก", timeout=0.5):
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอกน้ำหนัก (Label+Tab)")
            return True
        
        time.sleep(0.5)
    
    # ถ้าหมดเวลาแล้วยังไม่ได้ ให้ลองพิมพ์เลย
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

    speed_factor = calibrate_system()
    final_timeout = int(base_timeout * speed_factor)
    
    log(f"\n--- เริ่ม Scenario (ซองจดหมาย) Timeout: {final_timeout}s ---")
    time.sleep(1)

    # Step 1: รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ", timeout=final_timeout): return
    time.sleep(step_delay)

    # --- Check Popup (สำคัญ: ถ้ามี Popup ถึงจะกรอกเบอร์) ---
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