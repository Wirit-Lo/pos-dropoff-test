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
        # สร้าง Dummy config เพื่อให้รันเทสได้ถ้าไม่มีไฟล์
        return {'PRODUCT_QUANTITY': {'Quantity': '1'}, 'APP': {'WindowTitle': 'Escher Retail'}}
    config.read(file_path, encoding='utf-8')
    return config

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

# ================= 2. Helper Functions (ปรับปรุงใหม่) =================
def find_scroll_button_strict(window):
    """
    ค้นหาปุ่มเลื่อน (Scroll) แบบปรับปรุงใหม่ ให้รองรับ UI ตามภาพ
    เน้นหาปุ่มลูกศร '>' ที่อยู่ในโซนกลางค่อนขวา
    """
    try:
        win_rect = window.rectangle()
        win_w = win_rect.width()
        win_h = win_rect.height()

        # --- Zone Configuration ---
        # 1. ตัด Header ด้านบน (20% บน)
        min_y = win_rect.top + (win_h * 0.20)
        # 2. ตัด Footer ด้านล่าง (20% ล่าง - ปุ่ม Payment/Back อยู่แถวนี้)
        max_y = win_rect.top + (win_h * 0.80)
        # 3. เริ่มหาตั้งแต่กลางจอไปทางขวา (ลดจาก 0.85 เป็น 0.55 เพราะมี Panel ขวาสุดบังอยู่)
        min_x = win_rect.left + (win_w * 0.55)
        # 4. ไม่หาเกินขอบ Panel ขวาสุด (สมมติ Panel ขวา กินพื้นที่ 20%)
        max_x = win_rect.left + (win_w * 0.95)

        # รายชื่อ ID ที่ห้ามกด
        blacklist_ids = ["ShowHelpText", "ServiceGroupShowHelpText", "Help", "Info", 
                         "Total", "Summary", "Cart", "Payment", "Notification", "GlobalCommand"]

        candidates = []
        # หาปุ่มและ Image ทั้งหมด
        candidates.extend(window.descendants(control_type="Button"))
        candidates.extend(window.descendants(control_type="Image"))
        candidates.extend(window.descendants(control_type="Text")) # บางทีลูกศรเป็น Text
        
        valid_buttons = []
        for btn in candidates:
            if not btn.is_visible(): continue
            
            r = btn.rectangle()
            center_y = (r.top + r.bottom) // 2
            center_x = (r.left + r.right) // 2
            
            try:
                aid = btn.element_info.automation_id
                text = btn.window_text()
                # บางที name จะเก็บค่า text ไว้
                name = btn.element_info.name 
            except:
                continue

            # กฏที่ 1: ต้องอยู่ในโซนความสูงที่กำหนด (Middle Band)
            if center_y < min_y or center_y > max_y: continue
            
            # กฏที่ 2: ต้องอยู่ด้านขวาตามกำหนด
            if center_x < min_x: continue
            
            # กฏที่ 2.1: ต้องไม่อยู่ขวาสุดเกินไป (ไปโดนปุ่มใน Panel สรุปยอด)
            # if center_x > max_x: continue 

            # กฏที่ 3: ห้ามติด Blacklist
            if aid and any(b in aid for b in blacklist_ids): continue
            
            # กฏที่ 4: ขนาดปุ่มต้องไม่ใหญ่เกินไป (ปุ่ม Scroll มักจะเล็กหรือเป็นสี่เหลี่ยมจัตุรัส)
            if r.width() > 150 or r.height() > 150: continue

            # --- Scoring System ---
            score = 0
            
            # High Priority: สัญลักษณ์ลูกศร
            if text == ">" or name == ">": score += 20
            if "Right" in str(aid) or "NextPage" in str(aid): score += 15
            if "Scroll" in str(aid) or "Arrow" in str(aid): score += 10
            
            # Position Priority: ยิ่งอยู่ขวายิ่งดี (แต่ไม่เกินขอบเขต)
            # ให้คะแนนตามความขวา (Normalize 0-1)
            pos_score = (center_x - min_x) / (win_w * 0.4) * 5
            score += pos_score

            valid_buttons.append((score, btn))
        
        if valid_buttons:
            # เรียงตามคะแนนมากสุด
            valid_buttons.sort(key=lambda x: x[0], reverse=True)
            best_btn = valid_buttons[0][1]
            
            # Debug Log
            r = best_btn.rectangle()
            log(f"   [Found] เจอ Scroll Candidate: ID='{best_btn.element_info.automation_id}' Text='{best_btn.window_text()}' Score={valid_buttons[0][0]}")
            return best_btn
            
    except Exception as e:
        log(f"Error finding scroll button: {e}")
    
    return None

