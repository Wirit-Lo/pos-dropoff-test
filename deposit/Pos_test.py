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

# ================= 2. Helper Functions (Core Tools) =================

# ================= 2. Helper Functions (Auto-Wait Version) =================

def find_and_fill_smart(window, target_name, target_id_keyword, value, timeout=15):
    """
    (แก้ไขใหม่) ค้นหาช่องกรอกแบบ 'รอจนกว่าจะเจอ' (Wait until found)
    - timeout: ระยะเวลาสูงสุดที่จะรอ (วินาที) ป้องกันโปรแกรมค้าง
    """
    if not value or str(value).strip() == "": return False
    
    log(f"...กำลังรอช่อง '{target_name}' เพื่อกรอกข้อมูล (Max {timeout}s)...")
    start = time.time()
    
    while time.time() - start < timeout:
        target_elem = None
        try:
            # วนลูปหา Element ในหน้าจอ
            for child in window.descendants():
                if not child.is_visible(): continue
                
                aid = child.element_info.automation_id
                name = child.element_info.name
                
                # 1. เช็คจากชื่อ (Name)
                if target_name and name and target_name in name:
                    target_elem = child; break
                # 2. เช็คจาก ID
                if target_id_keyword and aid and target_id_keyword in aid:
                    target_elem = child; break
            
            if target_elem:
                # เจอแล้ว! พยายามหาช่อง Edit ข้างใน
                try:
                    edits = target_elem.descendants(control_type="Edit")
                    if edits: target_elem = edits[0]
                except: pass
                
                # คลิกและกรอกข้อมูล
                target_elem.set_focus()
                target_elem.click_input()
                # เพิ่มการรอเล็กน้อยหลังคลิก เพื่อให้เคอร์เซอร์กระพริบ
                time.sleep(0.5) 
                target_elem.type_keys(str(value), with_spaces=True)
                log(f"   [/] เจอและกรอก '{target_name}' เรียบร้อย")
                return True
                
        except Exception as e:
            # ถ้ามี Error ระหว่างหา ให้ลองใหม่รอบหน้า
            pass
            
        # ถ้ายังไม่เจอ ให้รอ 0.5 วินาที แล้ววนรอบใหม่
        time.sleep(0.5)
        
    log(f"[WARN] หมดเวลา ({timeout}s) หาช่อง '{target_name}' ไม่เจอ")
    return False

def wait_for_text(window, text_list, timeout=10):
    """(สำคัญ) ใช้สำหรับรอให้หน้าจอโหลดเสร็จ โดยเช็คจากข้อความบนจอ"""
    if isinstance(text_list, str): text_list = [text_list]
    log(f"...กำลังรอข้อความ: {text_list} (Max {timeout}s)...")
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            for child in window.descendants():
                txt = child.window_text()
                for t in text_list:
                    if t in txt and child.is_visible(): 
                        log(f"   [/] พบข้อความ '{t}' -> ไปต่อ")
                        return True
        except: pass
        time.sleep(0.5)
    log(f"[WARN] รอข้อความไม่เจอ (Timeout)")
    return False

# --- ฟังก์ชันอื่นๆ ใช้ของเดิมได้ แต่เพื่อความชัวร์แปะให้ครบชุดครับ ---

