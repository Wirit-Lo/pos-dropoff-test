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
def find_smart_scroll_button(window):
    """
    ค้นหาปุ่มเลื่อน (Scroll) โดยดูจากระดับความสูง (Y) ของบริการ
    เพื่อป้องกันการไปกดปุ่มผิดที่อยู่ด้านล่าง
    """
    try:
        # 1. หาตำแหน่งอ้างอิงของแถวบริการ (Service Row)
        # โดยการหาปุ่มบริการสักอันที่มองเห็น (เช่น EMS หรืออะไรก็ได้ที่มีคำว่า Service)
        service_ref = None
        for btn in window.descendants(control_type="Button"):
            if "ShippingService" in btn.element_info.automation_id and btn.is_visible():
                service_ref = btn
                break
        
        # กำหนดโซนความสูง (Y-Range) ที่ถูกต้อง
        min_y = 200
        max_y = 600 # ไม่ควรเกินนี้ เพราะด้านล่างเป็นส่วนยอดรวม

        if service_ref:
            rect = service_ref.rectangle()
            # ให้หาปุ่มที่อยู่ในระดับเดียวกับบริการ (+- 150px)
            center_y = (rect.top + rect.bottom) // 2
            min_y = center_y - 150
            max_y = center_y + 150
            log(f"      [Smart Scroll] พบแถวบริการที่ระดับ Y={center_y} (ค้นหาปุ่มเลื่อนในช่วง Y {min_y}-{max_y})")
        else:
            log("      [Smart Scroll] ไม่พบปุ่มบริการอ้างอิง -> ใช้ค่า Default Y (200-600)")

        # 2. ค้นหา Candidates (Button หรือ Image) ที่อยู่ขวาสุด และอยู่ในโซนความสูงนี้
        candidates = []
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        
        visible_candidates = [c for c in candidates if c.is_visible()]
        if not visible_candidates: return None
        
        win_rect = window.rectangle()
        # กรองเฉพาะ:
        # A. อยู่ด้านขวาของจอ (เกิน 80%)
        # B. อยู่ในระดับความสูงที่ถูกต้อง (ไม่ต่ำไปโดนปุ่มยอดรวม)
        # C. ขนาดไม่ใหญ่เกินไป (ปุ่มเลื่อนมักจะเล็ก)
        
        valid_scroll_btns = []
        for c in visible_candidates:
            r = c.rectangle()
            center_y_c = (r.top + r.bottom) // 2
            
            is_right_side = r.left > win_rect.left + (win_rect.width() * 0.85)
            is_in_y_range = min_y < center_y_c < max_y
            is_small = r.width() < 150
            
            if is_right_side and is_in_y_range and is_small:
                valid_scroll_btns.append(c)

        if valid_scroll_btns:
             # เอาตัวที่อยู่ขวาสุด
             valid_scroll_btns.sort(key=lambda x: x.rectangle().left, reverse=True)
             best_btn = valid_scroll_btns[0]
             log(f"      [Smart Scroll] เจอปุ่มเลื่อนที่ถูกต้อง! (ID: {best_btn.element_info.automation_id} | Y: {(best_btn.rectangle().top + best_btn.rectangle().bottom)//2})")
             return best_btn
        
        log("      [Smart Scroll] ไม่เจอปุ่มเลื่อนในระดับความสูงนี้")     
        return None
    except Exception as e:
        log(f"Error finding scroll: {e}")
        return None

def find_and_click_safe_zone(window, target_id, max_attempts=15):
    """
    เลื่อนหาปุ่มจนกว่าจะเข้ามาอยู่ใน Safe Zone โดยใช้ Smart Scroll
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
            safe_limit = win_rect.left + (win_rect.width() * 0.70) 
            
            log(f"   [Check {i+1}] ปุ่มอยู่ที่ X={rect.left} (Limit: {int(safe_limit)})")
            
            if abs(rect.left - last_rect_left) < 5 and i > 0:
                stuck_counter += 1
                if stuck_counter >= 3:
                    log("   [!] ปุ่มไม่ขยับแล้ว -> ตัดสินใจกดเลย")
                    target.click_input()
                    return True
            else:
                stuck_counter = 0
            
            last_rect_left = rect.left

            if rect.right < safe_limit:
                log(f"   [/] ปุ่มอยู่ใน Safe Zone -> คลิก!")
                time.sleep(0.5)
                target.click_input()
                return True
            else:
                log(f"   [!] ปุ่มอยู่ลึกไปทางขวา -> ต้องเลื่อนซ้ายเข้ามา")
        else:
            log(f"   [Check {i+1}] ยังไม่เห็นปุ่มเป้าหมาย -> ต้องเลื่อนหา")

        # 2. สั่งกดปุ่มเลื่อน (Smart Scroll V2)
        scroll_btn = find_smart_scroll_button(window)
        
        if scroll_btn:
            try:
                # scroll_btn.draw_outline() # Un-comment ถ้าต้องการเห็นกรอบสีแดงตอนเทส
                scroll_btn.click_input()
            except:
                log("      -> กดปุ่มเลื่อน Error -> ใช้ Keyboard แทน")
                window.type_keys("{RIGHT}")
        else:
            log("      -> หาปุ่มเลื่อนไม่เจอ (ใช้ Keyboard แทน)")
            window.type_keys("{RIGHT}")
            
        time.sleep(1.2) # รอ Animation เลื่อน
        
    log("[Fail] หมดความพยายามในการเลื่อนหา")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (Smart Scroll - Zone Specific) ---")
    
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

    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    time.sleep(1.5)

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
                popup_window.type_keys("{ENTER}")
                log("-> พิมพ์เลขและกด Enter (ถัดไป) เรียบร้อย")
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