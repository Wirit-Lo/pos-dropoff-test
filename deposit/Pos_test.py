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
    # ใช้ strict=False ตามโค้ดที่ 1 เพื่อป้องกัน Error key ซ้ำ
    config = configparser.ConfigParser(strict=False)
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

# ================= 2. Helper Functions (จากโค้ดที่ 1 + ส่วนเสริม) =================

def find_and_fill_smart(window, target_name, target_id_keyword, value):
    """
    ค้นหาและกรอกข้อมูล: รองรับทั้ง Name และ AutomationId (จากโค้ดที่ 1)
    """
    try:
        if not value or str(value).strip() == "":
            return False

        target_elem = None
        # 1. ค้นหารอบแรก (ในหน้าจอที่เห็น)
        for child in window.descendants():
            if not child.is_visible(): continue
            
            aid = str(child.element_info.automation_id)
            name = str(child.element_info.name)
            
            if target_name and target_name in name:
                target_elem = child; break
            if target_id_keyword and target_id_keyword in aid:
                target_elem = child; break
        
        # 2. ถ้าไม่เจอ ให้ลองเลื่อนลงนิดนึงแล้วหาใหม่
        if not target_elem:
            force_scroll_down(window, -3)
            time.sleep(0.5)
            for child in window.descendants():
                if not child.is_visible(): continue
                aid = str(child.element_info.automation_id)
                name = str(child.element_info.name)
                if target_name and target_name in name:
                    target_elem = child; break
                if target_id_keyword and target_id_keyword in aid:
                    target_elem = child; break

        if target_elem:
            log(f"   -> เจอช่อง '{target_name}/{target_id_keyword}' -> กรอก: {value}")
            try:
                # ถ้าเจอ Container ให้หา Edit box ข้างใน
                edits = target_elem.descendants(control_type="Edit")
                if edits: target_elem = edits[0]
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
    """
    [Updated V10 - Turbo Speed] จากโค้ดที่ 1
    """
    try:
        rect = window.rectangle()
        scrollbar_x = rect.left + int(rect.width() * 0.72)
        scrollbar_y = rect.top + int(rect.height() * 0.5)
        mouse.scroll(coords=(scrollbar_x, scrollbar_y), wheel_dist=scroll_dist)
        time.sleep(0.05) 
    except Exception as e:
        log(f"[!] Scroll Error: {e}")
        try: window.type_keys("{PGDN}")
        except: pass

def smart_click(window, criteria_list, timeout=5):
    if isinstance(criteria_list, str): criteria_list = [criteria_list]
    start = time.time()
    while time.time() - start < timeout:
        for criteria in criteria_list:
            try:
                for child in window.descendants():
                    text_match = criteria in child.window_text().strip()
                    id_match = criteria in str(child.element_info.automation_id)
                    name_match = criteria in str(child.element_info.name)
                    
                    if child.is_visible() and (text_match or id_match or name_match):
                        child.click_input()
                        log(f"[/] กดปุ่ม '{criteria}' สำเร็จ")
                        return True
            except: pass
        time.sleep(0.3)
    return False

def smart_click_with_scroll(window, criteria, max_scrolls=20, scroll_dist=-10):
    """
    [Updated V10 - Turbo Aggressive] จากโค้ดที่ 1
    """
    log(f"...ค้นหา '{criteria}' (โหมด V10: Turbo)...")
    loop_limit = max_scrolls + 10 
    
    for i in range(loop_limit):
        found_element = None
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                text_ok = criteria in child.window_text()
                id_ok = criteria in str(child.element_info.automation_id)
                name_ok = criteria in str(child.element_info.name)
                
                if text_ok or id_ok or name_ok:
                    found_element = child
                    break
        except: pass

        if found_element:
            try:
                elem_rect = found_element.rectangle()
                win_rect = window.rectangle()
                safe_bottom_limit = win_rect.bottom - 80
                
                if elem_rect.bottom >= safe_bottom_limit:
                    log(f"   [Turbo] เจอปุ่มอยู่ลึก -> กระชากขึ้นแรงๆ")
                    force_scroll_down(window, -60) 
                    time.sleep(0.1)
                    continue 
                
                found_element.click_input()
                log(f"   [/] เจอและกดปุ่ม '{criteria}' สำเร็จ")
                return True
            except Exception as e:
                log(f"   [!] Error: {e}")

        if i < loop_limit:
            if not found_element:
                force_scroll_down(window, scroll_dist)
            
    log(f"[X] หมดระยะเลื่อนหาแล้ว ไม่เจอปุ่ม '{criteria}'")
    return False

