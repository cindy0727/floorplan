import subprocess

# 存结果的陣列
results = []
run_times = 5


for i in range(run_times):
    # 執行命令並記錄輸出結果
    output = subprocess.run(['python', 'evacuate.py', '-i', 'twb.txt', '-w', str(i/run_times)], capture_output=True, text=True)

    # 將輸出结果加到陣列中
    results.append(output.stdout)

#印出結果
print("所有结果:", results)





