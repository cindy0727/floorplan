import random

# 讀取文本文件
with open('floorplan.txt', 'r') as file:
    content = file.read()

# 定義有幾趴的機率將N轉換成P
F_probability = 0.01
N_probability = 0.3    
M_probability = 0.45
H_probability = 0.6

# 將文本中的 "N" 替換成 "p"，以一定的機率
new_content = ""
for char in content:
    if (char == 'W' or char == 'N' or char == 'M' or char == 'H') and random.random() < F_probability:
        new_content += 'F'
    elif char == 'N' and random.random() < N_probability:
        new_content += 'P'
    elif char == 'H':
        if random.random() < H_probability:
            new_content += 'P'
        else:
            new_content += 'N'
    elif char == 'M':
        if random.random() < M_probability:
            new_content += 'P'
        else:
            new_content += 'N'
    else:
        new_content += char

# 寫回文本文件
with open('floorplan1.txt', 'w') as file:
    file.write(new_content)