# เพิ่มฟังก์ชัน click_element_by_id เพื่อรองรับ Logic ของโค้ดที่ 2
def click_element_by_id(window, exact_id, timeout=5, index=0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            found = [c for c in window.descendants() if c.element_info.automation_id == exact_id and c.is_visible()]
            if len(found) > index:
                found[index].click_input()
                log(f"[/] กดปุ่ม ID '{exact_id}' สำเร็จ")
                return True
        except: pass
        time.sleep(0.5)
    return False

# เพิ่มฟังก์ชัน click_element_by_fuzzy_id เพื่อรองรับ Logic ของโค้ดที่ 2
def click_element_by_fuzzy_id(window, keyword, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                aid = child.element_info.automation_id
                if child.is_visible() and aid and keyword in aid:
                    child.click_input()
                    log(f"[/] เจอ Fuzzy ID: '{aid}' -> กดสำเร็จ")
                    return True
        except: pass
        time.sleep(0.5)
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
                if not child.is_visible(): continue
                txt = child.window_text()
                name = child.element_info.name
                for t in text_list:
                    if (txt and t in txt) or (name and t in name): 
                        return True
        except: pass
        time.sleep(0.5)
    return False

def wait_while_processing(window, timeout=10):
    log("...ตรวจสอบการโหลด (Wait for Idle)...")
    start = time.time()
    while time.time() - start < timeout:
        found_loading = False
        try:
            for child in window.descendants():
                if not child.is_visible(): continue
                txt = child.window_text()
                if "กำลังดำเนินการ" in txt or "กรุณารอสักครู่" in txt or "Processing" in txt or "Loading" in txt:
                    found_loading = True
                    break
        except: pass
        
        if not found_loading:
            return True
        time.sleep(0.5)
    return False

def smart_next(window):
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
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
    # ฟังก์ชันจัดการหน้า Popup ผู้ส่ง (จากโค้ดที่ 1 - ดีกว่า)
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
    for _ in range(5):
        try:
            for child in window.descendants():
                if "สิ่งของต้องห้าม" in child.window_text():
                    window.type_keys("{RIGHT}{RIGHT}{ENTER}"); return
        except: pass
        time.sleep(0.5)

def smart_input_generic(window, value, description="ข้อมูล"):
    """ฟังก์ชันกรอกข้อมูลทั่วไป (จากโค้ดที่ 1)"""
    log(f"...กำลังกรอก {description}: {value}...")
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        if edits:
            edits[0].click_input()
            edits[0].type_keys(str(value), with_spaces=True)
            return True
    except: pass
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

def process_receiver_address_selection(window, address_keyword, manual_data):
    # ฟังก์ชันจัดการที่อยู่ (จากโค้ดที่ 1 - รองรับ Manual Mode ได้ดีกว่า)
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    is_manual_mode = False

    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        try:
            search_ready = False
            for _ in range(10):
                edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
                if edits: search_ready = True; break
                time.sleep(0.5)
            
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    edit.click_input(); edit.type_keys(str(address_keyword), with_spaces=True)
                    filled = True; break
            if not filled and len(edits) > 1:
                edits[1].click_input(); edits[1].type_keys(str(address_keyword), with_spaces=True)
        except: pass

        log("...กด Enter/ถัดไป เพื่อค้นหารายการ...")
        smart_next(window)
        time.sleep(1.0) 
        
        log("...ตรวจสอบผลลัพธ์ (Popup/List)...")
        found_popup = False; found_list = False
        
        for _ in range(40): 
            if check_error_popup(window, delay=0.0):
                log("[WARN] ตรวจพบ Popup คำเตือน! -> ปิดแล้วเข้าสู่โหมดกรอกเอง")
                found_popup = True; break
            list_items = [i for i in window.descendants(control_type="ListItem") 
                          if i.is_visible() and i.rectangle().top > 200]
            if list_items: found_list = True; break
            time.sleep(0.25)

        if found_popup:
            log("...เข้าสู่โหมดกรอกเอง (Manual Mode) -> รอส่งข้อมูลหน้าถัดไป...")
            is_manual_mode = True
            time.sleep(1.0)
            
        elif found_list:
            log("...เจอรายการที่อยู่ -> เลือกรายการแรกสุด...")
            time.sleep(1.0)
            try:
                all_list_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible()]
                valid_items = [i for i in all_list_items if i.rectangle().top > 200 and i.rectangle().height() > 50]
                if valid_items:
                    valid_items.sort(key=lambda x: x.rectangle().top)
                    target_item = valid_items[0]
                    log(f"[/] Click รายการที่: (Y={target_item.rectangle().top})")
                    try: target_item.set_focus()
                    except: pass
                    target_item.click_input()
                    log("...เลือกรายการแล้ว รอโหลดข้อมูล (2.0s)...")
                    time.sleep(2.0) 
                else: log("[!] เจอ List แต่กรองความสูงไม่ผ่าน")
            except: pass
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการ -> สันนิษฐานว่าเข้าหน้ากรอกเอง")
            is_manual_mode = True
            smart_next(window)

    return is_manual_mode

def process_receiver_details_form(window, fname, lname, phone, is_manual_mode, manual_data):
    # ฟังก์ชันกรอกรายละเอียด (จากโค้ดที่ 1 - รองรับการกรอก manual address เมื่อจำเป็น)
    log("--- หน้า: รายละเอียดผู้รับ ---")
    log("...รอหน้าจอโหลด (พร้อมตรวจสอบ Popup Error)...")
    
    for _ in range(30):
        if check_error_popup(window, delay=0):
            log("...ปิด Popup แล้ว -> รอโหลดฟอร์มต่อ...")
            time.sleep(1.0)
        found = False
        for child in window.descendants():
            if "ชื่อ" in child.window_text() or "CustomerFirstName" in str(child.element_info.automation_id):
                found = True; break
        if found: break
        time.sleep(0.5)

    try:
        find_and_fill_smart(window, "ชื่อ", "CustomerFirstName", fname)
        find_and_fill_smart(window, "นามสกุล", "CustomerLastName", lname)

        need_fill_address = is_manual_mode
        if not need_fill_address:
            try:
                prov_box = [c for c in window.descendants(control_type="Edit") if "AdministrativeArea" in str(c.element_info.automation_id)]
                if prov_box:
                    val = prov_box[0].get_value()
                    if not val or str(val).strip() == "":
                        log("[Auto-Detect] ช่องจังหวัดว่าง -> บังคับเข้าโหมด Manual Fill")
                        need_fill_address = True
            except: pass

        if need_fill_address:
            log("...[Manual Data] เริ่มกรอกที่อยู่ (Scroll & Fill)...")
            log("   -> Scroll Down เพื่อหาช่องที่อยู่...")
            force_scroll_down(window, -5)
            time.sleep(1.0)

            addr1 = manual_data.get('Address1', '')
            addr2 = manual_data.get('Address2', '')
            province = manual_data.get('Province', '')
            district = manual_data.get('District', '')
            subdistrict = manual_data.get('SubDistrict', '')

            if not find_and_fill_smart(window, "จังหวัด", "AdministrativeArea", province):
                window.type_keys("{TAB}"); window.type_keys(province, with_spaces=True)
            if not find_and_fill_smart(window, "เขต/อำเภอ", "Locality", district):
                window.type_keys("{TAB}"); window.type_keys(district, with_spaces=True)
            if not find_and_fill_smart(window, "แขวง/ตำบล", "DependentLocality", subdistrict):
                window.type_keys("{TAB}"); window.type_keys(subdistrict, with_spaces=True)
            find_and_fill_smart(window, "ที่อยู่ 1", "StreetAddress1", addr1)
            find_and_fill_smart(window, "ที่อยู่ 2", "StreetAddress2", addr2)

        force_scroll_down(window, -5)
        if not find_and_fill_smart(window, "หมายเลขโทรศัพท์", "PhoneNumber", phone):
             find_and_fill_smart(window, "โทร", "Phone", phone)

    except Exception as e: log(f"[!] Error Details: {e}")

    log("...จบขั้นตอนข้อมูลผู้รับ -> กด 'ถัดไป' 3 ครั้ง...")
    for i in range(3):
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window); time.sleep(1.8)

