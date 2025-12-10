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
    """
    [Updated V5] ฟังก์ชันช่วยเลื่อนหน้าจอลง (Mouse Scroll with Config)
    แก้ไข: รับค่า scroll_dist เพื่อกำหนดระยะการหมุนได้ (ค่าลบ = ลง, ค่าบวก = ขึ้น)
    """
    log(f"...สั่งเลื่อนหน้าจอลง (Scroll Distance: {scroll_dist})...")
    try:
        # 1. เรียก Focus มาที่หน้าต่าง
        window.set_focus()
        
        # 2. คำนวณตำแหน่ง Scrollbar (จุดที่ปลอดภัยสำหรับการ Scroll)
        rect = window.rectangle()
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        
        # 3. คลิก 1 ครั้งเพื่อเรียก Focus ที่จุดนั้นก่อน
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        time.sleep(0.5)
        
        # 4. ใช้คำสั่ง Mouse Scroll ตามระยะที่ส่งมา
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(1) # รอให้ภาพขยับเสร็จ
        
    except Exception as e:
        log(f"[!] Scroll Error: {e}")
        # กันเหนียว: ถ้าเมาส์พัง ให้กดปุ่ม Page Down แทน
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

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    """
    [Updated V4] คลิกปุ่มแบบเลื่อนหา (Strict Bounds Check)
    เพิ่ม: Safety Margin 150px เพื่อกันไม่ให้คลิกโดนแถบ Footer ด้านล่าง
    """
    log(f"...กำลังค้นหาปุ่ม '{criteria}' (โหมดเลื่อนหา)...")
    
    for i in range(max_scrolls + 1):
        found_element = None
        
        # 1. พยายามค้นหา Element ในหน้าจอปัจจุบัน
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found_element = child
                    break
        except: pass

        # 2. ถ้าเจอ Element -> เช็คตำแหน่งอย่างละเอียดก่อนกด
        if found_element:
            try:
                elem_rect = found_element.rectangle()
                win_rect = window.rectangle()
                
                # [New Logic] กำหนดเส้นตาย (Dead Zone) ด้านล่าง
                # เผื่อไว้ 150 pixel สำหรับแถบ Footer สีฟ้า/เทา ด้านล่าง
                safe_bottom_limit = win_rect.bottom - 150 
                
                # เช็คว่าขอบล่างของปุ่ม อยู่ต่ำกว่าเส้นตายหรือไม่
                if elem_rect.bottom >= safe_bottom_limit:
                    log(f"   [!] เจอปุ่ม '{criteria}' แต่อยู่ต่ำเกินไป (ติด Footer) -> สั่งเลื่อนลงเพื่อให้เห็นเต็มกล่อง")
                    force_scroll_down(window, scroll_dist)
                    time.sleep(1)
                    continue # วนลูปใหม่ เพื่อหาปุ่มในตำแหน่งใหม่ที่ขยับขึ้นมาแล้ว
                
                # ถ้าตำแหน่ง OK (อยู่สูงกว่า Footer) -> กดเลย
                found_element.click_input()
                log(f"   [/] เจอและกดปุ่ม '{criteria}' สำเร็จ (ตำแหน่งปลอดภัย)")
                return True
                
            except Exception as e:
                log(f"   [!] เจอแต่กดไม่ได้ ({e}) -> ลองเลื่อนต่อ")

        # 3. ถ้าไม่เจอ หรือ เจอแต่ตกขอบแล้วสั่งเลื่อนไปแล้ว -> วนรอบถัดไป
        if i < max_scrolls:
            if not found_element:
                log(f"   [Rotate {i+1}/{max_scrolls}] ยังไม่เจอ '{criteria}' -> สั่งเลื่อนลง")
                force_scroll_down(window, scroll_dist)
                time.sleep(1)
            
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

