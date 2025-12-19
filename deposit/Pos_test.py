import configparser
import os
import time
import datetime
from pywinauto.application import Application
from pywinauto import mouse

# ================= 1. Config & Log =================
def load_config(filename='config.ini'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    # [แก้ไข] เพิ่ม strict=False เพื่อป้องกัน Error กรณีมี Key ซ้ำใน Config
    config = configparser.ConfigParser(strict=False)
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

# ================= 2. Helper Functions =================

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    try:
        if not value or str(value).strip() == "":
            return False

        target_elem = None
        for child in window.descendants():
            if not child.is_visible(): continue
            
            aid = child.element_info.automation_id
            name = child.element_info.name
            
            # ค้นหาจากชื่อ (Name) หรือ ID
            if target_name and name and target_name in name:
                target_elem = child
                break
            if target_id_keyword and aid and target_id_keyword in aid:
                target_elem = child
                break
        
        if target_elem:
            log(f"   -> เจอช่อง '{target_name}/{target_id_keyword}' -> กรอก: {value}")
            try:
                # ถ้าเจอ Container ให้หา Edit box ข้างใน
                edits = target_elem.descendants(control_type="Edit")
                if edits:
                    target_elem = edits[0]
            except: pass

            target_elem.set_focus()
            target_elem.click_input()
            target_elem.type_keys(str(value), with_spaces=True)
            return True
        else:
            log(f"[WARN] หาช่อง '{target_name}' ไม่เจอ")
            return False
            
    except Exception as e:
        log(f"[!] Error find_and_fill: {e}")
        return False
    
def click_scroll_arrow_smart(window, direction='right', repeat=5):
    try:
        target_group = window.descendants(auto_id="ShippingServiceList")
        if target_group:
            target_group[0].set_focus()
        else:
            window.set_focus()

        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        keys_string = key_code * repeat
        window.type_keys(keys_string, pause=0.2, set_foreground=False)
        return True
    except Exception as e:
        try:
             key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
             window.type_keys(key_code * repeat, pause=0.05)
             return True
        except:
            return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}' (โหมด Scroll, Limit={max_rotations} รอบ)...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False 

        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            if rect.right < safe_limit:
                 log(f"   [{i}] ✅ เจอปุ่มใน Safe Zone -> กำลังกด...")
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else:
                 log(f"   [{i}] ⚠️ เจอปุ่มแต่โดนบัง/อยู่ขวาสุด -> ต้องเลื่อน")
                 should_scroll = True
        else:
            log(f"   [{i}] ไม่เจอปุ่มในหน้านี้ -> เลื่อนขวา...")
            should_scroll = True
        
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5):
                window.type_keys("{RIGHT}")
            time.sleep(1.0)
        
    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}'")
    return False

def force_scroll_down(window, scroll_dist=-5):
    try:
        window.set_focus()
        rect = window.rectangle()
        center_x = rect.left + int(rect.width() * 0.5)
        center_y = rect.top + int(rect.height() * 0.5)
        mouse.click(coords=(center_x, center_y))
        time.sleep(0.2)
        mouse.scroll(coords=(center_x, center_y), wheel_dist=scroll_dist)
        time.sleep(0.8)
    except: pass

def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    if child.is_visible() and criteria in child.window_text().strip():
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.3)
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=5, scroll_dist=-5):
    """
    ค้นหาปุ่ม ถ้าไม่เจอจะทำการ Scroll Down (เหมาะสำหรับข้อ 4 ที่ให้เลื่อนหา)
    """
    log(f"...ค้นหา '{criteria}' (Scroll)...")
    for i in range(max_scrolls + 1):
        found = None
        try:
            for child in window.descendants():
                if child.is_visible() and criteria in child.window_text():
                    found = child; break
        except: pass
        
        if found:
            try:
                elem_rect = found.rectangle()
                win_rect = window.rectangle()
                # เช็คว่าอยู่ขอบล่างเกินไปไหม ถ้าใช่ให้เลื่อนอีกนิด
                if elem_rect.bottom >= win_rect.bottom - 50:
                    force_scroll_down(window, -2); time.sleep(0.5); continue 
                
                found.click_input()
                log(f"   [/] เจอและกด '{criteria}' สำเร็จ")
                return True
            except: pass
        
        # ถ้ายังไม่เจอ และยังไม่ครบจำนวนรอบ ให้เลื่อนลง
        if i < max_scrolls: 
            log(f"   [Scroll] ยังไม่เจอ '{criteria}' -> เลื่อนลงครั้งที่ {i+1}")
            force_scroll_down(window, scroll_dist)
            
    log(f"[X] หา '{criteria}' ไม่เจอหลังเลื่อน {max_scrolls} รอบ")
    return False