def click_scroll_arrow_smart(window, direction='right', repeat=5):
    try:
        target_group = [c for c in window.descendants() if c.element_info.automation_id == "ShippingServiceList"]
        if target_group: target_group[0].set_focus()
        else: window.set_focus()
        key_code = '{RIGHT}' if direction == 'right' else '{LEFT}'
        window.type_keys(key_code * repeat, pause=0.2, set_foreground=False)
        return True
    except: return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=15):
    log(f"...กำลังค้นหาปุ่มบริการ ID: '{target_id}'...")
    for i in range(1, max_rotations + 1):
        found_elements = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        should_scroll = False
        if found_elements:
            target = found_elements[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            if rect.right < safe_limit:
                 try: target.click_input()
                 except: target.set_focus(); window.type_keys("{ENTER}")
                 return True
            else: should_scroll = True
        else: should_scroll = True
        if should_scroll:
            if not click_scroll_arrow_smart(window, repeat=5): window.type_keys("{RIGHT}")
            time.sleep(1.0)
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

def smart_next(window):
    submits = [c for c in window.descendants() if c.element_info.automation_id == "LocalCommand_Submit" and c.is_visible()]
    if submits:
        submits.sort(key=lambda x: x.rectangle().top)
        submits[-1].click_input()
        log("   [/] กดปุ่ม 'ถัดไป' (Footer)")
    else:
        log("   [!] หาปุ่มถัดไปไม่เจอ -> กด Enter")
        window.type_keys("{ENTER}")

# ================= 3. Business Logic Functions (Updated) =================

def process_sender_info_popup(window, phone, sender_postal):
    """จัดการหน้าข้อมูลผู้ส่งแบบ Safe Mode (รอจนกว่าจะพร้อม)"""
    
    # 1. รอให้หน้า Popup ขึ้นมาก่อน (สังเกตจากคำว่า 'ที่อยู่' หรือ 'รหัสไปรษณีย์')
    wait_for_text(window, ["ที่อยู่", "รหัสไปรษณีย์", "ข้อมูลผู้ส่ง"], timeout=10)
    
    # กดปุ่มอ่านบัตรประชาชน
    if smart_click(window, "อ่านบัตรประชาชน", timeout=5): 
        # รอให้ระบบอ่านบัตร (เพิ่มเวลาตรงนี้เผื่อเครื่องช้า)
        log("...กำลังอ่านบัตรและโหลดข้อมูล (รอ 5s)...")
        time.sleep(5.0) 

        # 1. กรอกรหัสไปรษณีย์ (ฟังก์ชันนี้จะวนรอจนกว่าช่องจะโผล่และพิมพ์ได้)
        find_and_fill_smart(window, "รหัสไปรษณีย์", "PostalCode", sender_postal, timeout=10)
        
        # 2. กรอกเบอร์โทรศัพท์ (ฟังก์ชันนี้จะวนรอจนกว่าช่องจะโผล่)
        if not find_and_fill_smart(window, "เบอร์โทรศัพท์", "PhoneNumber", phone, timeout=10):
            # Fallback
            find_and_fill_smart(window, "หมายเลขโทรศัพท์", "Phone", phone, timeout=5)
        
        # รอให้แน่ใจว่าข้อมูลลงครบ
        time.sleep(1.0)
        smart_next(window)

def process_payment(window, payment_method, received_amount):
    """
    ฟังก์ชันชำระเงินแบบ Fast Cash (ไม่มีเงินทอน)
    - ปรับปรุง: เพิ่มระบบรอปุ่ม (Wait) เพื่อความแม่นยำ
    """
    # ใช้ตัวแปร log เพื่อให้ Python รู้ว่าเราใช้ค่าที่ส่งมาแล้ว (กันสีจาง/Error)
    log(f"--- ขั้นตอนการชำระเงิน: วิธี '{payment_method}' | ยอด: '{received_amount}' (โหมด Fast Cash) ---")
    
    # 1. กดรับเงิน (หน้าหลัก)
    log("...กำลังค้นหาปุ่ม 'รับเงิน'...")
    
    wait_for_text(window, "รับเงิน", timeout=10)
    time.sleep(1.0) # รอ Animation นิ่งสนิท
    
    # กดปุ่ม
    if smart_click(window, "รับเงิน"):
        log("...กดปุ่มรับเงินสำเร็จ -> รอโหลดหน้าชำระเงิน...")
        
        # รอให้ปุ่ม Fast Cash (ID: EnableFastCash) 
        if not wait_until_id_appears(window, "EnableFastCash", timeout=10):
            log("[WARN] รอนานเกินไป หน้าชำระเงินไม่โหลด")
            return
            
        time.sleep(1.0) 
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    # 2. กดปุ่ม Fast Cash (ID: EnableFastCash)
    log("...กำลังกดปุ่ม Fast Cash (อันที่ 2 แบบไม่มีเงินทอน)...")
    
    # ใช้ ID: EnableFastCash 
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] กดปุ่ม Fast Cash สำเร็จ -> ระบบตัดเงินทันที")
    else:
        log("[WARN] กดปุ่ม Fast Cash ไม่ติด -> ลองกด Enter ช่วย")
        window.type_keys("{ENTER}")

    # 3. จบรายการ
    log("...รอหน้าสรุป/เงินทอน -> กด Enter ปิดรายการ...")
    time.sleep(2.0) # รอ Animation ใบเสร็จเด้ง
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 3. Business Logic Functions =================