def force_click_right_side(window):
    """
    Fallback: ถ้าหาปุ่มไม่เจอจริงๆ ให้คลิกที่ตำแหน่งพิกัด (Blind Click)
    ตำแหน่ง: ขอบขวาของโซนแสดงรายการ (ประมาณ 75% ของความกว้างจอ, กึ่งกลางแนวตั้ง)
    """
    try:
        rect = window.rectangle()
        # จุด X: 78% ของจอ (น่าจะเป็นตำแหน่งปุ่มลูกศรขวา ก่อนถึง Panel สรุปยอด)
        target_x = rect.left + int(rect.width() * 0.78)
        # จุด Y: 50% กึ่งกลางจอ
        target_y = rect.top + int(rect.height() * 0.50)
        
        log(f"   [Fallback] หาปุ่มไม่เจอ -> บังคับคลิกที่พิกัด ({target_x}, {target_y})")
        window.click_input(coords=(target_x, target_y))
        return True
    except Exception as e:
        log(f"Force click failed: {e}")
        return False

def find_and_click_with_rotate_logic(window, target_id, max_rotations=10):
    """
    ค้นหาปุ่มแบบ Rotate Loop
    """
    log(f"...ค้นหา ID '{target_id}' (โหมดเลื่อนหาไว)...")
    
    for i in range(1, max_rotations + 1):
        # 1. ลองหาปุ่มเป้าหมาย
        found = [c for c in window.descendants() if str(c.element_info.automation_id) == target_id and c.is_visible()]
        
        if found:
            target = found[0]
            rect = target.rectangle()
            win_rect = window.rectangle()
            
            # Safe Zone Check
            # ในรูป Panel ขวาบังอยู่ -> limit ขอบขวาที่ 75% ของจอ
            safe_right_limit = win_rect.left + (win_rect.width() * 0.75) 
            
            if rect.right < safe_right_limit:
                 log(f"   [/] เจอ '{target_id}' ใน Safe Zone -> คลิก")
                 try:
                    target.click_input()
                 except:
                    target.set_focus()
                    window.type_keys("{ENTER}")
                 return True
            else:
                 log(f"   [Rotate {i}] เจอ '{target_id}' แต่อยู่ชิดขอบขวา/โดนบัง -> ต้องเลื่อน (Scroll)")
        else:
            log(f"   [Rotate {i}] ไม่เจอ '{target_id}' -> เลื่อนหา (Scroll)")
        
        # 2. สั่งเลื่อน (Scroll)
        scroll_btn = find_scroll_button_strict(window)
        if scroll_btn:
            try:
                scroll_btn.click_input()
            except:
                log("   [Error] คลิกปุ่ม Scroll ไม่ติด -> ลองใช้ Fallback Coordinate")
                force_click_right_side(window)
        else:
            # ถ้าหาปุ่มไม่เจอเลย ใช้ไม้ตาย: คลิกพิกัดเอาดื้อๆ
            if not force_click_right_side(window):
                window.type_keys("{RIGHT}")
            
        time.sleep(1.5) # รอ Animation เลื่อน (สำคัญมาก ถ้าน้อยไป UI อัปเดตไม่ทัน)
        
    log(f"[X] หมดความพยายามในการหาปุ่ม '{target_id}'")
    return False

