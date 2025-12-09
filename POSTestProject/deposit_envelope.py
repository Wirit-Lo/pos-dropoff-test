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

# ================= 2. System Calibration (ระบบวัดความเร็วเครื่อง) =================
def get_machine_delay_factor():
    """
    ฟังก์ชันวัดความเร็วเครื่อง (Benchmark)
    เพื่อปรับค่า Timeout ให้เหมาะสมกับความช้า/เร็วของเครื่องอัตโนมัติ
    """
    log("...กำลังตรวจสอบประสิทธิภาพเครื่อง (Calibrating)...")
    start_time = time.time()
    
    # ทดสอบ Loop คำนวณเบาๆ เพื่อวัด CPU Speed
    count = 0
    for i in range(3000000): # วนลูป 3 ล้านรอบ
        count += 1
        
    end_time = time.time()
    duration = end_time - start_time
    
    # เกณฑ์การวัด (Threshold)
    # เครื่องเร็วปกติจะใช้เวลาประมาณ 0.1 - 0.2 วินาที
    if duration > 0.5:
        log(f"[System] เครื่องทำงานหนัก/ช้า ({duration:.2f}s) -> เพิ่มเวลาการรอเป็น 2 เท่า")
        return 2.0
    elif duration > 0.25:
        log(f"[System] เครื่องทำงานปานกลาง ({duration:.2f}s) -> เพิ่มเวลาการรอเป็น 1.5 เท่า")
        return 1.5
    else:
        log(f"[System] เครื่องทำงานเร็ว ({duration:.2f}s) -> ใช้เวลาตาม Config ปกติ")
        return 1.0

# ================= 3. Smart Functions (Adaptive) =================
def force_scroll_down(window, scroll_dist=-20):
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
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                # Deep Search
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
    ฟังก์ชันเช็คหน้า 'ผู้ฝากส่ง'
    ใช้ timeout ที่ผ่านการคำนวณตามความเร็วเครื่องแล้ว
    """
    log(f"...เช็ค Popup ผู้ฝากส่ง (รอสูงสุด {current_timeout} วิ)...")
    
    if smart_click(window, "อ่านบัตรประชาชน", timeout=current_timeout, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1)
        
        try:
            scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -20))
            phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
            
            force_scroll_down(window, scroll_dist)
            log(f"...กรอกเบอร์โทรศัพท์: {phone}")
            
            labels = ["หมายเลขโทรศัพท์", "เบอร์โทรศัพท์", "โทรศัพท์", "เบอร์มือถือ"]
            if smart_click(window, labels, timeout=current_timeout, optional=True):
                window.type_keys("{TAB}")
                time.sleep(0.2)
                window.type_keys(str(phone), with_spaces=True)
                log("[/] กรอกเบอร์เรียบร้อย (สูตร Click Label + Tab)")
            else:
                log("...หา Label ไม่เจอ -> ลองพิมพ์เลย (Blind Type)...")
                window.type_keys(str(phone), with_spaces=True)
                
        except Exception as e:
            log(f"[!] Error ช่วงกรอกเบอร์: {e}")

        smart_click(window, "ถัดไป", timeout=current_timeout, optional=True)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง (ภายในเวลาที่กำหนด) -> ข้ามไปขั้นตอนต่อไป")

def smart_input_weight(window, value, timeout=5):
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    try:
        start = time.time()
        edits = []
        while time.time() - start < timeout:
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits: break
            time.sleep(0.5)

        if edits:
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            log(f"[/] เจอ Edit Box และกรอก '{value}' สำเร็จ")
            return True
    except: pass

    log("...หา Edit Box ไม่เจอ ลองสูตร Click+Tab...")
    try:
        if smart_click(window, "น้ำหนัก", timeout=timeout, optional=True):
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอก '{value}' ด้วยสูตร Tab สำเร็จ")
            return True
    except: pass

    log("...ลองพิมพ์สด (Blind Type)...")
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window, timeout=5):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=timeout, optional=True):
        window.type_keys("{ENTER}")

def wait_for_text(window, text, timeout=10):
    """รอให้ข้อความปรากฏบนหน้าจอ"""
    log(f"...รอข้อความ '{text}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    log(f"[!] รอ '{text}' จนหมดเวลา (อาจจะยังอยู่หน้าเดิม)")
    return False

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
        base_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))
    except: 
        log("[Error] Config ผิดพลาด")
        return

    # --- เริ่มวัดความเร็วเครื่อง และคำนวณ Timeout ใหม่ ---
    speed_factor = get_machine_delay_factor()
    final_timeout = int(base_timeout * speed_factor)
    
    log(f"\n--- เริ่มต้น Scenario (ซองจดหมาย - Smart Mode) ---")
    log(f"Config Timeout: {base_timeout}s | Machine Factor: {speed_factor}x | Final Timeout: {final_timeout}s")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ", timeout=final_timeout): return
    time.sleep(step_delay)

    # --- เช็ค Popup ผู้ฝากส่ง (ใช้ Timeout ที่คำนวณแล้ว) ---
    check_sender_popup(main_window, config, final_timeout)
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย", timeout=final_timeout): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่) --> กด Enter ผ่านไปเลย
    log("STEP 3: กด Enter ผ่านหมวดหมู่")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # 4. น้ำหนัก
    smart_input_weight(main_window, weight, timeout=final_timeout)
    smart_next(main_window, timeout=final_timeout)
    
    # --- รอหน้าจอเปลี่ยนไปหน้า "รหัสไปรษณีย์" ---
    wait_for_text(main_window, "รหัสไปรษณีย์", timeout=final_timeout)
    time.sleep(0.5) 

    # 5. รหัสไปรษณีย์
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        start = time.time()
        edits = []
        while time.time() - start < final_timeout:
            edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
            if edits: break
            time.sleep(0.5)
            
        if edits:
            postal_box = edits[0]
            postal_box.click_input()
            postal_box.type_keys(str(postal))
        else:
            main_window.type_keys(str(postal), with_spaces=True)
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