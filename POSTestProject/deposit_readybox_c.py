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
        # หาจุดกลางหน้าจอเพื่อวางเมาส์
        center_x = rect.left + 300
        center_y = rect.top + 300
        
        # คลิกเพื่อให้หน้าจอ Focus ก่อนเลื่อน
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.5)
        # สั่งเลื่อนเมาส์
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(1)
    except Exception as e:
        log(f"[!] Mouse scroll failed: {e}")
        # ถ้าใช้เมาส์ไม่ได้ ให้ลองกดปุ่ม Page Down แทน
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ (รองรับหลายชื่อ)"""
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                # Deep Search หาปุ่มหรือ Element ที่มีชื่อตรงกับ criteria
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

def smart_click_with_scroll(window, criteria, max_scrolls=3):
    """
    [New Function] คลิกปุ่มแบบเลื่อนหา (สำหรับปุ่มที่อยู่ด้านล่างจอ)
    """
    log(f"...กำลังค้นหาปุ่ม '{criteria}' (พร้อมเลื่อนจอ)...")
    
    for i in range(max_scrolls + 1):
        # ลองใช้ smart_click แบบเร็ว (timeout สั้นๆ)
        if smart_click(window, criteria, timeout=2, optional=True):
            return True
            
        # ถ้าหาไม่เจอ และยังไม่ครบจำนวนรอบ ให้เลื่อนจอลง
        if i < max_scrolls:
            log(f"[Rotate {i+1}] ยังหาปุ่ม '{criteria}' ไม่เจอ -> เลื่อนจอลง")
            force_scroll_down(window, scroll_dist=-5) # เลื่อนลง
            time.sleep(1) # รอให้หน้าจอนิ่ง
            
    log(f"[X] หมดความพยายามในการหาปุ่ม '{criteria}'")
    return False

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value):
    """ฟังก์ชันกรอกน้ำหนัก"""
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
    
    # Fallback methods: พิมพ์ค่าลงไปเลย
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2):
    """
    ฟังก์ชันกรอกข้อมูลที่รองรับการเลื่อนหน้าจอ (สำหรับเบอร์โทร หรือช่องที่อยู่ด้านล่าง)
    """
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")

    # ลองหา 2-3 รอบ (รอบแรกหาเลย, รอบต่อไปลอง Scroll แล้วหา)
    for i in range(scroll_times + 1):
        try:
            # 1. พยายามหา Edit Box โดยตรงจากชื่อ
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    log(f"[/] กรอก {label_text} สำเร็จ (Found by Name)")
                    return True
            
            # 2. ถ้าหา Edit ไม่เจอ ลองหา Text Label แล้วกด Tab
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                log(f"[/] เจอ Label '{label_text}' -> กำลังกด Tab เพื่อเข้าช่องกรอก")
                labels[0].click_input() # คลิกที่ข้อความก่อน
                window.type_keys("{TAB}") # กด Tab เพื่อไปช่อง Input ถัดไป
                time.sleep(0.2)
                window.type_keys(str(value), with_spaces=True)
                return True

        except Exception as e:
            log(f"[!] Error finding input: {e}")

        # ถ้ายังไม่เจอ ให้เลื่อนจอลง
        if i < scroll_times:
            log(f"[Rotate {i+1}] หาช่องไม่เจอ... กำลังเลื่อนหน้าจอลง...")
            force_scroll_down(window, scroll_dist=-5)
            time.sleep(1)

    log(f"[X] หมดความพยายามในการหาช่อง '{label_text}'")
    return False

def smart_next(window):
    """กดถัดไป หรือ Enter"""
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number, default_postal):
    """
    ฟังก์ชันจัดการหน้าผู้ฝากส่ง: 
    1. อ่านบัตร 
    2. เช็คปณ. (ถ้าว่างให้เติม) 
    3. กรอกเบอร์ -> กดถัดไป
    """
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")

    # 1. กดปุ่มอ่านบัตรประชาชน
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        
        # รอให้ข้อมูลจากบัตรวิ่งลงช่อง (เพิ่มเวลาหน่อยเพื่อให้ชัวร์)
        time.sleep(3) 

        # ---------------------------------------------------------
        # 2. ส่วนที่เพิ่ม: ตรวจสอบและเติมรหัสไปรษณีย์ (ถ้าว่าง)
        # ---------------------------------------------------------
        log("...ตรวจสอบช่องรหัสไปรษณีย์...")
        try:
            found_postal_box = False
            # ค้นหาช่อง Edit ทั้งหมดในหน้านั้น
            edits = window.descendants(control_type="Edit")
            
            for edit in edits:
                # ตรวจสอบชื่อของช่องว่าใช่ "รหัสไปรษณีย์" หรือไม่
                # (บางทีชื่ออาจจะเป็น "ZipCode" หรือ "PostCode" แล้วแต่โปรแกรม แต่ส่วนใหญ่จะใช้ชื่อภาษาไทยตาม Label)
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    
                    # ดึงค่าปัจจุบันในช่องออกมาดู (สำหรับ UIA Backend ใช้ get_value)
                    current_val = edit.get_value() 
                    
                    if current_val is None or str(current_val).strip() == "":
                        log(f"   [Auto-Fix] รหัสไปรษณีย์ว่างเปล่า -> กำลังเติมค่า Config: {default_postal}")
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    else:
                        log(f"   [Skip] มีรหัสไปรษณีย์แล้ว ({current_val}) -> ไม่ต้องเติม")
                    
                    found_postal_box = True
                    break # เจอแล้ว ออกจาก Loop
            
            if not found_postal_box:
                log("   [!] หาช่องรหัสไปรษณีย์แบบระบุชื่อไม่เจอ (ข้ามขั้นตอนซ่อมแซม)")

        except Exception as e:
            log(f"   [Error] เกิดข้อผิดพลาดตอนเช็ค ปณ.: {e}")
        # ---------------------------------------------------------

        # 3. กรอกเบอร์โทรศัพท์ต่อ (ตามปกติ)
        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        
        # 4. กดถัดไป
        log("...ข้อมูลครบถ้วน กดถัดไป...")
        smart_next(window)
    else:
        log("[Popup] ไม่เจอหน้าผู้ฝากส่ง -> ข้ามไปขั้นตอนต่อไป")

def wait_for_text(window, text, timeout=10):
    """รอให้ข้อความปรากฏ (ใช้เช็คการเปลี่ยนหน้า)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.5)
    return False