def process_sender_info_popup(window, phone, sender_postal):
    """จัดการหน้าข้อมูลผู้ส่ง: กดอ่านบัตร -> เติมรหัสปณ. -> เติมเบอร์โทร"""
    
    # กดปุ่มอ่านบัตรประชาชนเพื่อดึงข้อมูล (หรือเพื่อให้แน่ใจว่าโฟกัสหน้านี้)
    if smart_click(window, "อ่านบัตรประชาชน", timeout=3): 
        time.sleep(1.5) 

        # 1. กรอกรหัสไปรษณีย์ (ถ้ายังว่างอยู่)
        # ใช้ find_and_fill_smart ช่วยหาทั้ง "รหัสไปรษณีย์" หรือ ID ที่เกี่ยวข้อง
        find_and_fill_smart(window, "รหัสไปรษณีย์", "PostalCode", sender_postal)

        # 2. กรอกเบอร์โทรศัพท์ [จุดที่แก้ไข]
        # เปลี่ยนคำค้นหาเป็น "เบอร์โทรศัพท์" ตามที่ปรากฏในรูปภาพ
        if not find_and_fill_smart(window, "เบอร์โทรศัพท์", "PhoneNumber", phone):
            # Fallback: ถ้าหาไม่เจอ ลองหาคำว่า "โทรศัพท์" หรือ "หมายเลขโทรศัพท์" เผื่อไว้
            if not find_and_fill_smart(window, "โทรศัพท์", "Phone", phone):
                find_and_fill_smart(window, "หมายเลขโทรศัพท์", "Phone", phone)
        
        # กดถัดไป
        smart_next(window)

def process_payment(window, payment_method, received_amount):
    """(แก้ไข) รับ Argument ให้ครบ 3 ตัว ตามที่เรียกใช้"""
    log("--- ขั้นตอนการชำระเงิน (โหมด Fast Cash) ---")
    
    # รอจนกว่าปุ่ม 'รับเงิน' จะโผล่มา
    wait_for_text(window, "รับเงิน", timeout=10)
    time.sleep(1.0) # รอ Animation หยุด
    
    if smart_click(window, "รับเงิน"):
        # รอเข้าหน้า Fast Cash
        wait_until_id_appears(window, "EnableFastCash", timeout=10)
        time.sleep(1.0)
    else:
        log("[WARN] หาปุ่ม 'รับเงิน' ไม่เจอ")
        return

    log("...กดปุ่ม Fast Cash...")
    if click_element_by_id(window, "EnableFastCash", timeout=5):
        log("[/] ชำระเงินสำเร็จ")
    else:
        window.type_keys("{ENTER}")

    # รอหน้าสรุป
    time.sleep(2.0)
    window.type_keys("{ENTER}")
    time.sleep(1)

