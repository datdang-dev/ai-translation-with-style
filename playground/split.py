import json

def split_to_json(input_file, num_files=200):
    # đọc nội dung
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    data = {}
    current_id = None

    for line in lines:
        line = line.strip()
        if line.startswith("---------"):
            current_id = line.replace("-", "").strip()
        elif line and current_id:
            data[current_id] = line
            current_id = None

    # chia thành num_files phần
    items = list(data.items())
    chunk_size = len(items) // num_files + (len(items) % num_files > 0)

    for i in range(num_files):
        chunk = items[i*chunk_size:(i+1)*chunk_size]
        if not chunk:
            continue
        chunk_dict = {k: v for k, v in chunk}
        with open(f"chunk_{i+1}.json", "w", encoding="utf-8") as f:
            json.dump(chunk_dict, f, ensure_ascii=False, indent=2)

    print(f"Done! Created {num_files} JSON files.")

# chạy thử
split_to_json("input.txt", 200)
