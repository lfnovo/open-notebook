import os
import glob
import re

locales_dir = "frontend/src/lib/locales"
locales = glob.glob(f"{locales_dir}/*/index.ts")

for locale_file in locales:
    with open(locale_file, 'r') as f:
        content = f.read()
        
    if 'visionModelLabel' in content:
        continue
        
    label = "Vision Model"
    desc = "Used to analyze images and extract text from PDFs"
    
    if "it-IT" in locale_file:
        label = "Modello Visione"
        desc = "Usato per l'analisi di immagini e l'estrazione di testo da PDF"
        
    # We will use regex to find the sttModelLabel line and insert before it
    pattern = r"(\s+sttModelLabel:.*?\n)"
    replacement = f'    visionModelLabel: "{label}",\n    visionModelDesc: "{desc}",\n\\1'
    
    new_content = re.sub(pattern, replacement, content)
    
    with open(locale_file, 'w') as f:
        f.write(new_content)

print("Updated all locales successfully")
