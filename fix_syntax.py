#!/usr/bin/env python3
"""Fix the syntax error in simple_gui.py"""

import os

project_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(project_dir, "src", "agents", "simple_gui.py")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and fix the syntax error
old = '''            for report in reports[-20:]:
                self.report_text.insert(tk.END, report + "
259|
260|")'''

new = '''            for report in reports[-20:]:
                self.report_text.insert(tk.END, report + "\\n\\n")'''

if old in content:
    content = content.replace(old, new)
    print("Fixed the syntax error")
else:
    print("Pattern not found, searching for alternative...")
    # Try to find the exact line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'report_text.insert(tk.END, report +' in line:
            print(f"Line {i}: {repr(line)}")
            # Fix this line
            lines[i] = '                self.report_text.insert(tk.END, report + "\\n\\n")'
            content = '\n'.join(lines)
            print("Fixed!")
            break

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File saved")