# ================= 4. Workflow Main (Safe Mode) =================
def run_smart_scenario(main_window, config):
    try:
        # อ่าน Config (ส่วนเดิม)
        sender_postal = config['TEST_DATA'].get('SenderPostalCode', '10110')
        sender_phone = config['TEST_DATA'].get('PhoneNumber', '0812345678')
        mo_config = config['MONEY_ORDER'] if 'MONEY_ORDER' in config else {}
        amount = mo_config.get('Amount', '100')
        dest_postal = mo_config.get('DestinationPostalCode', '10110')
        rcv_fname = mo_config.get('ReceiverFirstName', 'TestName')
        rcv_lname = mo_config.get('ReceiverLastName', 'TestLast')
        options_str = mo_config.get('Options', '')
        pay_method = config['PAYMENT'].get('Method', 'เงินสด') if 'PAYMENT' in config else 'เงินสด'
        pay_amount = config['PAYMENT'].get('ReceivedAmount', '1000') if 'PAYMENT' in config else '1000'
        step_delay = float(config['SETTINGS'].get('StepDelay', 0.8))
    except Exception as e: 
        log(f"[Error] อ่าน Config ไม่สำเร็จ: {e}")
        return

    log("--- เริ่มต้นการทำงาน (โหมดปลอดภัย: รอทุกขั้นตอน) ---")
    time.sleep(1.0)

    # Step 1: เลือกเมนู "ธนาณัติในประเทศ"
    # ใช้ smart_click ซึ่งมีระบบรออยู่แล้ว (timeout=5)
    if not smart_click(main_window, "ธนาณัติในประเทศ", timeout=10): 
        log("[Error] หาเมนูไม่เจอ")
        return
    time.sleep(step_delay)

    # Step 2: เลือกเมนู "รับฝากธนาณัติ"
    if not smart_click(main_window, "รับฝากธนาณัติ", timeout=10): return
    time.sleep(step_delay)

    # Step 3: เลือกบริการ
    target_service_id = "PayOutDomesticSendMoneyNormal101"
    
    # [แก้ไข] เปลี่ยนจากรอ ShippingServiceList เป็นรอปุ่มบริการโดยตรง
    # จะได้ไม่รอเก้อ 10 วินาที ถ้าปุ่มมาแล้วก็กดเลย
    wait_until_id_appears(main_window, target_service_id, timeout=10)
    
    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] ไม่เจอปุ่มบริการ {target_service_id}")
        return
    time.sleep(step_delay)

    # Step 4: Popup ข้อมูลผู้ส่ง
    # (ใช้ฟังก์ชันใหม่ที่เขียนรอไว้แล้ว)
    process_sender_info_popup(main_window, sender_phone, sender_postal)
    
    # Step 5: หน้าส่งเงิน
    # รอให้แน่ใจว่าเข้าหน้าส่งเงินแล้ว (เช็คจากคำว่า 'จำนวนเงิน' หรือ ID ช่องกรอก)
    wait_for_text(main_window, ["จำนวนเงิน", "ปลายทาง"], timeout=10)
    
    # กรอกจำนวนเงิน (Auto Wait)
    find_and_fill_smart(main_window, "จำนวนเงิน", "CurrencyAmount", amount, timeout=10)
    
    # กรอกปลายทาง (Auto Wait)
    find_and_fill_smart(main_window, "ปลายทาง", "SpecificPostOfficeFilter", dest_postal, timeout=10)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 6: เลือกบริการเสริม
    target_opt = str(options_str).strip().lower()
    
    log(f"--- หน้าเลือกบริการเสริม (Target: {target_opt}) ---")
    
    # รอให้ตัวเลือกโหลดขึ้นมา (เช็คจากคำว่า "SMS" หรือ "ตอบรับ")
    wait_for_text(main_window, ["SMS", "ตอบรับ", "บริการพิเศษ"], timeout=10)
    
    if target_opt:
        # 1. ตอบรับธรรมดา (Paper)
        if 'paper' in target_opt or 'ธรรมดา' in target_opt:
            log("...กำลังเลือก: ตอบรับธรรมดา...")
            click_element_by_fuzzy_id(main_window, "TransferOption_PaperNotice")
            
        # 2. ตอบรับด่วน (EMS) -> ใช้ elif เพื่อให้เลือกแค่อันเดียว
        elif 'ems' in target_opt or 'ด่วน' in target_opt:
            log("...กำลังเลือก: ตอบรับด่วนพิเศษ...")
            click_element_by_fuzzy_id(main_window, "TransferOption_EMSNotice")
            
        # 3. SMS -> ใช้ elif เพื่อให้เลือกแค่อันเดียว
        elif 'sms' in target_opt:
            log("...กำลังเลือก: ส่ง SMS...")
            click_element_by_fuzzy_id(main_window, "TransferOption_SMSNotice")

    # กดถัดไป
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 7: หน้าข้อมูลผู้ส่ง (ยืนยัน)
    # รอให้ Header ขึ้น
    wait_for_text(main_window, ["ผู้ฝากส่ง", "ข้อมูลผู้ส่ง"], timeout=10)
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 8: หน้าข้อมูลผู้รับ
    wait_for_text(main_window, ["ผู้รับ", "ชื่อ", "นามสกุล"], timeout=10)
    
    find_and_fill_smart(main_window, "ชื่อ", "CustomerFirstName", rcv_fname, timeout=10)
    find_and_fill_smart(main_window, "นามสกุล", "CustomerLastName", rcv_lname, timeout=10)
    
    smart_next(main_window)
    time.sleep(step_delay)

    # Step 9-10: รับเงิน (ใช้ฟังก์ชันที่เขียนรอไว้แล้ว)
    process_payment(main_window, pay_method, pay_amount)

    log("\n[SUCCESS] จบการทำงานธนาณัติครบทุกขั้นตอน")

# ================= 5. Start App =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        log("Connecting...")
        try:
            wait = int(conf['SETTINGS'].get('ConnectTimeout', 10))
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to Title: {app_title} (Wait: {wait}s)")
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