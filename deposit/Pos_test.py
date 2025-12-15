import configparser
import os
import time
import datetime
from pywinauto.application import Application

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
def find_scroll_button(window):
    """ค้นหาปุ่มเลื่อนขวา (>) โดยดูจากตำแหน่งขวาสุดของจอ"""
    try:
        # หาปุ่มทั้งหมด
        buttons = [b for b in window.descendants(control_type="Button") if b.is_visible()]
        
        # กรองปุ่มที่อยู่ขวาสุด (Top 3 ปุ่มที่ค่า Left เยอะสุด)
        if not buttons: return None
        
        # เรียงลำดับตามค่า Left (มากไปน้อย)
        buttons.sort(key=lambda x: x.rectangle().left, reverse=True)
        
        # ปุ่มเลื่อนมักจะเป็นปุ่มขวาสุดที่มีขนาดไม่ใหญ่มาก (เช่น กว้าง < 100)
        potential_scroll_btns = [b for b in buttons[:3] if b.rectangle().width() < 100]
        
        for btn in potential_scroll_btns:
            # ตรวจสอบ Text หรือกดได้เลยถ้ามั่นใจ
            txt = btn.window_text()
            if ">" in txt or "Next" in txt or not txt: # ปุ่มลูกศรมักจะไม่มี Text หรือเป็น >
                return btn
                
        return buttons[0] # ถ้าหาไม่เจอจริงๆ คืนค่าปุ่มขวาสุดไปเลย
    except:
        return None

def find_and_click_safe_zone(window, target_id, max_attempts=10):
    """
    [Logic ใหม่] เลื่อนหาจนกว่าปุ่มจะเข้ามาอยู่ใน Safe Zone (กลางจอ) แล้วค่อยกด
    """
    log(f"...กำลังค้นหาปุ่ม '{target_id}' และจัดตำแหน่ง...")
    
    for i in range(max_attempts):
        # 1. ค้นหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
        
        target_ready = False
        
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # คำนวณขอบเขต
            # Safe Zone: ปุ่มต้องไม่อยู่ชิดขอบขวาเกินไป (เผื่อโดนปุ่มเลื่อนบัง)
            # สมมติปุ่มเลื่อนกว้างประมาณ 60-80px
            unsafe_zone_start = win_rect.right - 120 
            
            log(f"   [Check {i+1}] เจอ {target_id} ที่ X={rect.left} ถึง {rect.right}")
            
            if rect.right < unsafe_zone_start:
                # ปุ่มอยู่ในระยะปลอดภัย (ไม่โดนบัง) -> กดได้
                log(f"   [/] ปุ่มอยู่ใน Safe Zone (ไม่โดนบัง) -> คลิก!")
                target.click_input()
                return True
            else:
                log(f"   [!] ปุ่มอยู่ชิดขวาเกินไป (อาจโดนบัง) -> ต้องเลื่อนอีก")
        else:
            log(f"   [Check {i+1}] ยังไม่เห็นปุ่มบนหน้าจอ -> ต้องเลื่อนหา")

        # 2. กดปุ่มเลื่อน (Scroll)
        scroll_btn = find_scroll_button(window)
        if scroll_btn:
            log(f"      -> กดปุ่มเลื่อนหน้าจอ (พิกัดปุ่ม: {scroll_btn.rectangle().mid_point()})")
            scroll_btn.click_input()
        else:
            log("      -> หาปุ่มเลื่อนไม่เจอ ใช้ปุ่มลูกศรขวาที่คีย์บอร์ดแทน")
            window.type_keys("{RIGHT}")
            
        time.sleep(1.5) # รอ Animation เลื่อน
        
    log("[Fail] หมดความพยายามในการเลื่อนหา")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (ระบบ Safe Zone Scroll) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ (ShippingService_2583)
    # แก้ ID ให้ตรงกับ Config หรือปุ่มจริงของคุณ
    target_service_id = "ShippingService_2583" 
    
    # ใช้ฟังก์ชันใหม่ที่ฉลาดขึ้น
    if not find_and_click_safe_zone(main_window, target_service_id):
        log(f"[Error] ไม่สามารถกดปุ่ม {target_service_id} ได้")
        return

    # [ส่วน Popup เดิม]
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(1.0)
    main_window.type_keys("{ENTER}")

    # ดึงค่าจาก Config
    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    
    time.sleep(1.5)

    # --- ค้นหา Popup ---
    popup_window = None
    try:
        app_top = Application(backend="uia").connect(active_only=True).top_window()
        if "จำนวน" in app_top.window_text() or app_top.element_info.control_type == "Window":
            popup_window = app_top
            log(f"-> เจอ Top Window Popup: {app_top.window_text()}")
    except: pass
    
    if not popup_window:
        try:
            children = main_window.children(control_type="Window")
            if children: popup_window = children[0]
        except: pass

    # --- กรอกข้อมูล ---
    if popup_window:
        try: popup_window.set_focus()
        except: pass
        
        target_edit = None
        try:
            edits = [e for e in popup_window.descendants(control_type="Edit") if e.is_visible()]
            valid_edits = [e for e in edits if e.rectangle().width() > 30]
            if valid_edits: target_edit = valid_edits[0]
        except: pass

        if target_edit:
            try:
                target_edit.click_input()
                time.sleep(0.2)
                target_edit.type_keys("^a{DELETE}", pause=0.1)
                time.sleep(0.1)
                target_edit.type_keys(str(qty), with_spaces=True)
                log(f"-> พิมพ์เลข {qty} เรียบร้อย")
                time.sleep(0.5)
                popup_window.type_keys("{ENTER}")
                log("-> กด Enter (ถัดไป) ใน Popup เรียบร้อย")
            except Exception as e:
                log(f"Error: {e}")
        else:
            log("[Warning] ไม่เจอช่อง Edit -> พิมพ์ใส่ Window เลย")
            popup_window.type_keys(str(qty), with_spaces=True)
            popup_window.type_keys("{ENTER}")
    else:
        log("[Error] หา Popup ไม่เจอ")

    log("--- จบการทดสอบ ---")

# ================= 4. Run =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        try:
            app_title = conf['APP']['WindowTitle']
            log(f"Connecting to: {app_title}")
            app = Application(backend="uia").connect(title_re=app_title, timeout=10)
            main_window = app.top_window()
            main_window.set_focus()
            
            test_popup_process(main_window, conf)
            
        except Exception as e:
            log(f"Error Connect: {e}")