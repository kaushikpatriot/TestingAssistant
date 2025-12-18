import requests
headers = {
    'Authorization': f'Bearer sk-1875555551ae4b7fb455ce863ccc210d',
    'Content-Type': 'application/json'
}

data = {
"model": f"deepseek-r1:14b", #"gpt-oss:20b" , qwen3-coder:30b
"messages": [
    {
    "role": "user",
    "content": f"What is capital of India"
    }
]}
response = requests.post('https://ai.chelsoft.com/api/chat/completions', headers=headers, json=data)
print(response.text)
