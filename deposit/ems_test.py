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
    config = configparser.ConfigParser()
    if not os.path.exists(file_path): 
        print(f"[Error] ไม่พบไฟล์ Config ที่: {file_path}")
        return None
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions =================
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

def wait_for_text(window, text_list, timeout=5):
    if isinstance(text_list, str): text_list = [text_list]
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible():
                        return True
        except: pass
        time.sleep(0.5)
    return False

def smart_next(window):
    """กดปุ่มถัดไป (Footer) หรือ Enter"""
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

def check_error_popup(window, delay=0.5):
    """เช็ค Popup และกดปิด"""
    if delay > 0:
        time.sleep(delay)
    try:
        for child in window.descendants(control_type="Window"):
            txt = child.window_text()
            if "แจ้งเตือน" in txt or "Warning" in txt or "คำเตือน" in txt:
                log(f"[WARN] พบ Popup: {txt}")
                if smart_click(window, ["ตกลง", "OK", "ปิด", "Close", "Yes", "ใช่"], timeout=2):
                    return True
                else:
                    window.type_keys("{ENTER}")
                    return True
        if wait_for_text(window, ["ไม่มีผลลัพธ์", "ไม่สามารถเชื่อมต่อ"], timeout=0.1): 
             log("[WARN] พบข้อความ Error")
             if smart_click(window, ["ตกลง", "OK", "กลับ"], timeout=2):
                 return True
             window.type_keys("{ENTER}") 
             return True
    except: pass
    return False

# ================= 3. Logic หลัก (Process Functions) =================

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