def process_repeat_transaction(window, should_repeat):
    # ฟังก์ชันวนลูปทำรายการซ้ำ (จากโค้ดที่ 1 - สำคัญมาก)
    log("--- หน้า: ทำรายการซ้ำ (รอ Popup) ---")
    clean_flag = str(should_repeat).strip().lower().replace("'", "").replace('"', "")
    is_repeat_intent = clean_flag in ['true', 'yes', 'on', '1']
    
    found_popup = False
    for i in range(30):
        if wait_for_text(window, ["การทำรายการซ้ำ", "ทำซ้ำไหม", "ทำซ้ำ"], timeout=0.5):
            found_popup = True; break
        time.sleep(0.5)
        
    if found_popup:
        log("...เจอ Popup ทำรายการซ้ำ...")
        time.sleep(1.0)
        target = "ใช่" if is_repeat_intent else "ไม่"
        log(f"...Config: {should_repeat} -> Intent: {is_repeat_intent} -> เลือก: '{target}'")
        if not smart_click(window, target, timeout=3):
            if target == "ไม่": window.type_keys("{ESC}")
            else: window.type_keys("{ENTER}")
    else: 
        log("[WARN] ไม่พบ Popup ทำรายการซ้ำ (Timeout)")
    return is_repeat_intent

def process_payment(window, payment_method, received_amount):
    # ฟังก์ชันชำระเงิน (จากโค้ดที่ 1 - ครอบคลุมกว่า)
    log("--- ขั้นตอนการชำระเงิน ---")
    wait_while_processing(window)
    log("...ค้นหาปุ่ม 'รับเงิน'...")
    if smart_click(window, "รับเงิน", timeout=5): 
        log("...รอหน้าต่างชำระเงิน...")
        time.sleep(2.0) 
        if not wait_for_text(window, ["รับชำระเงิน", "ยอดเงินสุทธิ", "ช่องทางการชำระเงิน"], timeout=10):
            log("[WARN] ไม่เจอข้อความยืนยันหน้าจ่ายเงิน -> อาจจะกดปุ่มเงินสดวืดได้")
    else:
        log("[WARN] หาปุ่มรับเงินไม่เจอ")
        return

    log(f"...เลือกวิธีชำระเงิน: {payment_method}...")
    if not smart_click(window, payment_method, timeout=5):
        log(f"[WARN] ไม่เจอ '{payment_method}' -> เลือก 'เงินสด' แทน")
        smart_click(window, "เงินสด")
    
    time.sleep(1.0)
    log(f"...กรอกจำนวนเงิน: {received_amount}...")
    try:
        for _ in range(10):
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            if edits:
                edits[0].click_input()
                edits[0].type_keys(str(received_amount), with_spaces=True)
                break
            time.sleep(0.5)
        window.type_keys("{ENTER}") 
    except: log("[!] Error กรอกเงิน")
    time.sleep(1.5)

    log("...หน้าเงินทอน -> กด Enter จบรายการ...")
    wait_for_text(window, ["เปลี่ยนแปลงจำนวนเงิน", "เงินทอน"], timeout=5)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main (ผสมผสาน) =================
