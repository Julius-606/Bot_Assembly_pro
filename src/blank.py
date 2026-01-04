#!/usr/bin/env python3
import os

# ---------------------------------------------------------
# 🧹 THE JANITOR SCRIPT (Linux Line Ending Fixer)
# ---------------------------------------------------------

# The list of files to scrub
target_files = [
    "main.py",
    "config.py",
    "requirements.txt",
    "src/cloud.py",
    "src/broker.py",
    "src/strategy.py"
]

print("🚀 STARTING LINE ENDING SCRUB...")

cleaned_count = 0

for file_path in target_files:
    if os.path.exists(file_path):
        try:
            # 1. Read in binary to find hidden characters
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 2. Aggressively fix ANY Windows/Mac line endings
            # First fix standard Windows CRLF
            fixed_content = content.replace(b'\r\n', b'\n')
            # Then fix any stray CRs (Mac style or artifacts)
            fixed_content = fixed_content.replace(b'\r', b'\n')
            
            # 3. Write back only if changes occurred
            if content != fixed_content:
                with open(file_path, 'wb') as f:
                    f.write(fixed_content)
                print(f"✅ CLEANED: {file_path}")
                cleaned_count += 1
            else:
                print(f"✨ SKIPPED: {file_path} (Already Clean)")
                
        except Exception as e:
            print(f"❌ ERROR: {file_path} - {e}")
    else:
        print(f"⚠️ MISSING: {file_path}")

print("-" * 30)
if cleaned_count > 0:
    print(f"🎉 SUCCESS! {cleaned_count} files scrubbed.")
else:
    print("🤷 No files needed fixing.")