def smart_input_with_scroll(window, label_text, value, scroll_times=2, scroll_dist=-5):
    """
    ฟังก์ชันกรอกข้อมูลที่รองรับการเลื่อนหน้าจอ (รับค่า Scroll Distance)
    """
    log(f"...กำลังพยายามกรอก '{label_text}': {value}")

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
            force_scroll_down(window, scroll_dist)
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

    if smart_click(window, "อ่านบัตรประชาชน", timeout=5, optional=True):
        log("[Popup] เจอหน้าผู้ฝากส่ง -> กดอ่านบัตรเรียบร้อย")
        time.sleep(3) 

        log("...ตรวจสอบช่องรหัสไปรษณีย์...")
        try:
            found_postal_box = False
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    current_val = edit.get_value() 
                    if current_val is None or str(current_val).strip() == "":
                        log(f"   [Auto-Fix] รหัสไปรษณีย์ว่างเปล่า -> กำลังเติมค่า Config: {default_postal}")
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    else:
                        log(f"   [Skip] มีรหัสไปรษณีย์แล้ว ({current_val}) -> ไม่ต้องเติม")
                    found_postal_box = True
                    break 
            
            if not found_postal_box:
                log("   [!] หาช่องรหัสไปรษณีย์แบบระบุชื่อไม่เจอ (ข้ามขั้นตอนซ่อมแซม)")

        except Exception as e:
            log(f"   [Error] เกิดข้อผิดพลาดตอนเช็ค ปณ.: {e}")

        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        
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
    Logic: กดขวา 2 ที ({RIGHT}{RIGHT}) เพื่อไปหายืนยัน แล้วกด Enter ({ENTER})
    """
    log("...รอตรวจสอบหน้าสิ่งของต้องห้าม (Prohibited Items)...")
    
    if wait_for_text(window, "สิ่งของต้องห้าม", timeout=5):
        log("[Detect] พบหน้า 'สิ่งของต้องห้าม' -> (Default Focus: ปฏิเสธ)")
        time.sleep(1) 
        
        log("   [Action] กดลูกศรขวา 2 ครั้ง (Move Focus >> Confirm)")
        window.type_keys("{RIGHT}{RIGHT}")
        time.sleep(0.5)
        
        log("   [Action] กด Enter เพื่อยืนยัน")
        window.type_keys("{ENTER}")
        time.sleep(1) 
        
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
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = int(config['SETTINGS'].get('StepDelay', 1))
        
        # [NEW] อ่านค่า ScrollDistance จาก Config (ถ้าไม่มีให้ใช้ -5 เป็นค่า Default)
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        
    except Exception as e: 
        log(f"[Error] Config ผิดพลาด: {e}")
        return

    log(f"\n--- เริ่มต้น Scenario (Options: {special_options_str}) Phone: {phone} ---")
    log(f"--- Scroll Distance setting: {scroll_dist} ---")
    time.sleep(1)

    # 1. รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    # --- ขั้นตอนผู้ฝากส่ง ---
    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    # 2. เลือกกล่อง (ใช้ฟังก์ชันใหม่ คลิก+เลื่อนหา + ส่งค่า Scroll จาก Config)
    if not smart_click_with_scroll(main_window, "กล่องสำเร็จรูปแบบ ง.", scroll_dist=scroll_dist): 
        log("[Error] หา 'กล่องสำเร็จรูปแบบ ง.' ไม่เจอ แม้เลื่อนจอแล้ว")
        return
    time.sleep(step_delay)

    # --- STEP 3: เลือกหมวดหมู่ / ลักษณะเฉพาะ ---
    log("STEP 3: เลือกหมวดหมู่/ลักษณะเฉพาะ")
    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        log(f"...กำลังเลือกรายการพิเศษ: {options}")
        for opt in options:
            if opt: 
                smart_click(main_window, opt, timeout=2, optional=True)
                time.sleep(0.5)
    else:
        log("...ไม่มีการระบุลักษณะเฉพาะ (ข้าม)")

    log("...กด Enter เพื่อไปหน้าถัดไป")
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    # จัดการหน้าสิ่งของต้องห้าม
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
    
    # [NEW] ปิดการกด Enter อัตโนมัติ เพื่อให้หน้าจอค้างไว้ให้ดูผลลัพธ์
    # main_window.type_keys("{ENTER}")

    log("\n[SUCCESS] จบการทำงาน - ระบบค้างหน้าจอนี้ไว้")
    print("\n>>> กด Enter ที่หน้าต่างนี้ (Console) เพื่อปิดโปรแกรม... <<<")
    input() # หยุดรอ Input จากผู้ใช้

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