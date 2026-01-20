import os
import re

# ==============================================================================
# 1. รายชื่อไฟล์เป้าหมาย (เฉพาะที่คุณระบุมา)
# ==============================================================================
TARGET_FILES = [
    "Customsize2.py", "Customsize3.py", "Customsize4.py", "Customsize5.py",
    "Customsize6.py", "Customsize7.py", "Customsize8.py", "Customsize9.py",
    "Customsize10.py", "Customsize11.py", "Customsize12.py", "Customsize13.py",
    "Customsize14.py", "Customsize15.py", "Customsize16.py", "Customsize17.py",
    "Customsize18.py", "Customsize19.py", "Customsize20.py", "Customsize21.py",
    "Customsize22.py", "Customsize24.py", "Customsize25.py", "Customsize26.py",
    "Customsize27.py", "Customsize28.py", "Customsize29.py", "Customsize30.py",
    "Customsize31.py", "Customsize32.py", "Customsize33.py", "Customsize34.py",
    "Customsize35.py", "Customsize36.py", "Customsize38.py", "Customsize39.py",
    "Customsize40.py", "Customsize41.py", "Customsize42.py", "Customsize43.py",
    "Customsize44.py", "Customsize45.py", "Customsize46.py", "Customsize47.py",
    "Customsize48.py", "Customsize49.py", "Customsize50.py", "Customsize51.py",
    "Customsize52.py", "Customsize53.py", "Customsize54.py", "Customsize55.py",
    "Customsize58.py", "Customsize62.py", "Customsize63.py", "Customsize64.py",
    "Customsize65.py", "Customsize66.py", "Customsize68.py", "Customsize69.py",
    "Customsize70.py", "Customsize71.py", "Customsize72.py", "Customsize75.py",
    "Customsize76.py", "Customsize77.py", "Customsize78.py", "Customsize79.py",
    "Customsize81.py"
]

# ==============================================================================
# 2. โค้ดที่จะแทรก (Code Blocks)
# ==============================================================================

# ส่วนที่ 1: Config Dimensions
# (ไม่ต้องมีย่อหน้าตรงนี้ เดี๋ยวสคริปต์จะเติมให้เองตามไฟล์ต้นฉบับ)
CODE_BLOCK_1 = """width = config['DEPOSIT_ENVELOPE'].get('Width', '10')
length = config['DEPOSIT_ENVELOPE'].get('Length', '20')
height = config['DEPOSIT_ENVELOPE'].get('Height', '10')"""

# ส่วนที่ 2: Logic กรอกข้อมูล
# (ใส่ {{TAB}} เพื่อให้ f-string ไม่พังใน Python)
CODE_BLOCK_2 = """log(f"...[Step 6] กรอกปริมาตร (กว้าง: {width}, ยาว: {length}, สูง: {height})")
try:
    main_window.set_focus()
    edits = [e for e in main_window.descendants(control_type="Edit") if e.is_visible()]
    if edits:
        edits[0].click_input()
        log("   -> เจอช่องแรก -> เริ่มกรอกและ Tab")
        main_window.type_keys(f"{width}{{TAB}}{length}{{TAB}}{height}", with_spaces=True)
    else:
        log("   [WARN] ไม่เจอ Edit box -> ลองพิมพ์ Blind Type")
        main_window.type_keys(f"{width}{{TAB}}{length}{{TAB}}{height}", with_spaces=True)
except:
     log("   [!] Error กรอกปริมาตร")

smart_next(main_window)
time.sleep(step_delay)"""

# ==============================================================================
# 3. ฟังก์ชั่นการทำงาน
# ==============================================================================

def indent_code(code, indentation):
    """ฟังก์ชั่นเติมย่อหน้าให้โค้ดใหม่ เท่ากับโค้ดเดิม"""
    lines = code.split('\n')
    indented_lines = [indentation + line for line in lines]
    return '\n'.join(indented_lines)

print(f"🚀 เริ่มต้นกระบวนการแทรกโค้ด (จำนวนไฟล์เป้าหมาย: {len(TARGET_FILES)})")
print("-" * 60)

success_count = 0
not_found_count = 0
error_count = 0

for filename in TARGET_FILES:
    if not os.path.exists(filename):
        print(f"⚠️  หาไฟล์ไม่เจอ: {filename} (ข้าม)")
        not_found_count += 1
        continue

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # เช็คว่าเคยแทรกไปแล้วหรือยัง (ป้องกันการแทรกซ้ำ)
        if "config['DEPOSIT_ENVELOPE'].get('Width'" in content and "Step 6" in content:
            print(f"⏩ {filename}: เคยแทรกโค้ดไปแล้ว (ข้าม)")
            continue

        # ------------------------------------------------------------------
        # จุดแทรกที่ 1: ต่อจาก weight = ...
        # Regex จับบรรทัด weight พร้อม Indentation ข้างหน้า (group 1)
        # ------------------------------------------------------------------
        pattern1 = r"(^\s*)weight\s*=\s*config\['DEPOSIT_ENVELOPE'\]\.get\('Weight',\s*'10'\)"
        match1 = re.search(pattern1, content, re.MULTILINE)
        
        if match1:
            indentation = match1.group(1) # จับย่อหน้าของบรรทัดเดิม
            original_line = match1.group(0)
            
            # เตรียมโค้ดใหม่พร้อมย่อหน้าที่ถูกต้อง
            new_code_1 = indent_code(CODE_BLOCK_1, indentation)
            
            # แทนที่: บรรทัดเดิม + ขึ้นบรรทัดใหม่ + โค้ดใหม่
            replacement1 = original_line + "\n" + new_code_1
            content = content.replace(original_line, replacement1)
        else:
            print(f"❌ {filename}: หาจุดแทรกที่ 1 (weight=...) ไม่เจอ")
            error_count += 1
            continue

        # ------------------------------------------------------------------
        # จุดแทรกที่ 2: ต่อจาก smart_input_weight -> smart_next -> sleep(1)
        # ------------------------------------------------------------------
        # Regex จับบล็อก 3 บรรทัดนี้ เพื่อความแม่นยำ 100%
        pattern2 = r"(^\s*)smart_input_weight\(main_window,\s*weight\)\s*\n\s*smart_next\(main_window\)\s*\n\s*time\.sleep\(1\)"
        match2 = re.search(pattern2, content, re.MULTILINE)

        if match2:
            indentation = match2.group(1) # จับย่อหน้า
            original_block = match2.group(0)
            
            # เตรียมโค้ดใหม่พร้อมย่อหน้า
            new_code_2 = indent_code(CODE_BLOCK_2, indentation)
            
            # แทนที่: บล็อกเดิม + ขึ้นบรรทัดใหม่ + โค้ดใหม่
            replacement2 = original_block + "\n\n" + new_code_2
            content = content.replace(original_block, replacement2)
        else:
            print(f"❌ {filename}: หาจุดแทรกที่ 2 (input->next->sleep) ไม่เจอ")
            error_count += 1
            continue

        # บันทึกไฟล์
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ {filename}: แทรกโค้ดสมบูรณ์")
        success_count += 1

    except Exception as e:
        print(f"🔥 Error {filename}: {e}")
        error_count += 1

print("-" * 60)
print(f"สรุป: สำเร็จ {success_count} | หาไฟล์ไม่เจอ {not_found_count} | มีปัญหา/จุดแทรกไม่ตรง {error_count}")