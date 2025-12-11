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
    [Updated V6] ฟังก์ชันช่วยเลื่อนหน้าจอลง
    - ปรับลด delay ให้ทำงานไวขึ้นตามคำขอ
    """
    # log(f"...สั่งเลื่อนหน้าจอ (Dist: {scroll_dist})...") # ปิด Log รกๆ
    try:
        window.set_focus()
        rect = window.rectangle()
        # จุดหมุน Mouse อยู่ค่อนไปทางขวา (กันโดนปุ่มกลางจอ)
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        
        mouse.click(coords=(scrollbar_x, scrollbar_y))
        # time.sleep(0.1) # ตัด delay ออกเพื่อความไว
        
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.5) # ลดจาก 1.0 เหลือ 0.5 เพื่อความไว
        
    except Exception as e:
        log(f"[!] Scroll Error: {e}")
        window.type_keys("{PGDN}")

def smart_click(window, criteria_list, timeout=5, optional=False):
    """คลิกปุ่มตามรายการชื่อ (พื้นฐาน)"""
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
        time.sleep(0.3) # ลด delay การวนหา

    if not optional:
        log(f"[X] หาปุ่ม {criteria_list} ไม่เจอ!")
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    """
    [Updated V6 - Fast & Accurate] 
    1. ลด Safe Zone เหลือ 70px (เพื่อให้กดปุ่มล่างๆ ได้เลย ไม่ต้องเลื่อน)
    2. ถ้าต้องเลื่อนขยับ (Nudge) ให้เลื่อนแค่ -4 พอ (กันปุ่มกระเด็นหาย)
    """
    log(f"...ค้นหา '{criteria}' (โหมดเลื่อนหาไว)...")
    
    for i in range(max_scrolls + 1):
        found_element = None
        
        # 1. กวาดหา Element ในหน้าจอ
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found_element = child
                    break
        except: pass

        # 2. ถ้าเจอ -> เช็คตำแหน่ง
        if found_element:
            try:
                elem_rect = found_element.rectangle()
                win_rect = window.rectangle()
                
                # [FIX 1] ลดพื้นที่กันชนด้านล่างลง (จาก 150 เหลือ 70) 
                # ปุ่มอยู่ล่างแค่ไหนก็กดได้ ตราบใดที่ไม่ทับกับ Footer จริงๆ
                safe_bottom_limit = win_rect.bottom - 70 
                
                # เช็คว่าปุ่มอยู่ต่ำกว่าเส้นตายหรือไม่
                if elem_rect.bottom >= safe_bottom_limit:
                    log(f"   [!] เจอปุ่ม '{criteria}' แต่อยู่ต่ำมาก (ติดขอบล่าง) -> ขยับนิดเดียว")
                    
                    # [FIX 2] บังคับเลื่อนแค่ -4 พอ (Nudge) ไม่ใช้ค่า scroll_dist ที่อาจจะเยอะเกินไป
                    # เพื่อป้องกันปุ่มเลื่อนเลยขึ้นไปข้างบนจนหาไม่เจอ
                    force_scroll_down(window, -4)
                    time.sleep(0.3) # รอแป๊บเดียวแล้วหาใหม่เลย
                    continue 
                
                # ถ้าตำแหน่ง OK -> กดเลย
                found_element.click_input()
                log(f"   [/] เจอและกดปุ่ม '{criteria}' สำเร็จ")
                return True
                
            except Exception as e:
                log(f"   [!] เจอแต่กดไม่ได้ ({e}) -> ลองเลื่อนต่อ")

        # 3. ถ้าไม่เจอเลย -> เลื่อนหาหน้าถัดไป (ใช้ค่า scroll_dist ตาม Config ได้เลยเพื่อความไว)
        if i < max_scrolls:
            if not found_element:
                log(f"   [Rotate {i+1}] ไม่เจอ '{criteria}' -> เลื่อนหา (Scroll)")
                force_scroll_down(window, scroll_dist)
            
    log(f"[X] หมดความพยายามในการหาปุ่ม '{criteria}'")
    return False

# ================= 3. Smart Input Functions =================
def smart_input_weight(window, value):
    log(f"...กรอกน้ำหนัก: {value}")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            target_box = edits[0]
            target_box.click_input()
            target_box.type_keys(str(value), with_spaces=True)
            return True
    except: pass
    window.type_keys(str(value), with_spaces=True)
    return True

def smart_input_with_scroll(window, label_text, value, scroll_times=2, scroll_dist=-5):
    log(f"...กรอก '{label_text}': {value}")
    for i in range(scroll_times + 1):
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if edit.is_visible() and (label_text in edit.element_info.name or label_text in edit.window_text()):
                    edit.set_focus()
                    edit.click_input()
                    edit.type_keys(str(value), with_spaces=True)
                    log(f"[/] กรอกสำเร็จ")
                    return True
            
            labels = [c for c in window.descendants(control_type="Text") if label_text in c.window_text() and c.is_visible()]
            if labels:
                labels[0].click_input()
                window.type_keys("{TAB}")
                time.sleep(0.1)
                window.type_keys(str(value), with_spaces=True)
                return True
        except: pass

        if i < scroll_times:
            force_scroll_down(window, scroll_dist)
            time.sleep(0.5)

    return False

def smart_next(window):
    if not smart_click(window, "ถัดไป", timeout=2, optional=True):
        window.type_keys("{ENTER}")

def process_sender_info(window, phone_number, default_postal):
    log("...เช็คหน้า Popup ผู้ฝากส่ง...")
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3, optional=True): # ลด timeout
        log("[Popup] กดอ่านบัตรเรียบร้อย")
        time.sleep(2) # ลดเวลาอ่านบัตร

        try:
            found_postal_box = False
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name or "รหัสไปรษณีย์" in edit.window_text():
                    current_val = edit.get_value() 
                    if current_val is None or str(current_val).strip() == "":
                        edit.click_input()
                        edit.type_keys(str(default_postal), with_spaces=True)
                    found_postal_box = True
                    break 
        except: pass

        smart_input_with_scroll(window, "หมายเลขโทรศัพท์", phone_number)
        smart_next(window)

def wait_for_text(window, text, timeout=5): # ลด timeout default
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if text in child.window_text() and child.is_visible():
                    return True
        except: pass
        time.sleep(0.3)
    return False

def handle_prohibited_items_warning(window):
    log("...เช็คสิ่งของต้องห้าม...")
    if wait_for_text(window, "สิ่งของต้องห้าม", timeout=3):
        window.type_keys("{RIGHT}{RIGHT}")
        time.sleep(0.2)
        window.type_keys("{ENTER}")
        time.sleep(0.5) 
    else:
        log("[Skip] ไม่เจอหน้าสิ่งของต้องห้าม")

# ================= 4. Main Scenario =================
def run_smart_scenario(main_window, config):
    try:
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        postal = config['DEPOSIT_ENVELOPE'].get('PostalCode', '10110')
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.5)) # บังคับ float
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
    except: return

    log(f"--- เริ่มต้น (Scroll: {scroll_dist}) ---")
    time.sleep(0.5)

    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)

    process_sender_info(main_window, phone, postal) 
    time.sleep(step_delay)

    # [จุดที่แก้ไข] เลือกกล่องด้วย logic ใหม่
    if not smart_click_with_scroll(main_window, "กล่องสำเร็จรูปแบบ ฉ.", scroll_dist=scroll_dist): 
        log("[Error] หา 'กล่องสำเร็จรูปแบบ ฉ.' ไม่เจอ")
        return
    time.sleep(step_delay)

    if special_options_str.strip():
        options = [opt.strip() for opt in special_options_str.split(',')]
        for opt in options:
            if opt: smart_click(main_window, opt, timeout=1, optional=True)
    
    main_window.type_keys("{ENTER}")
    time.sleep(step_delay)

    handle_prohibited_items_warning(main_window)
    
    smart_input_weight(main_window, weight)
    smart_next(main_window)
    
    
    wait_for_text(main_window, "รหัสไปรษณีย์")
    
    try:
        main_window.type_keys(str(postal), with_spaces=True)
    except: pass
    
    smart_next(main_window)
    time.sleep(step_delay)

    smart_click(main_window, "ดำเนินการ", timeout=2, optional=True)
    smart_click(main_window, ["เสร็จสิ้น", "Settle", "ยืนยัน"], timeout=2, optional=True)
    
    log("\n[SUCCESS] จบการทำงาน")
    print(">>> กด Enter เพื่อปิดโปรแกรม... <<<")
    input()

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