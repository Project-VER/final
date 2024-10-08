from integrated_back import app  


device_mode_action = "No Action Required"


with app.test_client() as client:
    response = client.get('/get-settings')
    data = response.get_json() 

    
    print(data)



mode = data.get('Device Mode', {}).get('value') 
length = data.get('Response Length', {}).get('value') 

prompt = f"{mode}(max {length} words)"
# Output the result
print(prompt)

