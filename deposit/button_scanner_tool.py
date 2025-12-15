import time
import os
from pywinauto import Desktop, Application

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*100)
    print("   BUTTON INSPECTOR - เครื่องมือค้นหา ID และพิกัดปุ่ม (Button Only)")
    print("="*100)

    # 1. เชื่อมต่อกับหน้าต่าง
    print("\n[Step 1] กำลังเชื่อมต่อกับหน้าต่าง...")
    target_window = None
    
    # วิธี A: ลองหาหน้าต่าง POS ด้วยชื่อที่น่าจะเป็น (เพิ่ม Riposte ตาม Log เก่า)
    try:
        # เพิ่ม Riposte และชื่ออื่นๆ
        regex_title = ".*Escher.*|.*POS.*|.*Retail.*|.*Riposte.*"
        app = Application(backend="uia").connect(title_re=regex_title, timeout=2)
        target_window = app.top_window()
        print(f" -> [Auto] เจอหน้าต่างโปรแกรม POS: '{target_window.window_text()}'")
    except:
        # วิธี B: ถ้าไม่เจอ ให้เอาหน้าต่างที่ Active อยู่ (วิธีที่แก้ Bug แล้ว)
        try:
            print(" -> [Auto] ไม่เจอ POS โดยตรง -> กำลังจับหน้าต่างที่ Active ล่าสุด...")
            print("    (กรุณาคลิกที่หน้าต่าง POS ภายใน 2 วินาที ถ้ายังไม่ได้เลือก)")
            time.sleep(2)
            
            # แก้ไข: ใช้ connect(active_only=True) แทน desktop.active_window()
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
        print("\nคำแนะนำ: เปิดโปรแกรม POS ค้างไว้ แล้วรันสคริปต์นี้ใหม่อีกครั้ง")
        return

    # 2. สแกนหาปุ่ม
    print(f"\n[Step 2] กำลังสแกนหา 'Button' ทั้งหมดในหน้าต่าง '{target_window.window_text()}'...")
    print("   (กรุณารอสักครู่ อาจใช้เวลา 5-10 วินาที หากมีปุ่มเยอะ)...\n")

    try:
        # ดึงเฉพาะ Button
        buttons = target_window.descendants(control_type="Button")
        
        # กรองเฉพาะปุ่มที่มองเห็น (Visible) เพื่อไม่ให้สับสน
        visible_buttons = [b for b in buttons if b.is_visible()]

        print(f" -> พบปุ่มทั้งหมด: {len(buttons)} ปุ่ม")
        print(f" -> ปุ่มที่มองเห็นได้ (Visible): {len(visible_buttons)} ปุ่ม\n")

        # 3. แสดงรายงาน (Report)
        # จัด Format ตาราง
        header = f"{'IDX':<5} | {'TEXT / NAME':<25} | {'AUTOMATION_ID':<35} | {'COORDS (L, T, R, B)':<20} | {'SIZE (WxH)'}"
        print("-" * 110)
        print(header)
        print("-" * 110)

        for idx, btn in enumerate(visible_buttons):
            try:
                # ดึงค่าต่างๆ
                text = btn.window_text().strip()
                auto_id = btn.element_info.automation_id
                rect = btn.rectangle()
                
                coords = f"{rect.left}, {rect.top}, {rect.right}, {rect.bottom}"
                size = f"{rect.width()} x {rect.height()}"

                # ถ้าปุ่มไม่มี Text ลองดูข้างในเผื่อเป็น Icon
                if not text:
                    children = btn.children()
                    if children:
                        try:
                            text = f"[{children[0].element_info.control_type}]"
                        except:
                            text = "[Icon]"
                    else:
                        text = "(No Text)"

                # ตัดคำถ้าข่อยาวเกินไป
                disp_text = (text[:22] + '..') if len(text) > 22 else text
                disp_id = (auto_id[:32] + '..') if len(auto_id) > 32 else auto_id

                # Highlight ปุ่มที่น่าสนใจ
                # เช่น ปุ่มที่มีคำว่า > หรือ Next หรือ ID มีคำว่า Scroll/Page
                note = ""
                if ">" in text or "Next" in text or "Scroll" in auto_id or "Arrow" in auto_id:
                    note = " <--- ปุ่มเลื่อน??"
                if "Shipping" in auto_id:
                    note = " <--- ปุ่มบริการ"

                print(f"{idx:<5} | {disp_text:<25} | {disp_id:<35} | {coords:<20} | {size} {note}")
                
            except Exception as e:
                print(f"{idx:<5} | Error reading element: {e}")

        print("-" * 110)
        print("\nคำแนะนำการหาปุ่มเลื่อน:")
        print("1. ดูคอลัมน์ COORDS ค่าแรก (Left) และค่าที่สาม (Right) ที่มีค่าสูงๆ (ด้านขวาของจอ)")
        print("2. ดูคอลัมน์ SIZE ที่ขนาดไม่กว้างมาก (เช่น 40x80, 50x50)")
        print("3. มองหา TEXT ที่เป็น '>' หรือ AutomationID ที่เกี่ยวกับ 'Arrow', 'Scroll', 'Next'")
        
    except Exception as e:
        print(f"Error scanning: {e}")

    input("\nกด Enter เพื่อจบการทำงาน...")

if __name__ == "__main__":
    main()