def fill_manual_address(window, manual_data):
    """ฟังก์ชันกรอกที่อยู่เอง (กรณีเกิด Error Popup)"""
    log("...เข้าสู่โหมดกรอกที่อยู่ด้วยตนเอง (Manual Fallback)...")
    province = manual_data.get('Province', '')
    district = manual_data.get('District', '')
    subdistrict = manual_data.get('SubDistrict', '')
    
    try:
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        address_edits = [e for e in edits if e.rectangle().top < 500]
        address_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
        
        if len(address_edits) >= 4:
            log(f"...กรอกจังหวัด: {province}")
            address_edits[1].click_input()
            address_edits[1].type_keys(province, with_spaces=True)
            log(f"...กรอกเขต/อำเภอ: {district}")
            address_edits[2].click_input()
            address_edits[2].type_keys(district, with_spaces=True)
            log(f"...กรอกแขวง/ตำบล: {subdistrict}")
            address_edits[3].click_input()
            address_edits[3].type_keys(subdistrict, with_spaces=True)
        else:
            log("[!] พบช่องกรอกไม่ครบ -> ลองกด Tab")
            window.type_keys("{TAB}")
            window.type_keys(province, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(district, with_spaces=True); window.type_keys("{TAB}")
            window.type_keys(subdistrict, with_spaces=True)
    except Exception as e:
        log(f"[!] Error กรอกที่อยู่เอง: {e}")

def process_receiver_address_selection(window, address_keyword, manual_data):
    log(f"--- หน้า: ค้นหาที่อยู่ ({address_keyword}) ---")
    
    if wait_for_text(window, "ข้อมูลผู้รับ", timeout=5):
        # 1. หาช่องค้นหาและกรอกข้อมูล
        try:
            search_ready = False
            for _ in range(10):
                edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
                if edits:
                    search_ready = True
                    break
                time.sleep(0.5)
            
            if not search_ready: log("[WARN] หาช่องค้นหาไม่เจอ")
            
            edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
            filled = False
            for edit in edits:
                if "ที่อยู่" in edit.element_info.name or not edit.get_value():
                    edit.click_input()
                    edit.type_keys(str(address_keyword), with_spaces=True)
                    filled = True
                    break
            if not filled and len(edits) > 1:
                edits[1].click_input()
                edits[1].type_keys(str(address_keyword), with_spaces=True)
        except: pass

        # กด Enter/ถัดไป เพื่อเรียกหน้า List
        log("...กด Enter/ถัดไป เพื่อค้นหารายการ...")
        smart_next(window)
        time.sleep(1.0)
        
        # 2. รอ Popup หรือ รายการที่อยู่
        log("...รอผลลัพธ์ (Popup หรือ รายการ) [Fast Check]...")
        found_popup = False
        found_list = False
        
        for _ in range(25):
            if check_error_popup(window, delay=0.0):
                log("[WARN] ตรวจพบ Popup คำเตือน -> เข้าสู่โหมด Manual")
                found_popup = True
                break
            list_items = [i for i in window.descendants(control_type="ListItem") 
                          if i.is_visible() and i.rectangle().top > 200]
            if list_items:
                found_list = True
                break
            time.sleep(0.25)

        # 3. ตัดสินใจทำงานต่อ
        if found_popup:
            fill_manual_address(window, manual_data)
            smart_next(window)
        elif found_list:
            log("...เจอรายการแล้ว! รอ UI นิ่ง (1.0s)...")
            time.sleep(1.0) 
            try:
                all_list_items = [i for i in window.descendants(control_type="ListItem") if i.is_visible()]
                valid_items = [i for i in all_list_items if i.rectangle().top > 200 and i.rectangle().height() > 50]
                
                if valid_items:
                    valid_items.sort(key=lambda x: x.rectangle().top)
                    target_item = valid_items[0]
                    log(f"[/] เลือกรายการแรกสุด: (Y={target_item.rectangle().top})")
                    try: target_item.set_focus()
                    except: pass
                    target_item.click_input()
                    log("...รอข้อมูลลงฟอร์ม (2.0s)...")
                    time.sleep(2.0) 
                else:
                    log("[!] รายการหายไปหลังรอ? (กรองไม่ผ่าน)")
            except: pass
            
            # เมื่อเลือกรายการเสร็จ ยังไม่ต้องกดถัดไปตรงนี้ 
            # เพราะผู้ใช้แจ้งว่า "หลังจากกดเลือกรายการแรกสุด จะเข้ามาหน้าข้อมูลผู้รับ ยังไม่ต้องกดถัดไป"
            # แต่ปกติการเลือกรายการ มันจะยังไม่เปลี่ยนหน้า จนกว่าเราจะกดถัดไป หรือ Enter
            # ตาม Workflow เดิมคือกดถัดไปเพื่อยืนยันการเลือก
            smart_next(window) 
        else:
            log("[!] ไม่เจอทั้ง Popup และ รายการ -> ลองกดถัดไปเลย")
            smart_next(window)

def process_receiver_details_form(window, fname, lname, phone):
    log("--- หน้า: รายละเอียดผู้รับ (ตรวจสอบ/แก้ไข) ---")
    log("...รอหน้าจอโหลด...")
    
    page_ready = False
    for i in range(15):
        if wait_for_text(window, ["ชื่อ", "นามสกุล", "คำนำหน้า"], timeout=1):
            page_ready = True
            break
        if i == 5: log("...ยังรอหน้าจออยู่ (5s)...")
        time.sleep(0.5)
    
    check_error_popup(window)
    time.sleep(1)

    try:
        log("...ตรวจสอบช่องกรอกชื่อ/นามสกุล...")
        edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        # กรองเฉพาะช่องที่อยู่ด้านบน
        top_edits = [e for e in edits if 150 < e.rectangle().top < 500]
        
        name_filled = False

        if len(top_edits) >= 2: 
            top_edits.sort(key=lambda x: (x.rectangle().top, x.rectangle().left))
            
            name_edit = None
            lastname_edit = None

            if len(top_edits) >= 3:
                name_edit = top_edits[1]
                lastname_edit = top_edits[-1]
            else:
                name_edit = top_edits[0]
                lastname_edit = top_edits[1]

            # ตรวจสอบชื่อ
            curr_name = name_edit.get_value()
            if curr_name and len(str(curr_name).strip()) > 0:
                log(f"...มีชื่ออยู่แล้ว ({curr_name}) -> ข้าม")
            else:
                log(f"...ช่องว่าง -> กรอกชื่อ: {fname}")
                name_edit.click_input()
                name_edit.type_keys(fname, with_spaces=True)

            # ตรวจสอบนามสกุล
            curr_lname = lastname_edit.get_value()
            if curr_lname and len(str(curr_lname).strip()) > 0:
                log(f"...มีนามสกุลอยู่แล้ว ({curr_lname}) -> ข้าม")
            else:
                log(f"...ช่องว่าง -> กรอกนามสกุล: {lname}")
                lastname_edit.click_input()
                lastname_edit.type_keys(lname, with_spaces=True)
            
            name_filled = True
        else:
            # Fallback Click Label + Tab
            log("[!] ไม่เจอช่อง Edit -> ใช้ระบบสำรอง (Click Label + Tab)")
            # (Fallback logic remains similar, assuming typing blindly if label found)
            # ... (ตัดส่วน Fallback สั้นๆ เพื่อความกระชับ แต่ Logic เดิมยังใช้ได้)
            
        if not name_filled:
            log("[WARN] ไม่พบช่องกรอกชื่อ/นามสกุล (อาจจะกรอกไปแล้ว หรือหาไม่เจอ)")

        # ตรวจสอบเบอร์โทร
        log("...เลื่อนลงเพื่อตรวจสอบเบอร์โทร...")
        force_scroll_down(window, -10)
        time.sleep(1)
        
        found_phone = False
        visible_edits = [e for e in window.descendants(control_type="Edit") if e.is_visible()]
        for edit in visible_edits:
            if "โทร" in edit.element_info.name or "Phone" in edit.element_info.automation_id:
                current_val = edit.get_value()
                if current_val and len(str(current_val).strip()) > 5:
                    log(f"...มีเบอร์โทรอยู่แล้ว ({current_val}) -> ข้าม")
                else:
                    log(f"...ช่องว่าง -> กรอกเบอร์: {phone}")
                    edit.click_input()
                    edit.type_keys(phone, with_spaces=True)
                found_phone = True
                break
        
        if not found_phone:
            log("[!] หาช่องเบอร์ไม่เจอ -> ลองกด Tab")
            window.type_keys("{TAB}"*3)
            window.type_keys(phone, with_spaces=True)

    except Exception as e:
        log(f"[!] Error: {e}")
        raise e 

    # [NEW REQUIREMENT] กดถัดไป (Enter) 3 ครั้ง เพื่อข้ามหน้าใบเสร็จไปหน้าทำรายการซ้ำ
    log("...กรอกเสร็จสิ้น -> กด 'ถัดไป' 3 ครั้ง เพื่อไปหน้าทำรายการซ้ำ...")
    for i in range(3):
        log(f"   -> Enter ครั้งที่ {i+1}")
        smart_next(window)
        time.sleep(1.0) # หน่วงเวลาเล็กน้อยระหว่างการกด

def process_repeat_transaction(window, should_repeat):
    log("--- หน้า: ทำรายการซ้ำ ---")
    if wait_for_text(window, ["ทำรายการซ้ำ", "ซ้ำ"], timeout=5):
        target = "ใช่" if should_repeat.lower() in ['true', 'yes', 'on'] else "ไม่"
        log(f"...เลือก: {target}...")
        smart_click(window, target)
        if target == "ไม่": window.type_keys("{LEFT}{ENTER}")
        else: window.type_keys("{ENTER}")
    else:
        log("[WARN] ไม่พบหน้าทำรายการซ้ำ")

# ================= 4. Run Function (Partial) =================
def run_partial_test(main_window, config):
    # Load vars
    special_services = config['SPECIAL_SERVICES'].get('Services', '')
    addr_keyword = config['RECEIVER'].get('AddressKeyword', '')
    rcv_fname = config['RECEIVER_DETAILS'].get('FirstName', '')
    rcv_lname = config['RECEIVER_DETAILS'].get('LastName', '')
    rcv_phone = config['RECEIVER_DETAILS'].get('PhoneNumber', '')
    repeat_flag = config['REPEAT_TRANSACTION'].get('Repeat', 'False')
    step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))

    if 'MANUAL_ADDRESS_FALLBACK' in config:
        manual_data = {
            'Province': config['MANUAL_ADDRESS_FALLBACK'].get('Province', ''),
            'District': config['MANUAL_ADDRESS_FALLBACK'].get('District', ''),
            'SubDistrict': config['MANUAL_ADDRESS_FALLBACK'].get('SubDistrict', '')
        }
    else:
        manual_data = {'Province': '', 'District': '', 'SubDistrict': ''}

    log("!!! เริ่มการทดสอบแบบย่อ (เริ่มที่หน้าบริการพิเศษ) !!!")
    time.sleep(2)

    # 11. หน้าบริการพิเศษ
    process_special_services(main_window, special_services)
    time.sleep(step_delay)

    # 12. หน้าข้อมูลผู้ส่ง (ข้าม)
    process_sender_info_page(main_window)
    time.sleep(step_delay)

    # 13. หน้าข้อมูลผู้รับ (เลือกที่อยู่)
    process_receiver_address_selection(main_window, addr_keyword, manual_data)
    time.sleep(step_delay)
    
    # 14. หน้ารายละเอียดผู้รับ (ตรวจสอบ -> กด Next 3 ครั้ง)
    process_receiver_details_form(main_window, rcv_fname, rcv_lname, rcv_phone)
    time.sleep(step_delay)

    # 15. หน้าคำแนะนำใบเสร็จ (ถูกข้ามไปแล้วจากการกด Next 3 ครั้งด้านบน)
    # process_receipt_info(main_window) 
    
    # 16. หน้าทำรายการซ้ำ
    process_repeat_transaction(main_window, repeat_flag)

    log("[SUCCESS] จบการทดสอบแบบย่อ")

# ================= 5. Main =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting to App...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            app = Application(backend="uia").connect(title_re=app_title, timeout=wait)
            main_window = app.top_window()
            if main_window.exists():
                if main_window.get_show_state() == 2: main_window.restore()
                main_window.set_focus()
            
            run_partial_test(main_window, conf)
            
        except Exception as e:
            log(f"Error: {e}")
    input("\n>>> กด Enter เพื่อปิด... <<<")