# ================= 3. Main Test Logic =================
def test_popup_process(main_window, config):
    log("--- เริ่มทดสอบ (Rotate Logic & Strict Scroll) ---")
    
    # 1. ค้นหาและกดปุ่มบริการ
    # ตัวอย่าง ID: ShippingService_2583 หรือ ID อื่นตามหน้างาน
    target_service_id = "ShippingService_2583" 
    
    # ลอง Print ID ปุ่มทั้งหมดออกมาดู เพื่อหา ID ที่ถูกต้อง (Uncomment เพื่อ Debug)
    # btns = main_window.descendants(control_type="Button")
    # for b in btns:
    #     if b.rectangle().width() > 50: # กรองปุ่มเล็กๆทิ้ง
    #         print(f"ID: {b.element_info.automation_id} | Text: {b.window_text()}")

    if not find_and_click_with_rotate_logic(main_window, target_service_id):
        log(f"[Error] ไม่สามารถกดปุ่ม {target_service_id} ได้")
        return

    # [ส่วน Popup เดิม - ตามโค้ดที่คุณส่งมา]
    log("...กด Enter (ถัดไป) เพื่อเรียก Popup...")
    time.sleep(1.0)
    main_window.type_keys("{ENTER}")

    qty = config['PRODUCT_QUANTITY'].get('Quantity', '1') if 'PRODUCT_QUANTITY' in config else '1'
    log(f"...รอ Popup 'จำนวน' (ค่า: {qty})...")
    time.sleep(1.5)

    popup_window = None
    try:
        app_top = Application(backend="uia").connect(active_only=True).top_window()
        # เช็คชื่อ Window หรือ Control Type
        if ("จำนวน" in app_top.window_text() or app_top.element_info.control_type == "Window"):
            popup_window = app_top
    except: pass
    
    if not popup_window:
        try:
            children = main_window.children(control_type="Window")
            if children: popup_window = children[0]
        except: pass

    if popup_window:
        try: 
            popup_window.set_focus()
            log(f"   [Popup] เจอ Popup: {popup_window.window_text()}")
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
                target_edit.type_keys("^a{DELETE}", pause=0.1) # Select All -> Delete
                time.sleep(0.1)
                target_edit.type_keys(str(qty), with_spaces=True)
                popup_window.type_keys("{ENTER}")
                log("-> พิมพ์เลขและกด Enter (ถัดไป) เรียบร้อย")
            except Exception as e:
                log(f"Error interacting with edit: {e}")
        else:
            log("[Warning] ไม่เจอช่อง Edit -> พิมพ์ใส่ Window เลย")
            popup_window.type_keys(str(qty), with_spaces=True)
            popup_window.type_keys("{ENTER}")
    else:
        log("[Error] หา Popup ไม่เจอ (หรืออาจจะไม่มี Popup ขึ้น)")

    log("--- จบการทดสอบ ---")

# ================= 4. Run =================
if __name__ == "__main__":
    conf = load_config()
    if conf:
        try:
            app_title = conf['APP'].get('WindowTitle', 'Escher Retail') # ใส่ Default กัน Error
            log(f"Connecting to: {app_title}")
            
            # เชื่อมต่อ Application
            try:
                app = Application(backend="uia").connect(title_re=app_title, timeout=10)
            except:
                # กรณีหาชื่อไม่เจอ ลอง connect active window (เฉพาะตอน Test)
                log("หา Window Title ไม่เจอ -> ลอง Connect Active Window")
                app = Application(backend="uia").connect(active_only=True)

            main_window = app.top_window()
            main_window.set_focus()
            
            test_popup_process(main_window, conf)
            
        except Exception as e:
            log(f"Error Connect: {e}")