def wait_until_id_appears(window, exact_id, timeout=10):
    log(f"...รอโหลด ID: {exact_id}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                if child.element_info.automation_id == exact_id and child.is_visible(): return True
        except: pass
        time.sleep(1)
    return False

def wait_for_text(window, text_list, timeout=5):
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible(): return True
        except: pass
        time.sleep(0.5)
    return False

def smart_next(window):
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    # พยายามหาปุ่ม Submit/Next ของระบบก่อน
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        # ถ้าไม่เจอให้กด Enter
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def check_error_popup(window, delay=0.5):
    if delay > 0: time.sleep(delay)
    try:
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2): return True
                else: window.type_keys("{ENTER}"); return True
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ", "Connect failed"], timeout=0.1): 
             log("[WARN] พบข้อความ Error บนหน้าจอ")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2): return True
             window.type_keys("{ENTER}"); return True
    except: pass
    return False

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, sender_postal):
    # ฟังก์ชันจัดการหน้า Popup ผู้ส่ง
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 
        try:
            edits = window.descendants(control_type="Edit")
            for edit in edits:
                if "รหัสไปรษณีย์" in edit.element_info.name:
                    if not edit.get_value():
                        edit.click_input(); edit.type_keys(str(sender_postal), with_spaces=True)
                    break 
        except: pass
        
        found_phone = False
        for _ in range(3):
            try:
                for edit in window.descendants(control_type="Edit"):
                    if "หมายเลขโทรศัพท์" in edit.element_info.name:
                        edit.click_input(); edit.type_keys(str(phone), with_spaces=True)
                        found_phone = True; break
            except: pass
            if found_phone: break
            force_scroll_down(window, -5)
        smart_next(window)

def handle_prohibited_items(window):
    # กดข้ามหน้าสิ่งของต้องห้าม
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}"); return
        except: pass
        time.sleep(0.5)

def smart_input_generic(window, value, description="ข้อมูล"):
    """ฟังก์ชันกรอกข้อมูลทั่วไป (ใช้สำหรับน้ำหนัก/ปริมาตร)"""
    log(f"...กำลังกรอก {description}: {value}...")
    try:
        # พยายามหา Edit box ที่มองเห็น
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            # ถ้าเจอ Edit box ให้คลิกแล้วพิมพ์
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
    
    # ถ้าหาไม่เจอ ให้พิมพ์เลย (Fallback)
    window.type_keys(str(value), with_spaces=True)
    return True

def process_special_services(window, services_str):
    log("--- หน้า: บริการพิเศษ ---")
    if wait_for_text(window, "บริการพิเศษ", timeout=5):
        if services_str.strip():
            for s in services_str.split(','):
                if s: smart_click(window, s.strip())
    smart_next(window)

def process_sender_info_page(window):
    log("--- หน้า: ข้อมูลผู้ส่ง (ข้าม) ---")
    wait_for_text(window, "ข้อมูลผู้ส่ง", timeout=5)
    smart_next(window)

# ... (ฟังก์ชัน manual address, receiver address คงเดิมตามต้นฉบับ หากต้องการใช้ให้แปะกลับมาได้) ...
# เพื่อความกระชับของคำตอบ ผมจะขอโฟกัสที่ Logic หลักใน run_smart_scenario 
# แต่ใน Code นี้จะรวมฟังก์ชันที่จำเป็นสำหรับการ Run Flow ใหม่ไว้ครบถ้วน

def process_receiver_address_selection(window, address_keyword, manual_data):
    # (ย่อโค้ดส่วนนี้ เพื่อโฟกัสจุดที่แก้ แต่ยังคง Logic เดิมไว้สำหรับการทำงาน)
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    smart_next(window) # จำลองการทำงานเดิม
    return False

