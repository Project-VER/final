import requests

url = 'http://192.168.193.33:8000/chat'
files = {'image': open('Screenshot 2024-07-15 at 2.42.25 pm.png', 'rb')}
data = {'text': 'What is the image?'}

response = requests.post(url, files=files, data=data)
print(response.json())
