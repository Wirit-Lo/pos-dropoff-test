import time
from pywinauto import Desktop

def main():
    print("="*70)
    print("   UI TREE DUMPER - ดึงข้อมูลปุ่มทั้งหมดในหน้าจอ   ")
    print("="*70)

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
    print(f"\n[Step 2] กำลังสแกนองค์ประกอบภายใน '{target_window.window_text()}'...")
    print("(อาจใช้เวลาสักครู่...)\n")

    try:
        # ดึงปุ่ม (Button)
        buttons = target_window.descendants(control_type="Button")
        # ดึงรายการ (ListItem) - เมนูบริการมักจะเป็นอันนี้
        list_items = target_window.descendants(control_type="ListItem")
        # ดึงรูปภาพ (Image) - เผื่อปุ่มเป็นรูปภาพ
        images = target_window.descendants(control_type="Image")

        all_elements = []
        # รวมกลุ่มและแปะป้ายประเภท
        for b in buttons: all_elements.append(("Button", b))
        for l in list_items: all_elements.append(("ListItem", l))
        for i in images: all_elements.append(("Image", i))

        # กรองเฉพาะที่มองเห็น (Visible)
        visible_elements = [x for x in all_elements if x[1].is_visible()]

        print("-" * 100)
        print(f"{'INDEX':<6} | {'TYPE':<10} | {'TEXT (ชื่อที่เห็น)':<25} | {'AUTOMATION_ID':<20} | {'POSITION (x,y)'}")
        print("-" * 100)

        found_count = 0
        for idx, (etype, elem) in enumerate(visible_elements):
            try:
                # ดึงค่าต่างๆ
                text = elem.window_text().strip()
                auto_id = elem.element_info.automation_id
                rect = elem.rectangle()
                pos_str = f"({rect.left}, {rect.top})"
                
                # ถ้าไม่มีชื่อ ให้ลองดูชื่อของลูก (Child) เผื่อมี Text ซ่อนอยู่ข้างใน
                if not text:
                    children = elem.children()
                    for child in children:
                        child_txt = child.window_text().strip()
                        if child_txt:
                            text = f"[{child_txt}]" # ใส่ [] เพื่อบอกว่าเป็นชื่อลูก
                            break
                
                # แสดงผลเฉพาะที่มีข้อมูลน่าสนใจ (ตัดพวกปุ่มว่างๆ ไร้สาระออกได้ ถ้าต้องการ)
                # แต่รอบนี้จะโชว์หมดเพื่อให้เห็นครบ
                print(f"{idx:<6} | {etype:<10} | {text[:25]:<25} | {auto_id[:20]:<20} | {pos_str}")
                found_count += 1
                
            except Exception as e:
                print(f"{idx:<6} | {etype:<10} | <Error reading> | ...")

        print("-" * 100)
        print(f"\nสรุป: เจอทั้งหมด {found_count} รายการ")
        print("คำแนะนำ:")
        print("1. มองหาบรรทัดที่มีคำว่า 'EMS' หรือ 'บริการ'")
        print("2. ถ้าเจอ 'AutomationId' ให้ก๊อปไปใช้เลย (แม่นยำที่สุด)")
        print("3. ถ้าไม่มี ID ให้ดู 'Index' แล้วใช้คำสั่งกดตามลำดับแทน")
        
    except Exception as e:
        print(f"Error scanning window: {e}")

    input("\nกด Enter เพื่อปิดโปรแกรม...")

if __name__ == "__main__":
    main()