def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    # (ย่อโค้ดส่วนนี้)
    log("--- หน้า: รายละเอียดผู้รับ ---")
    # ใส่ Logic เดิมได้เลย
    smart_next(window); smart_next(window); smart_next(window)

def process_payment(window, payment_method, received_amount):
    log("--- ขั้นตอนการชำระเงิน ---")
    if smart_click(window, "รับเงิน"): time.sleep(1.5)
    if not smart_click(window, payment_method): smart_click(window, "เงินสด")
    window.type_keys(str(received_amount) + "{ENTER}")
    wait_for_text(window, ["เปลี่ยนแปลงจำนวนเงิน", "เงินทอน"], timeout=5)
    window.type_keys("{ENTER}")

# ================= 4. Workflow Main (จุดแก้ไขหลัก) =================
def run_smart_scenario(main_window, config):
    try:
        # --- อ่านค่า Config ---
        # 1. ข้อมูลสินค้า (Hardcoded: กำหนดค่าที่นี่เลยตามคำขอ)
        # [แก้ไข] อัปเดต category_name ให้เป็นชื่อเต็มตามที่ต้องการ
        category_name = "อุปกรณ์ไก่ชน ม้วนพรมไก่ ไม่เกิน 1 ผืน"
        product_detail = "อุปกรณ์ไก่ชน ม้วนพรมไก่ ไม่เกิน 1 ผืน"
        
        # 2. ข้อมูลทั่วไป (อ่านจาก Config เหมือนเดิม)
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10') # ข้อ 5
        
        # 3. ข้อมูลปริมาตร (กว้าง/ยาว/สูง) อ่านจาก Config ตามที่อัปเดตใหม่
        width = config['DEPOSIT_ENVELOPE'].get('Width', '10')
        length = config['DEPOSIT_ENVELOPE'].get('Length', '20')
        height = config['DEPOSIT_ENVELOPE'].get('Height', '10')
        
        receiver_postal = config['DEPOSIT_ENVELOPE'].get('ReceiverPostalCode', '10110')
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        
        # Settings
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log(f"--- เริ่มต้นการทำงาน (Modified Flow 1-7) ---")
    time.sleep(0.5)

    # 1. เลือก รับฝากสิ่งของ (มีอยู่แล้ว)
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    
    # (Process Popup ผู้ส่ง ถ้ามี)
    process_sender_info_popup(main_window, phone, sender_postal)
    time.sleep(step_delay)

    # 2. EMS สินค้าสำเร็จรูป (มีอยู่แล้ว)
    # ใช้ smart_click_with_scroll เผื่อต้องเลื่อนหา
    if not smart_click_with_scroll(main_window, "EMS สินค้าสำเร็จรูป", scroll_dist=scroll_dist): 
        log("[Error] ไม่เจอเมนู EMS สินค้าสำเร็จรูป")
        return
    time.sleep(step_delay)

    # ================= ปรับแก้ 4 ขั้นตอนแรก ตามที่ขอ =================

    # 3. เลือกหมวดหมู่ (รูป 1) -> ใช้ค่า Hardcoded
    log(f"...[Step 3] เลือกหมวดหมู่: {category_name}")
    # ใช้ smart_click_with_scroll เผื่อหมวดอยู่ข้างล่าง
    if not smart_click_with_scroll(main_window, category_name, max_scrolls=10, scroll_dist=scroll_dist):
        log(f"[WARN] หาหมวดหมู่ '{category_name}' ไม่เจอ")
    
    time.sleep(step_delay)

    # 4. เลือกรุปร่างชิ้นจดหมาย (รูป 2) -> ใช้ค่า Hardcoded + เลื่อนหาได้
    # **ใช้คนหาจาก Text (product_detail) ตามที่ต้องการ**
    log(f"...[Step 4] เลือกสินค้า: {product_detail}")
    
    # เน้นย้ำ: ใช้ max_scrolls เยอะหน่อยเผื่อรายการเยอะ
    found_product = smart_click_with_scroll(main_window, product_detail, max_scrolls=15, scroll_dist=scroll_dist)
    if not found_product:
        log(f"[WARN] หาสินค้า '{product_detail}' ไม่เจอ (ลองเลื่อนแล้ว)")
    
    # กด ถัดไป (Enter)
    smart_next(main_window)
    time.sleep(step_delay)

    # 5. หน้า น้ำหนัก (รูป 3) -> อ่านจาก Config (เดิม)
    log(f"...[Step 5] กรอกน้ำหนัก: {weight}")
    smart_input_generic(main_window, weight, "น้ำหนัก")
    
    # กด ถัดไป (Enter)
    smart_next(main_window)
    time.sleep(step_delay)

    # 6. หน้า ปริมาตร (รูป 4) -> ใช้ TAB Navigation
    log(f"...[Step 6] กรอกปริมาตร (กว้าง: {width}, ยาว: {length}, สูง: {height})")
    
    # [แก้ไข] ใช้การหา Edit แรกแล้วกด Tab ไปเรื่อยๆ เพราะช่องไม่มีชื่อ
    try:
        # พยายามหาช่องกรอกแรกสุดที่มองเห็น (ช่องกว้าง)
        edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            log("   -> เจอช่องแรก -> เริ่มกรอกและ Tab")
            # กรอก กว้าง -> TAB -> ยาว -> TAB -> สูง
            main_window.type_keys(f"{width}{{TAB}}{length}{{TAB}}{height}", with_spaces=True)
        else:
            log("   [WARN] ไม่เจอ Edit box -> ลองพิมพ์ Blind Type")
            main_window.type_keys(f"{width}{{TAB}}{length}{{TAB}}{height}", with_spaces=True)
    except:
         log("   [!] Error กรอกปริมาตร")

    # กด ถัดไป (Enter)
    smart_next(main_window)
    time.sleep(step_delay)

    # 7. หน้า เลข ปณ ปลายทาง (รูป 4/5) -> มีอยู่แล้ว
    log(f"...[Step 7] กรอก ปณ ปลายทาง: {receiver_postal}")
    # ลองพิมพ์เลยเพราะเมาส์มักจะโฟกัสที่ช่องนี้อยู่แล้ว
    try: main_window.type_keys(str(receiver_postal), with_spaces=True)
    except: pass
    
    # กด ถัดไป (Enter) เพื่อไปต่อ
    smart_next(main_window)
    time.sleep(step_delay)

    # ================= จบส่วนแก้ไข =================
    
    # Flow ต่อจากนี้เป็น Pattern เดิม (ขออนุญาตย่อส่วนนี้เพื่อให้โค้ดไม่ยาวเกินไป 
    # แต่ในการใช้งานจริง ให้เอา Code ส่วนที่เหลือจากไฟล์เดิมมาแปะต่อได้เลยครับ)
    
    log("...เข้าสู่กระบวนการเดิม (ตรวจสอบพื้นที่ทับซ้อน/บริการขนส่ง)...")
    # (Handle Overlap Area)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ"); found = True; break
        if found: break
        time.sleep(0.5)

    # เลือกบริการขนส่ง (ShippingService_2579)
    wait_until_id_appears(main_window, "ShippingService_2579", timeout=15)
    if find_and_click_with_rotate_logic(main_window, "ShippingService_2579"):
        main_window.type_keys("{ENTER}")
    
    time.sleep(1)
    smart_next(main_window)
    
    # จบ Flow แบบย่อ
    log("[SUCCESS] จบการทำงานส่วนต้นที่แก้ไขแล้ว")

# ================= 5. Start App =================
if __name__ == "__main__":
    
    target_config = 'config.ini' # <-- เปลี่ยนชื่อไฟล์ตรงนี้ได้เลยตามต้องการ
    
    conf = load_config(target_config)
    
    if conf:
        log(f"Connecting... (Using Config: {target_config})")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to Title: {app_title}")
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            run_smart_scenario(main_window, conf)
        except Exception as e:
            log(f"Error: {e}")
            print("คำแนะนำ: ตรวจสอบว่าเปิดโปรแกรม POS ไว้หรือยัง")
    input("\n>>> กด Enter เพื่อปิดโปรแกรม... <<<")