#!/usr/bin/env python3
"""
Tự động fix dependencies cho Streamlit Cloud
"""
import subprocess
import sys

FIXED_DEPS = {
    'streamlit-autorefresh': '0.0.1',
    'pandas': '2.2.2',
    'numpy': '1.26.4',
    'streamlit': '1.28.1'
}

def update_requirements():
    with open('requirements.txt', 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            new_lines.append(line)
            continue
            
        # Tách tên package và version
        if '==' in line:
            pkg = line.split('==')[0].strip()
        elif '>=' in line:
            pkg = line.split('>=')[0].strip()
        elif '<=' in line:
            pkg = line.split('<=')[0].strip()
        else:
            pkg = line.strip()
        
        # Fix nếu là package có vấn đề
        if pkg in FIXED_DEPS:
            new_lines.append(f"{pkg}=={FIXED_DEPS[pkg]}")
            print(f"✅ Fixed: {pkg} -> {FIXED_DEPS[pkg]}")
        else:
            new_lines.append(line)
    
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(new_lines))
    print("✅ Updated requirements.txt")

if __name__ == '__main__':
    update_requirements()
