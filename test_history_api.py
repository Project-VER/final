import requests

url = 'http://192.168.193.33:8000/chat'
files = {'image': open('/Users/abigailhiggins/Desktop/Screenshot 2024-09-30 at 8.25.51 pm.png', 'rb')}
data = {'text': 'What color is the sunset? (max 20 words)'}

response = requests.post(url, files=files, data=data)
print(response.json())
