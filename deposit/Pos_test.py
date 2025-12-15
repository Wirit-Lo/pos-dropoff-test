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
    ค้นหาปุ่มเลื่อน (Scroll) โดยกรองปุ่ม Help ออก
    และเน้นหาปุ่มลูกศรจริงๆ
    """
    try:
        # รายชื่อ ID ที่ห้ามกด (ไม่ใช่ปุ่มเลื่อนแน่นอน)
        blacklist_ids = ["ShowHelpText", "ServiceGroupShowHelpText", "ShippingService", "GlobalCommand", "Notification", "CartButton"]
        
        # 1. หาปุ่มบริการเพื่อดูระดับความสูง (Y)
        service_ref = None
        for btn in window.descendants(control_type="Button"):
            aid = btn.element_info.automation_id
            if "ShippingService" in aid and btn.is_visible():
                service_ref = btn
                break
        
        min_y = 200
        max_y = 700 

        if service_ref:
            rect = service_ref.rectangle()
            center_y = (rect.top + rect.bottom) // 2
            # ขยาย Range ให้กว้างขึ้นนิดหน่อย เผื่อปุ่มเลื่อนอยู่เหลื่อมกัน
            min_y = center_y - 200
            max_y = center_y + 200
        
        # 2. ค้นหา Candidates
        candidates = []
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        
        visible_candidates = [c for c in candidates if c.is_visible()]
        if not visible_candidates: return None
        
        win_rect = window.rectangle()
        valid_scroll_btns = []
        
        for c in visible_candidates:
            aid = c.element_info.automation_id
            text = c.window_text()
            r = c.rectangle()
            center_y_c = (r.top + r.bottom) // 2
            
            # กรอง Blacklist ทิ้ง
            if any(b in aid for b in blacklist_ids):
                continue

            # เงื่อนไขพื้นฐาน: อยู่ขวา และอยู่ในระดับความสูง
            is_right_side = r.left > win_rect.left + (win_rect.width() * 0.85)
            is_in_y_range = min_y < center_y_c < max_y
            is_small = r.width() < 120 # ปุ่มเลื่อนต้องไม่ใหญ่มาก

            # ให้คะแนนความน่าจะเป็น
            score = 0
            if is_right_side and is_in_y_range: score += 1
            if is_small: score += 1
            if ">" in text or "Arrow" in aid or "Scroll" in aid or "Next" in aid: score += 5
            
            if score >= 2: # ต้องผ่านเกณฑ์อย่างน้อย 2 ข้อ
                valid_scroll_btns.append((score, c))

        if valid_scroll_btns:
             # เรียงตามคะแนน (มากไปน้อย) และตามตำแหน่งขวาสุด
             valid_scroll_btns.sort(key=lambda x: (x[0], x[1].rectangle().left), reverse=True)
             best_btn = valid_scroll_btns[0][1]
             log(f"      [Smart Scroll] เจอปุ่มเลื่อน! (ID: {best_btn.element_info.automation_id} | Score: {valid_scroll_btns[0][0]})")
             return best_btn
        
        log("      [Smart Scroll] ไม่เจอปุ่มเลื่อนที่เหมาะสม")     
        return None
    except Exception as e:
        log(f"Error finding scroll: {e}")
        return None

def find_and_click_safe_zone(window, target_id, max_attempts=20):
    """
    เลื่อนหาปุ่มจนกว่าจะเข้ามาอยู่ใน Safe Zone
    """
    log(f"...กำลังค้นหาปุ่ม '{target_id}' และจัดตำแหน่ง...")
    
    last_rect_left = -1
    stuck_counter = 0
    force_keyboard_mode = False

    for i in range(max_attempts):
        # 1. ค้นหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if c.element_info.automation_id == target_id and c.is_visible()]
        
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # Safe Zone: ต้องไม่อยู่ชิดขอบขวา (ไม่เกิน 75% ของหน้าจอ)
            safe_limit = win_rect.left + (win_rect.width() * 0.75) 
            
            log(f"   [Check {i+1}] ปุ่มอยู่ที่ X={rect.left} (Safe Limit: {int(safe_limit)})")
            
            # เช็คว่าปุ่มขยับไหม
            if abs(rect.left - last_rect_left) < 5 and i > 0:
                stuck_counter += 1
                if stuck_counter >= 2:
                    log("   [!] ปุ่มไม่ขยับเลย -> เปลี่ยนไปใช้ Keyboard Scroll ทันที")
                    force_keyboard_mode = True
            else:
                stuck_counter = 0
            
            last_rect_left = rect.left

            if rect.right < safe_limit:
                log(f"   [/] ปุ่มอยู่ใน Safe Zone -> เห็นเต็มใบ -> คลิก!")
                time.sleep(0.5)
                try:
                    target.click_input()
                    return True
                except:
                    log("   [!] คลิกไม่ติด (อาจมีอะไรบัง) -> ลองกด Enter ใส่")
                    target.set_focus()
                    window.type_keys("{ENTER}")
                    return True
            else:
                log(f"   [!] ปุ่มอยู่ลึกไปทางขวา -> ต้องเลื่อนซ้ายเข้ามา")
        else:
            log(f"   [Check {i+1}] ยังไม่เห็นปุ่มเป้าหมาย -> ต้องเลื่อนหา")
            force_keyboard_mode = True # ถ้าไม่เห็นเลย ให้ใช้คีย์บอร์ดนำร่องไปก่อน

        # 2. สั่งเลื่อน (Scroll)
        if force_keyboard_mode:
            log("      -> ใช้ Keyboard {RIGHT} (Force Mode)")
            window.type_keys("{RIGHT}")
        else:
            scroll_btn = find_smart_scroll_button(window)
            if scroll_btn:
                try:
                    scroll_btn.click_input()
                except:
                    log("      -> กดปุ่มเลื่อน Error -> ใช้ Keyboard แทน")
                    window.type_keys("{RIGHT}")
            else:
                log("      -> หาปุ่มเลื่อนไม่เจอ -> ใช้ Keyboard {RIGHT}")
                window.type_keys("{RIGHT}")
            
        time.sleep(1.0) # รอ Animation เลื่อน
        
    log("[Fail] หมดความพยายามในการเลื่อนหา")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (Smart Scroll - Help Filtered) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ
    target_service_id = "ShippingService_2583" 
    
    if not find_and_click_safe_zone(main_window, target_service_id):
        log(f"[Error] ไม่สามารถกดปุ่ม {target_service_id} ได้")
        return

    # [ส่วน Popup]
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(1.0)
    main_window.type_keys("{ENTER}")

    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    time.sleep(1.5)

    popup_window = None
    try:
        app_top = Application(backend="uia").connect(active_only=True).top_window()
        # เช็คว่าเป็น Popup จริงไหม (ต้องไม่ใช่หน้าหลัก)
        if ("จำนวน" in app_top.window_text() or app_top.element_info.control_type == "Window") and "Riposte" not in app_top.window_text():
            popup_window = app_top
    except: pass
    
    if not popup_window:
        try:
            # ลองหา Child Window ตัวแรก
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
        log("[Error] หา Popup ไม่เจอ (อาจจะกดปุ่มบริการไม่ติด)")

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