def run_smart_scenario(main_window, config):
    try:
        # --- อ่านค่า Config (รวม Key จากทั้ง 2 แบบ) ---
        weight = config['DEPOSIT_ENVELOPE'].get('Weight', '10')
        receiver_postal = config['DEPOSIT_ENVELOPE'].get('ReceiverPostalCode', '10110')
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        
        # ส่วนประกันภัย (จากโค้ดที่ 2)
        add_insurance_flag = config['DEPOSIT_ENVELOPE'].get('AddInsurance', 'False')
        insurance_amt = config['DEPOSIT_ENVELOPE'].get('Insurance', '1000')
        
        # ส่วน Special Options (จากโค้ดที่ 2)
        special_options_str = config['DEPOSIT_ENVELOPE'].get('SpecialOptions', '')

        # ส่วนท้าย (จากโค้ดที่ 1)
        special_services = config['SPECIAL_SERVICES'].get('Services', '')
        addr_keyword = config['RECEIVER'].get('AddressKeyword', '99/99')
        rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', 'A')
        rcv_lname = config['RECEIVER_DETAILS'].get('LastName', 'B')
        rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '081')
        repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
        
        # Payment Config
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'

        manual_data = {
            'Address1': config['MANUAL_ADDRESS_FALLBACK'].get('Address1', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Address2': config['MANUAL_ADDRESS_FALLBACK'].get('Address2', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', '') if 'MANUAL_ADDRESS_FALLBACK' in config else '',
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '') if 'MANUAL_ADDRESS_FALLBACK' in config else ''
        }
        
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
        scroll_dist = int(config['SETTINGS'].get('ScrollDistance', -5))
        wait_timeout = int(config['SETTINGS'].get('ElementWaitTimeout', 15))
        
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log(f"--- เริ่มต้นการทำงาน (Hybrid Mode) ---")
    log(f"--- ปณ.ต้นทาง: {sender_postal} | ปณ.ปลายทาง: {receiver_postal} ---")
    time.sleep(0.5)

    # 1. เลือก รับฝากสิ่งของ
    if not smart_click(main_window, "รับฝากสิ่งของ"): return
    time.sleep(step_delay)
    
    # 2. Popup ผู้ส่ง (ใช้ Logic โค้ดที่ 1)
    process_sender_info_popup(main_window, phone, sender_postal)
    time.sleep(step_delay)

    # 3. เลือก ซองจดหมาย (ใช้ Flow โค้ดที่ 2 - เป็นมาตรฐานกว่า)
    if not smart_click_with_scroll(main_window, "ซองจดหมาย", scroll_dist=scroll_dist): 
        log("[Error] ไม่เจอเมนูซองจดหมาย")
        return
    time.sleep(step_delay)

    # 4. Special Options (โค้ดที่ 2)
    if special_options_str.strip():
        for opt in special_options_str.split(','):
            if opt: smart_click(main_window, opt.strip(), timeout=2)
    main_window.type_keys("{ENTER}") # ปิด Popup Option
    time.sleep(step_delay)

    # 5. น้ำหนัก & สิ่งของต้องห้าม
    handle_prohibited_items(main_window)
    smart_input_generic(main_window, weight, "น้ำหนัก")
    smart_next(main_window)
    time.sleep(1)

    # 6. กรอก ปณ. ปลายทาง
    try: 
        log(f"...กรอก ปณ. ปลายทาง: {receiver_postal}")
        main_window.type_keys(str(receiver_postal), with_spaces=True)
    except: pass
    smart_next(main_window)
    time.sleep(step_delay)

    # 7. ตรวจสอบพื้นที่ทับซ้อน (Common Logic)
    for _ in range(3):
        found = False
        for child in main_window.descendants():
            if "ทับซ้อน" in child.window_text() or "พื้นที่" in child.window_text():
                smart_click(main_window, "ดำเนินการ"); found = True; break
        if found: break
        time.sleep(0.5)

    # ================= ส่วนกลาง: ใช้ Logic จากโค้ดที่ 2 (Service ID & Insurance) =================
    
    log("...[Step Middle] รอเลือกบริการด้วย ID (Logic โค้ด 2)...")
    wait_until_id_appears(main_window, "ShippingService_EMSServices", timeout=wait_timeout)
    
    # พยายามกดปุ่ม EMS ด้วย ID
    if not click_element_by_id(main_window, "ShippingService_EMSServices"):
        if not click_element_by_fuzzy_id(main_window, "EMSS"): return
    time.sleep(step_delay) 
    
    # พยายามเลือกบริการย่อย (ShippingService_2572 หรืออื่นๆ)
    if not click_element_by_id(main_window, "ShippingService_2572"):
        click_element_by_fuzzy_id(main_window, "ShippingService")
    time.sleep(1)

    # จัดการประกันภัย (Insurance)
    if add_insurance_flag.lower() in ['true', 'yes', 'on', '1']:
        log(f"...[Insurance] เพิ่มประกันภัย วงเงิน {insurance_amt}...")
        if click_element_by_id(main_window, "CoverageButton"):
            if wait_until_id_appears(main_window, "CoverageAmount", timeout=5):
                # หาช่องกรอกวงเงิน
                for child in main_window.descendants():
                    if child.element_info.automation_id == "CoverageAmount":
                        child.click_input(); child.type_keys(str(insurance_amt), with_spaces=True); break
                time.sleep(0.5)
                # กดตกลง
                submits = [c for c in main_window.descendants() if c.element_info.automation_id == "LocalCommand_Submit"]
                submits.sort(key=lambda x: x.rectangle().top)
                if submits: submits[0].click_input()
                else: main_window.type_keys("{ENTER}")
    
    time.sleep(1)
    smart_next(main_window) 
    time.sleep(step_delay)

    # ================= ส่วนท้าย: ใช้ Logic จากโค้ดที่ 1 (Receiver & Payment) =================

    # 1. บริการพิเศษ
    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    # 2. ข้อมูลผู้ส่ง (ตรวจสอบหน้า)
    process_sender_info_page(main_window)
    time.sleep(step_delay)
    
    # 3. ค้นหาที่อยู่ผู้รับ
    is_manual_mode = process_receiver_address_selection(main_window, addr_keyword, manual_data)
    time.sleep(step_delay)
    
    # 4. กรอกรายละเอียดผู้รับ
    process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone, is_manual_mode, manual_data)
    time.sleep(step_delay)
    
    # 5. เช็ค Loop รายการซ้ำ
    is_repeat_mode = process_repeat_transaction(main_window, repeat_flag)
    
    if is_repeat_mode:
        log("[Logic] ตรวจสอบพบโหมดทำรายการซ้ำ -> หยุดการทำงานทันที")
        return 
    
    # 6. ชำระเงิน
    process_payment(main_window, pay_method, pay_amount)

    log("\n[SUCCESS] จบการทำงานครบทุกขั้นตอน")

# ================= 5. Start App =================
if __name__ == "__main__":
    
    target_config = 'config.ini'
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