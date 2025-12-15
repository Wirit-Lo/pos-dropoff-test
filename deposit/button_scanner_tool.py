import time
import os
from pywinauto import Desktop, Application

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*100)
    print("   UI ELEMENT SCANNER - ค้นหา ID ของปุ่ม (Button) และปุ่มเลื่อน (Scroll)")
    print("="*100)

    # 1. เชื่อมต่อกับหน้าต่าง
    print("\n[Step 1] กำลังเชื่อมต่อกับหน้าต่าง...")
    target_window = None
    
    # วิธี A: ลองหาหน้าต่าง POS ด้วยชื่อที่น่าจะเป็น
    try:
        regex_title = ".*Escher.*|.*POS.*|.*Retail.*|.*Riposte.*"
        app = Application(backend="uia").connect(title_re=regex_title, timeout=2)
        target_window = app.top_window()
        print(f" -> [Auto] เจอหน้าต่างโปรแกรม POS: '{target_window.window_text()}'")
    except:
        # วิธี B: ถ้าไม่เจอ ให้เอาหน้าต่างที่ Active อยู่
        try:
            print(" -> [Auto] ไม่เจอ POS โดยตรง -> กำลังจับหน้าต่างที่ Active ล่าสุด...")
            print("    (กรุณาคลิกที่หน้าต่าง POS ภายใน 3 วินาที ถ้ายังไม่ได้เลือก)")
            time.sleep(3)
            
            app = Application(backend="uia").connect(active_only=True)
            target_window = app.top_window()
            print(f" -> [Active] เป้าหมายคือหน้าต่าง: '{target_window.window_text()}'")
        except Exception as e:
            print(f"[Error] ไม่สามารถจับหน้าต่างได้: {e}")

    if not target_window:
        print("\n[!] ไม่พบหน้าต่างเป้าหมายเลย ลองดูรายชื่อหน้าต่างที่เปิดอยู่:")
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            for w in windows:
                if w.is_visible() and w.window_text():
                    print(f"   - {w.window_text()}")
        except: pass
        return

    # 2. สแกนหาปุ่ม
    print(f"\n[Step 2] กำลังสแกนหา Elements ในหน้าต่าง '{target_window.window_text()}'...")
    print("   (เน้น Button และ Image เพื่อหาปุ่มเลื่อน...)\n")

    try:
        # ดึง Button และ Image (เผื่อปุ่มเลื่อนเป็น Image)
        buttons = target_window.descendants(control_type="Button")
        images = target_window.descendants(control_type="Image")
        
        # รวมรายการและกรองเฉพาะที่มองเห็น
        all_elements = buttons + images
        visible_elements = [e for e in all_elements if e.is_visible()]

        print(f" -> พบ Elements ทั้งหมด: {len(all_elements)}")
        print(f" -> ที่มองเห็นได้ (Visible): {len(visible_elements)}\n")

        # 3. แสดงรายงาน (Report)
        header = f"{'IDX':<5} | {'TYPE':<8} | {'TEXT / NAME':<20} | {'AUTOMATION_ID':<35} | {'COORDS (L, T, R, B)':<20} | {'NOTE'}"
        print("-" * 120)
        print(header)
        print("-" * 120)

        win_rect = target_window.rectangle()
        win_width = win_rect.width()
        right_zone_x = win_rect.left + (win_width * 0.75) # โซนขวาสุด 25%

        for idx, elem in enumerate(visible_elements):
            try:
                # ดึงค่าต่างๆ
                etype = "Button" if elem.element_info.control_type == "Button" else "Image"
                text = elem.window_text().strip()
                auto_id = elem.element_info.automation_id
                rect = elem.rectangle()
                
                coords = f"{rect.left},{rect.top},{rect.right},{rect.bottom}"
                
                # ถ้าไม่มี Text ลองดูข้างใน
                if not text:
                    children = elem.children()
                    if children:
                        try: text = f"[{children[0].element_info.control_type}]"
                        except: text = "(No Text)"
                    else:
                        text = "(No Text)"

                # ตัดคำ
                disp_text = (text[:18] + '..') if len(text) > 18 else text
                disp_id = (auto_id[:32] + '..') if len(auto_id) > 32 else auto_id

                # Logic วิเคราะห์ปุ่ม
                note = ""
                
                # 1. เช็คว่าเป็นปุ่มเลื่อนหรือไม่ (อยู่ขวาสุด + ขนาดเล็ก + keywords)
                is_right_side = rect.left > right_zone_x
                is_small_width = rect.width() < 120
                keywords = [">", "next", "scroll", "arrow", "page", "right"]
                has_keyword = any(k in auto_id.lower() or k in text.lower() for k in keywords)

                if is_right_side and (is_small_width or has_keyword):
                    note = "<<< ปุ่มเลื่อน (Scroll)?"
                elif "Shipping" in auto_id:
                    note = "<<< บริการขนส่ง"
                elif "Arrow" in auto_id:
                    note = "<<< ไอคอนลูกศร"

                print(f"{idx:<5} | {etype:<8} | {disp_text:<20} | {disp_id:<35} | {coords:<20} | {note}")
                
            except Exception as e:
                pass

        print("-" * 120)
        print("\nวิธีดู:")
        print("1. มองหาบรรทัดที่มี Note ว่า '<<< ปุ่มเลื่อน (Scroll)?'")
        print("2. เช็ค COORDS ว่าอยู่ด้านขวาของจอหรือไม่ (ค่าแรก > 1000+)")
        print("3. จด AutomationID ไปใช้ในสคริปต์")
        
    except Exception as e:
        print(f"Error scanning: {e}")

    input("\nกด Enter เพื่อจบการทำงาน...")

if __name__ == "__main__":
    main()