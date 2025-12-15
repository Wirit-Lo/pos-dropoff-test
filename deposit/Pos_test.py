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
def find_scroll_button(window, target_rect=None):
    """
    ค้นหาปุ่มเลื่อนขวา โดยใช้ ID ที่น่าจะเป็น หรือค้นหาตามตำแหน่งขวาสุด
    """
    try:
        # 1. ลองหาจาก ID ที่น่าสงสัย (จาก Dump ของคุณ: Index 85 ArrowIcon)
        arrow_icons = [c for c in window.descendants() if c.element_info.automation_id == "ArrowIcon" and c.is_visible()]
        if arrow_icons:
            log("      [Scroll] เจอ ID 'ArrowIcon' -> ใช้ปุ่มนี้")
            return arrow_icons[0]

        # 2. ถ้าไม่เจอ ให้สแกนหาปุ่ม/รูปภาพ ที่อยู่ขวาสุดของจอ และอยู่ในระนาบเดียวกับเป้าหมาย
        candidates = []
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        
        visible_candidates = [c for c in candidates if c.is_visible()]
        
        if not visible_candidates: return None
        
        win_rect = window.rectangle()
        # กรองเฉพาะตัวที่อยู่ขวาสุด (ขวาเกิน 85% ของหน้าจอ)
        right_side_candidates = [c for c in visible_candidates if c.rectangle().left > win_rect.left + (win_rect.width() * 0.85)]
        
        # ถ้ามี Target Rect ให้หาตัวที่ Y ใกล้เคียงกัน (ระดับเดียวกัน)
        if target_rect and right_side_candidates:
            target_mid_y = (target_rect.top + target_rect.bottom) // 2
            # เรียงตามระยะห่างจากแกน Y ของเป้าหมาย (ใกล้สุดขึ้นก่อน)
            right_side_candidates.sort(key=lambda x: abs(((x.rectangle().top + x.rectangle().bottom) // 2) - target_mid_y))
            
            best_scroll = right_side_candidates[0]
            log(f"      [Scroll] เจอวัตถุขวาสุดที่ระดับเดียวกัน ({best_scroll.element_info.control_type}) -> ใช้ปุ่มนี้")
            return best_scroll

        # 3. ถ้าไม่มี Target หรือหาไม่เจอ เอาตัวขวาสุดที่มีขนาดเล็ก (ปุ่มลูกศร)
        if right_side_candidates:
             # เรียงจากซ้ายไปขวา (เอาตัวขวาสุด)
             right_side_candidates.sort(key=lambda x: x.rectangle().left, reverse=True)
             for c in right_side_candidates:
                 # กรองพวกปุ่มใหญ่ๆ ทิ้ง (ปุ่มเลื่อนน่าจะกว้างไม่เกิน 100)
                 if c.rectangle().width() < 120:
                     return c
                     
        return None
    except Exception as e:
        log(f"Error finding scroll: {e}")
        return None

def find_and_click_safe_zone(window, target_id, max_attempts=15):
    """
    [Logic ใหม่ V2] บีบ Safe Zone ให้แคบลง (60%) บังคับเลื่อนจนกว่าจะเห็นเต็มๆ
    """
    log(f"...กำลังค้นหาปุ่ม '{target_id}' และจัดตำแหน่ง (Strict Mode)...")
    
    last_rect_left = -1
    stuck_counter = 0

    for i in range(max_attempts):
        # 1. ค้นหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
        
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # คำนวณ Safe Zone: ต้องอยู่ใน "ซ้าย-กลาง" ของจอ (ไม่เกิน 60-70% ของความกว้าง)
            # เพื่อหนีจาก Overlay ด้านขวา
            safe_limit = win_rect.left + (win_rect.width() * 0.65) 
            
            log(f"   [Check {i+1}] ปุ่มอยู่ที่ X={rect.left} (Limit: {int(safe_limit)})")
            
            # เช็คว่าปุ่มขยับไหม (ถ้าเลื่อนแล้วที่เดิม แสดงว่าสุดทางแล้ว หรือเลื่อนไม่ไป)
            if abs(rect.left - last_rect_left) < 5 and i > 0:
                stuck_counter += 1
                if stuck_counter >= 3:
                    log("   [!] ปุ่มไม่ขยับแล้ว (อาจสุดทางแล้ว) -> ตัดสินใจกดเลย")
                    target.click_input()
                    return True
            else:
                stuck_counter = 0
            
            last_rect_left = rect.left

            if rect.right < safe_limit:
                log(f"   [/] ปุ่มอยู่ใน Safe Zone (เห็นเต็มใบ) -> คลิก!")
                time.sleep(0.5) # รอนิ่งๆ ก่อนกด
                target.click_input()
                return True
            else:
                log(f"   [!] ปุ่มอยู่ลึกไปทางขวา (โดนบังแน่ๆ) -> ต้องเลื่อนซ้ายเข้ามา")
        else:
            log(f"   [Check {i+1}] ยังไม่เห็นปุ่มบนหน้าจอ -> ต้องเลื่อนหา")

        # 2. ปฏิบัติการเลื่อน (Scroll)
        # ส่ง rect ของปุ่มเป้าหมายไปช่วยหาปุ่มเลื่อนที่ระดับเดียวกัน (ถ้าเจอ)
        target_rect_ref = found[0].rectangle() if found else None
        scroll_btn = find_scroll_button(window, target_rect=target_rect_ref)
        
        if scroll_btn:
            try:
                # ลอง Highlight ดูตำแหน่ง (Optional)
                # scroll_btn.draw_outline() 
                log(f"      -> กดปุ่มเลื่อน (ID: {scroll_btn.element_info.automation_id} | Type: {scroll_btn.element_info.control_type})")
                scroll_btn.click_input()
            except:
                log("      -> กดปุ่มเลื่อน Error -> ใช้ Keyboard แทน")
                window.type_keys("{RIGHT}")
        else:
            log("      -> หาปุ่มเลื่อนไม่เจอ -> ใช้ Keyboard {RIGHT}")
            window.type_keys("{RIGHT}")
            
        time.sleep(1.2) # รอ Animation เลื่อน
        
    log("[Fail] หมดความพยายามในการเลื่อนหา")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (Strict Scroll System) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ
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