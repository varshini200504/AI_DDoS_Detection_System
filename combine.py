import pandas as pd
import glob
import os

# ==========================
# CONFIG
# ==========================
ATTACK_FOLDER = r"data-attack"
NORMAL_FOLDER = r"data-normal"
OUTPUT_FILE = "final_multiclass_dataset_large.csv"

# Larger dataset settings
CHUNK_SIZE = 100000
ROWS_PER_CHUNK = 30000

# ==========================
# ENHANCED LIGHTWEIGHT FEATURE SET
# ==========================
TARGET_FEATURES = [
    "Flow Duration",
    "Flow Packets/s",
    "Flow Bytes/s",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Packet Length Mean",
    "Packet Length Std",
    "Average Packet Size",
    "SYN Flag Count",
    "ACK Flag Count",
    "RST Flag Count",
    "PSH Flag Count",
    "Down/Up Ratio",
    "Destination Port",
    "Protocol"
]

# ==========================
# ATTACK LABEL MAP
# ==========================
attack_label_map = {
    "DrDoS_DNS": 1,
    "DrDoS_NTP": 2,
    "DrDoS_SNMP": 3,
    "DrDoS_SSDP": 4,
    "LDAP": 5,
    "MSSQL": 6,
    "NetBIOS": 7,
    "Portmap": 8,
    "Syn": 9,
    "TFTP": 10,
    "UDP": 11,
    "UDPLag": 12
}

NORMAL_LABEL = 0


# ==========================
# PROCESS FILE
# ==========================
def process_file(file_path, label_value):
    print(f"\nProcessing: {os.path.basename(file_path)} -> Label {label_value}")

    collected_chunks = []

    try:
        chunks = pd.read_csv(
            file_path,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8"
        )

        chunk_count = 0

        for chunk in chunks:
            chunk_count += 1

            # Clean column names
            chunk.columns = chunk.columns.str.strip()

            # Check required columns
            missing = [col for col in TARGET_FEATURES if col not in chunk.columns]

            if missing:
                print(f"Skipping chunk {chunk_count}, missing columns: {missing}")
                continue

            # Select needed columns
            chunk = chunk[TARGET_FEATURES]

            # Replace bad values
            chunk.replace([float("inf"), -float("inf")], 0, inplace=True)
            chunk.fillna(0, inplace=True)

            # Add label
            chunk["Label"] = label_value

            # Sample more rows
            if len(chunk) > 0:
                sample_size = min(ROWS_PER_CHUNK, len(chunk))
                chunk = chunk.sample(n=sample_size, random_state=42)

                collected_chunks.append(chunk)

            print(f"Chunk {chunk_count} processed, rows collected: {sample_size}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    if collected_chunks:
        combined = pd.concat(collected_chunks, ignore_index=True)
        print(f"Total rows from {os.path.basename(file_path)}: {len(combined)}")
        return combined

    else:
        return pd.DataFrame(columns=TARGET_FEATURES + ["Label"])


# ==========================
# MAIN COLLECTION
# ==========================
all_data = []

# ATTACK FILES
attack_files = glob.glob(os.path.join(ATTACK_FOLDER, "*.csv"))

for file_path in attack_files:
    filename = os.path.basename(file_path).replace(".csv", "")

    if filename in attack_label_map:
        label = attack_label_map[filename]

        df = process_file(file_path, label)

        if not df.empty:
            all_data.append(df)

    else:
        print(f"Unknown attack type skipped: {filename}")


# NORMAL FILES
normal_files = glob.glob(os.path.join(NORMAL_FOLDER, "*.csv"))

for file_path in normal_files:
    df = process_file(file_path, NORMAL_LABEL)

    if not df.empty:
        all_data.append(df)


# ==========================
# COMBINE
# ==========================
print("\nCombining all datasets...")

final_df = pd.concat(all_data, ignore_index=True)

# ==========================
# BALANCE CLASSES
# ==========================
print("Balancing classes...")

class_counts = final_df["Label"].value_counts()
min_class_size = class_counts.min()

balanced_data = []

for label in sorted(final_df["Label"].unique()):
    class_df = final_df[final_df["Label"] == label]

    balanced_sample = class_df.sample(
        n=min_class_size,
        random_state=42
    )

    balanced_data.append(balanced_sample)

final_df = pd.concat(balanced_data, ignore_index=True)

# Shuffle
final_df = final_df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)

# ==========================
# SAVE
# ==========================
final_df.to_csv(OUTPUT_FILE, index=False)

# ==========================
# REPORT
# ==========================
print("\n==== LARGE MULTICLASS DATASET CREATED SUCCESSFULLY ====")
print("Saved as:", OUTPUT_FILE)
print("Final shape:", final_df.shape)

print("\nLabel distribution:")
print(final_df["Label"].value_counts().sort_index())

print("\nLabel mapping:")
print("0 = Normal")
for attack_name, attack_id in attack_label_map.items():
    print(f"{attack_id} = {attack_name}")

print("\nColumns:")
print(final_df.columns.tolist())

print("\nPreview:")
print(final_df.head())