import time
from pywinauto import Desktop

def main():
    print("="*80)
    print("   UI ELEMENT SCANNER - สแกนหา ID ของปุ่มและช่องกรอกข้อมูล   ")
    print("="*80)

    # 1. ค้นหาหน้าต่าง POS อัตโนมัติ
    print("\n[Step 1] กำลังค้นหาหน้าต่างโปรแกรม...")
    desktop = Desktop(backend="uia")
    windows = desktop.windows()
    
    target_window = None
    for w in windows:
        if w.is_visible():
            txt = w.window_text()
            # กรองหาชื่อที่น่าจะเป็น POS (แก้ตรงนี้ได้ถ้าชื่อไม่ตรง)
            if "Escher" in txt or "Retail" in txt or "POS" in txt:
                target_window = w
                print(f" -> เจอเป้าหมาย: '{txt}'")
                break
    
    if not target_window:
        print("\n[!] ไม่พบหน้าต่าง POS (กรุณาเปิดโปรแกรมทิ้งไว้ก่อนรัน)")
        print("    รายชื่อหน้าต่างที่เจอในเครื่อง:")
        for w in windows:
            if w.is_visible() and w.window_text().strip():
                print(f"    - {w.window_text()}")
        return

    # 2. สแกนหาปุ่มและลิสต์ไอเท็ม
    print(f"\n[Step 2] กำลังดึงข้อมูลปุ่มและช่องกรอกทั้งหมดใน '{target_window.window_text()}'...")
    print("(อาจใช้เวลาสักครู่...)\n")

    try:
        # ดึง Element ที่น่าสนใจ
        # เราเน้น Button (ปุ่ม), Edit (ช่องกรอก), Image (รูปภาพ/ไอคอน), Text (ข้อความ)
        buttons = target_window.descendants(control_type="Button")
        edits = target_window.descendants(control_type="Edit")
        images = target_window.descendants(control_type="Image")
        
        all_elements = []
        for b in buttons: all_elements.append(("Button", b))
        for e in edits: all_elements.append(("Edit", e))
        for i in images: all_elements.append(("Image", i))

        # กรองเฉพาะที่มองเห็น (Visible)
        visible_elements = [x for x in all_elements if x[1].is_visible()]

        # หัวตาราง
        header = f"{'IDX':<4} | {'TYPE':<8} | {'TEXT (ชื่อ/ค่า)':<20} | {'AUTOMATION_ID':<30} | {'POS (x,y)'}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        found_count = 0
        for idx, (etype, elem) in enumerate(visible_elements):
            try:
                # ดึงค่าต่างๆ
                text = elem.window_text().strip()
                auto_id = elem.element_info.automation_id
                rect = elem.rectangle()
                pos_str = f"({rect.left}, {rect.top})"
                
                # ถ้าไม่มีชื่อ ลองดูชื่อของลูก (Child) เผื่อเป็นไอคอนที่มี text ซ่อน
                if not text and etype == "Button":
                    children = elem.children()
                    for child in children:
                        child_txt = child.window_text().strip()
                        if child_txt:
                            text = f"[{child_txt}]"
                            break
                
                # ตัดข้อความยาวๆ
                display_text = (text[:18] + '..') if len(text) > 18 else text
                display_id = (auto_id[:28] + '..') if len(auto_id) > 28 else auto_id

                # เน้นรายการที่น่าสนใจ (เช่น ช่องกรอกเงิน หรือ ปุ่มบวก)
                highlight = ""
                if etype == "Edit": highlight = " <--- ช่องกรอก?"
                if text == "+" or "Plus" in auto_id or "Add" in auto_id: highlight = " <--- ปุ่มบวก?"
                
                print(f"{idx:<4} | {etype:<8} | {display_text:<20} | {display_id:<30} | {pos_str} {highlight}")
                found_count += 1
                
            except Exception as e:
                pass

        print("-" * len(header))
        print(f"\nสรุป: เจอทั้งหมด {found_count} รายการ")
        print("วิธีดู:")
        print("3. จด AutomationId ไปใส่ในโค้ด")
        
    except Exception as e:
        print(f"Error scanning window: {e}")

    input("\nกด Enter เพื่อปิดโปรแกรม...")

if __name__ == "__main__":
    main()