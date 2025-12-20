# import requests
# headers = {
#     'Authorization': f'Bearer sk-1875555551ae4b7fb455ce863ccc210d',
#     'Content-Type': 'application/json'
# }

# data = {
# "model": f"deepseek-r1:14b", #"gpt-oss:20b" , qwen3-coder:30b
# "messages": [
#     {
#     "role": "user",
#     "content": f"What is capital of India"
#     }
# ]}
# response = requests.post('https://ai.chelsoft.com/api/chat/completions', headers=headers, json=data)
# print(response.text)

import pandas as pd

df = pd.DataFrame({
    'A': [[{'X': 1, 'Y': 2, 'Z': 3}, {'X': 1, 'Y': 2, 'Z': 3}, {'X': 1, 'Y': 2, 'Z': 3}], [{'X': 1, 'Y': 2, 'Z': 3}, {'X': 1, 'Y': 2, 'Z': 3}], [{'X': 1, 'Y': 2, 'Z': 3}]],
    'B': [10, 20, 30]
})


list_cols = []
for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, list)).any():
        #print(df[col].apply(lambda x: isinstance(x, list)).any())
        sub_list = pd.DataFrame(df[col].explode().to_list())
        print(sub_list)
print(list_cols)