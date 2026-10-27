import re

with open(r"D:\Downloads\Raj\Zebra_final_try\Zebra_final_try.xpr", "r") as f:
    text = f.read()

files = re.findall(r'<File Path="([^"]+)">', text)
print("Files in XPR:")
for fl in files:
    print(" ", fl)
