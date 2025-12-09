import configparser
import os
import time
import datetime
from pywinauto.application import Application

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    config = configparser.ConfigParser()
    if not os.path.exists(filename): return None
    config.read(filename, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Smart Functions (Adaptive) =================
def smart_click(window, criteria_list, timeout=5, optional=False):
    """
    คลิกปุ่มตามรายการชื่อ (รองรับหลายชื่อ)
    optional=True: ถ้าหาไม่เจอให้ปล่อยผ่าน (ไม่ Error) ใช้สำหรับ Popup ที่อาจจะขึ้นหรือไม่ขึ้นก็ได้
    """
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

def check_sender_popup(window):
    """
    ฟังก์ชันเช็คหน้า 'ผู้ฝากส่ง' (Adaptive)
    - ถ้าเจอ 'อ่านบัตรประชาชน' -> กดให้เลย
    - ถ้าไม่เจอ -> ทำงานต่อทันที (ไม่รอ)
    """
    log("...เช็ค Popup ผู้ฝากส่ง...")
    # ลองหาปุ่มอ่านบัตรประชาชน แบบเร็วๆ (Timeout 2 วินาทีพอ)
    if smart_click(window, "อ่านบัตรประชาชน", timeout=2, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(1) # รอโหลดนิดนึง
        
        # ถ้ากดแล้วต้องกด 'ถัดไป' หรือไม่? (ปกติอ่านบัตรเสร็จอาจจะเด้งไปเอง หรือต้องกดถัดไป)
        # ลองกดถัดไปเผื่อไว้
        smart_click(window, "ถัดไป", timeout=2, optional=True)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def smart_input_weight(window, value):
    """
    ฟังก์ชันกรอกน้ำหนักแบบเจาะจง (แก้ปัญหากรอกไม่ได้)
    """
    log(f"...กำลังกรอกน้ำหนัก: {value}")
    
    # วิธีที่ 1: หา Edit Box โดยตรง (หน้าน้ำหนักมักมี Edit Box ใหญ่ๆ อันเดียว)
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            # เจอ Edit Box! คลิกและพิมพ์เลย
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            log(f"[/] เจอ Edit Box และกรอก '{value}' สำเร็จ")
            return True
    except: pass

    # วิธีที่ 2: ถ้าวิธีแรกไม่ได้ผล ใช้สูตร Click Header + TAB
    log("...หา Edit Box ไม่เจอ ลองสูตร Click+Tab...")
    try:
        # คลิกที่คำว่า "น้ำหนัก" (ที่เป็นหัวข้อ)
        if smart_click(window, "น้ำหนัก", timeout=2, optional=True):
            window.type_keys("{TAB}")
            time.sleep(0.2)
            window.type_keys(str(value), with_spaces=True)
            log(f"[/] กรอก '{value}' ด้วยสูตร Tab สำเร็จ")
            return True
    except: pass

    # วิธีที่ 3: สุดท้ายจริงๆ พิมพ์ Blind Type (เผื่อ Cursor มันกระพริบอยู่แล้ว)
    log("...ลองพิมพ์สด (Blind Type)...")
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_next(window):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

# ================= 3. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE']['Weight']
        postal = config['DEPOSIT_ENVELOPE']['PostalCode']
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except: 
        log("[Error] Config ผิดพลาด")
        return

    log(f"\n--- เริ่มต้น Scenario (ซองจดหมาย - Smart Mode) ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # 2. ซองจดหมาย (รูปร่าง)
    if not smart_click(main_window, "ซองจดหมาย"): return
    time.sleep(step_delay)

    # 3. ซองจดหมาย (หมวดหมู่)
    smart_click(main_window, "ซองจดหมาย", timeout=3, optional=True) 
    time.sleep(step_delay)

    # --- จุดเช็ค Popup ผู้ฝากส่ง (Smart Check) ---
    # จะเช็คตรงนี้ เพราะมักจะถามก่อนเข้าน้ำหนัก หรือก่อนเข้าหน้าซอง
    check_sender_popup(main_window)
    time.sleep(step_delay)

    # 4. น้ำหนัก (New Logic)
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    time.sleep(step_delay)

    # 5. รหัสไปรษณีย์
    # ใช้วิธีพิมพ์เลย เพราะหน้าไปรษณีย์มักจะ Focus ที่ช่องแรกสุดเสมอ
    log(f"...กรอกรหัสไปรษณีย์: {postal}")
    try:
        # หา Edit Box แรกของหน้านี้
        postal_box = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()][0]
        postal_box.click_input()
        postal_box.type_keys(str(postal))
    except:
        # ถ้าหาไม่เจอ พิมพ์สด
        main_window.type_keys(str(postal), with_spaces=True)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. จบงาน (ดำเนินการ/เสร็จสิ้น/Popup ทับซ้อน)
    log("STEP 6: จบงาน")
    
    # เช็ค Popup "พื้นที่รหัสไปรษณีย์ทับซ้อน" (ที่มีปุ่ม ดำเนินการ)
    if smart_click(main_window, "ดำเนินการ", timeout=3, optional=True):
        log("[/] กดปุ่ม 'ดำเนินการ' (Popup ทับซ้อน) สำเร็จ")
    
    # เช็คปุ่มจบงานอื่นๆ
    final_buttons = ["เสร็จสิ้น", "Settle", "ยืนยัน", "ตกลง"]
    smart_click(main_window, final_buttons, timeout=3, optional=True)
    
    # กด Enter ปิดท้ายเพื่อความชัวร์
    main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน")

# ================= 4. Execution =================
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