import os
import glob

# ==============================================================================
# 🎯 เป้าหมาย: ทุกไฟล์ .py
# ==============================================================================
target_files = glob.glob("**/*.py", recursive=True)
me = os.path.basename(__file__)
target_files = [f for f in target_files if f != me]

# ==============================================================================
# ✨ โค้ดใหม่ (Clean Code Template)
# ==============================================================================
def get_clean_code(indent, window_var):
    return [
        f"{indent}# [Dynamic Next] ตรวจสอบบริการพิเศษเพื่อกำหนดจำนวนครั้งการกด\n",
        f"{indent}try:\n",
        f"{indent}    config\n",
        f"{indent}except NameError:\n",
        f"{indent}    import configparser\n",
        f"{indent}    config = configparser.ConfigParser()\n",
        f"{indent}    config.read('config.ini', encoding='utf-8')\n",
        f"\n",
        f"{indent}special_services = config['SPECIAL_SERVICES'].get('Services', '').strip()\n",
        f"{indent}loop_count = 3 if special_services else 1\n",
        f"\n",
        f"{indent}log(f\"...จบขั้นตอนข้อมูลผู้รับ (Services='{{special_services}}') -> กด 'ถัดไป' {{loop_count}} ครั้ง...\")\n",
        f"{indent}for i in range(loop_count):\n",
        f"{indent}    log(f\"   -> Enter ครั้งที่ {{i+1}}\")\n",
        f"{indent}    smart_next({window_var}); time.sleep(1.8)\n"
    ]

# ==============================================================================
# 🚀 เริ่มทำงาน
# ==============================================================================
print(f"🚀 เริ่มต้น V7 Nuclear Cleanup (เป้าหมาย: {len(target_files)} ไฟล์)")
print("-" * 60)

success_count = 0
skip_count = 0
error_count = 0

for filepath in target_files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        i = 0
        file_modified = False
        
        while i < len(lines):
            line = lines[i]
            
            # 1. หาจุดเริ่มต้น: # [Dynamic Next]
            if "# [Dynamic Next]" in line:
                start_index = i
                
                # เก็บ Indentation (ย่อหน้า) จากบรรทัดนี้
                indent = line.split('#')[0]
                
                # 2. หาจุดสิ้นสุด: time.sleep(1.8)
                # วิ่งหาไปเรื่อยๆ จนกว่าจะเจอ หรือหมดไฟล์
                end_index = -1
                window_var = "window" # Default fallback
                
                for j in range(start_index, len(lines)):
                    # หาชื่อตัวแปร window จากบรรทัด smart_next (ถ้ามี)
                    if "smart_next(" in lines[j]:
                        parts = lines[j].split("smart_next(")
                        if len(parts) > 1:
                            var_part = parts[1].split(")")[0]
                            window_var = var_part.strip()

                    # หาจุดจบ
                    if "time.sleep(1.8)" in lines[j]:
                        end_index = j
                        break
                
                # ถ้าเจอครบทั้งคู่ (หัว-ท้าย)
                if end_index != -1:
                    # สร้างบล็อกโค้ดใหม่
                    clean_block = get_clean_code(indent, window_var)
                    new_lines.extend(clean_block)
                    
                    # กระโดดข้ามบรรทัดเดิมทั้งหมด (ลบไส้ในที่มีช่องว่างทิ้ง)
                    i = end_index + 1
                    file_modified = True
                    continue
                else:
                    # ถ้าหาจุดจบไม่เจอ ก็ปล่อยบรรทัดนี้ไว้เหมือนเดิม
                    new_lines.append(line)
                    i += 1
            else:
                new_lines.append(line)
                i += 1

        if file_modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            success_count += 1
        else:
            skip_count += 1

    except Exception as e:
        print(f"🔥 Error {filepath}: {e}")
        error_count += 1

print("-" * 60)
print(f"สรุปผล V7: แก้ไขสำเร็จ {success_count} ไฟล์ | ไม่พบจุดแก้ {skip_count} | Error {error_count}")