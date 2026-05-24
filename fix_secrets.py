import json

json_path = r"C:\Northpharm\DeliveryTracker\tidy-outlet-460214-q3-e39b62db9844.json"
output_path = r"C:\Northpharm\DeliveryTracker\.streamlit\secrets.toml"

with open(json_path, "r", encoding="utf-8") as f:
    key = json.load(f)

with open(output_path, "w", encoding="utf-8") as f:
    f.write("[gcp_service_account]\n")
    for k, v in key.items():
        v_escaped = str(v).replace("\n", "\\n").replace('"', '\\"')
        f.write(f'{k} = "{v_escaped}"\n')

print("secrets.toml 已生成！")