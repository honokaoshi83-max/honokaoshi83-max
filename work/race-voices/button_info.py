import json
from status_button import WinMMButton
found=[]
for device in range(1,17):
    row=WinMMButton(device).describe()
    if row['connected']:found.append({'控制器编号':device,'设备':row['device_name'],'按钮数量':row['button_count']})
print(json.dumps(found if found else {'提示':'未检测到已连接的游戏控制器。'},ensure_ascii=False,indent=2))