def handle_prohibited_items_warning(window):
    """
    [Updated V3 - Key Sequence] ฟังก์ชันจัดการหน้า 'สิ่งของต้องห้าม'
    Logic:
    1. รอตรวจจับหน้า 'สิ่งของต้องห้าม'
    2. เนื่องจาก Focus อยู่ที่ปุ่มปฏิเสธ -> กดขวา 2 ที ({RIGHT}{RIGHT}) เพื่อไปหายืนยัน
    3. กด Enter ({ENTER})
    """
    log("...รอตรวจสอบหน้าสิ่งของต้องห้าม (Prohibited Items)...")
    
    # 1. รอตรวจจับว่าหน้า 'สิ่งของต้องห้าม' เด้งขึ้นมาจริงหรือไม่ (Timeout 5 วิ)
    if wait_for_text(window, "สิ่งของต้องห้าม", timeout=5):
        log("[Detect] พบหน้า 'สิ่งของต้องห้าม' -> (Default Focus: ปฏิเสธ)")
        time.sleep(1) # รอให้หน้าจอพร้อมรับ Input (สำคัญมาก)
        
        # 2. กดปุ่มลูกศรขวา 2 ครั้ง เพื่อเลื่อนไปหาปุ่มยืนยัน
        log("   [Action] กดลูกศรขวา 2 ครั้ง (Move Focus >> Confirm)")
        window.type_keys("{RIGHT}{RIGHT}")
        time.sleep(0.5) # พักนิดนึงให้ Focus เปลี่ยน
        
        # 3. กด Enter
        log("   [Action] กด Enter เพื่อยืนยัน")
        window.type_keys("{ENTER}")
        time.sleep(1) # รอผลลัพธ์
        
        # เช็คว่าผ่านจริงไหม (Optional)
        if not wait_for_text(window, "สิ่งของต้องห้าม", timeout=1):
            log("   [/] Success: หน้าสิ่งของต้องห้ามหายไปแล้ว")
        else:
            log("   [Warning] หน่ายังค้างอยู่ (อาจต้องเช็คจังหวะการกดอีกครั้ง)")

    else:
        log("[Skip] ไม่พบหน้าแจ้งเตือนสิ่งของต้องห้าม (ภายใน 5 วินาที) -> ข้ามไปขั้นตอนถัดไป")

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        # อ่านค่าจาก Config
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        # อ่านค่าลักษณะเฉพาะ (SpecialOptions) เช่น "LQ, FR"
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        
        # อ่านเบอร์โทรจาก TEST_DATA
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
    except Exception as e: 
        log(f"[Error] Config ผิดพลาด: {e}")
        return

    log(f"\n--- เริ่มต้น Scenario (Options: {special_options_str}) Phone: {phone} ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # --- ขั้นตอนผู้ฝากส่ง (อ่านบัตร + กรอกเบอร์) ---
    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    # 2. เลือกกล่อง (ใช้ฟังก์ชันใหม่ คลิก+เลื่อนหา)
    # เปลี่ยนเป้าหมายเป็น "กล่องสำเร็จรูปแบบ ค." (ซึ่งมักอยู่ด้านล่าง)
    if not smart_click_with_scroll(main_window, "กล่องสำเร็จรูปแบบ ค."): 
        log("[Error] หา 'กล่องสำเร็จรูปแบบ ค.' ไม่เจอ แม้เลื่อนจอแล้ว")
        return
    time.sleep(step_delay)

    # --- STEP 3: เลือกหมวดหมู่ / ลักษณะเฉพาะ ตาม Config ---
    log("STEP 3: เลือกหมวดหมู่/ลักษณะเฉพาะ")
    
    # ตรวจสอบว่าใน Config มีค่าหรือไม่
    if special_options_str.strip():
        # แยกข้อความด้วยเครื่องหมายคอมมา (,) เช่น "LQ, FR" -> ["LQ", "FR"]
        options = [opt.strip() for opt in special_options_str.split(',')]
        
        log(f"...กำลังเลือกรายการพิเศษ: {options}")
        for opt in options:
            if opt: # ป้องกันค่าว่าง
                # พยายามกดปุ่มที่มีข้อความตรงกับ Config
                smart_click(main_window, opt, timeout=2, optional=True)
                time.sleep(0.5)
    else:
        log("...ไม่มีการระบุลักษณะเฉพาะ (ข้าม)")

    # กด Enter เพื่อไปต่อ (ต้องกดเสมอเพื่อผ่านหน้านี้)
    log("...กด Enter เพื่อไปหน้าถัดไป")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # เรียกใช้ฟังก์ชันจัดการหน้าสิ่งของต้องห้าม (แบบกด Key: Right x2 -> Enter)
    handle_prohibited_items_warning(main_window)
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
    
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. จบงาน
    log("STEP 6: จบงาน")
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