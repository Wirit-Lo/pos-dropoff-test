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
    """
    ค้นหาปุ่มเลื่อนขวา โดยใช้ ID 'ArrowIcon' ที่เจอจากการสแกน
    """
    try:
        # 1. ค้นหาด้วย ID 'ArrowIcon' (จากที่คุณสแกนเจอ)
        arrow_icons = [c for c in window.descendants() if c.element_info.automation_id == "ArrowIcon" and c.is_visible()]
        if arrow_icons:
            log("      [Scroll] เจอ ID 'ArrowIcon' -> ใช้ปุ่มนี้เลื่อนหน้า")
            return arrow_icons[0]

        # 2. กรณีสำรอง: ถ้าไม่เจอ ArrowIcon ให้หาปุ่ม/รูปภาพ ที่อยู่ขวาสุดของจอ
        log("      [Scroll] ไม่เจอ ArrowIcon -> หาปุ่มขวาสุดแทน")
        candidates = []
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        
        visible_candidates = [c for c in candidates if c.is_visible()]
        if not visible_candidates: return None
        
        win_rect = window.rectangle()
        # กรองเฉพาะตัวที่อยู่ขวาสุด (โซน 85% ของจอขึ้นไป)
        right_side_candidates = [c for c in visible_candidates if c.rectangle().left > win_rect.left + (win_rect.width() * 0.85)]
        
        if right_side_candidates:
             # เรียงจากซ้ายไปขวา (เอาตัวขวาสุด)
             right_side_candidates.sort(key=lambda x: x.rectangle().left, reverse=True)
             return right_side_candidates[0]
                     
        return None
    except Exception as e:
        log(f"Error finding scroll: {e}")
        return None

def find_and_click_safe_zone(window, target_id, max_attempts=15):
    """
    เลื่อนหาปุ่มจนกว่าจะเข้ามาอยู่ใน Safe Zone (กลางจอ) แล้วค่อยกด
    """
    log(f"...กำลังค้นหาปุ่ม '{target_id}' และจัดตำแหน่ง...")
    
    last_rect_left = -1
    stuck_counter = 0

    for i in range(max_attempts):
        # 1. ค้นหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
        
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # Safe Zone: ต้องไม่อยู่ชิดขอบขวา (ไม่เกิน 70% ของหน้าจอ)
            # เพื่อให้มั่นใจว่าปุ่มเลื่อนมากลางจอแล้ว และไม่โดน ArrowIcon บัง
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            log(f"   [Check {i+1}] ปุ่มอยู่ที่ X={rect.left} (Limit: {int(safe_limit)})")
            
            # เช็คว่าปุ่มขยับไหม (ถ้าเลื่อนแล้วที่เดิม แสดงว่าสุดทางแล้ว)
            if abs(rect.left - last_rect_left) < 5 and i > 0:
                stuck_counter += 1
                if stuck_counter >= 3:
                    log("   [!] ปุ่มไม่ขยับแล้ว (สุดทาง) -> ตัดสินใจกดเลย")
                    target.click_input()
                    return True
            else:
                stuck_counter = 0
            
            last_rect_left = rect.left

            if rect.right < safe_limit:
                log(f"   [/] ปุ่มอยู่ใน Safe Zone (เห็นชัดเจน) -> คลิก!")
                time.sleep(0.5)
                target.click_input()
                return True
            else:
                log(f"   [!] ปุ่มอยู่ลึกไปทางขวา -> ต้องเลื่อนซ้ายเข้ามา")
        else:
            log(f"   [Check {i+1}] ยังไม่เห็นปุ่มเป้าหมายบนหน้าจอ -> ต้องเลื่อนหา")

        # 2. สั่งกดปุ่มเลื่อน (ArrowIcon)
        scroll_btn = find_scroll_button(window)
        
        if scroll_btn:
            try:
                log(f"      -> กดปุ่มเลื่อน (ID: {scroll_btn.element_info.automation_id})")
                scroll_btn.click_input()
            except:
                log("      -> กดปุ่มเลื่อน Error -> ใช้ Keyboard แทน")
                window.type_keys("{RIGHT}")
        else:
            log("      -> หาปุ่มเลื่อนไม่เจอ -> ใช้ Keyboard {RIGHT}")
            window.type_keys("{RIGHT}")
            
        time.sleep(1.5) # รอ Animation เลื่อน
        
    log("[Fail] หมดความพยายามในการเลื่อนหา")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (ระบบ Scroll โดยใช้ ArrowIcon) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ
    # แก้ ID ตรงนี้ให้ตรงกับบริการที่คุณต้องการเทส
    target_service_id = "ShippingService_2583" 
    
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
    except: pass
    
    if not popup_window:
        try:
            children = main_window.children(control_type="Window")
            if children: popup_window = children[0]
        except: pass

    # --- กรอกข้อมูลใน Popup ---
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