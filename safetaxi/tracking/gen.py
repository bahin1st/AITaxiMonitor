import json
import csv

def convert_json_to_csv(json_files, csv_file, plate_number):
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:  # Changed to 'a' for append mode
        writer = csv.writer(file)
        
        # Write the header only if the CSV file is empty
        if file.tell() == 0:
            writer.writerow(["plate_number", "current_lat", "current_lon"])
        
        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract the coordinates from the 'geometry' part of the JSON file
            coordinates = data.get("geometry", {}).get("coordinates", [])
                
            for loc in coordinates:
                lat, lon = loc
                writer.writerow([plate_number, lon, lat])

if __name__ == "__main__":
    json_input_files = ["files/route (2).json", "files/route (4).json", "files/route (5).json"]  # Add files as needed
    csv_output = "taxis_paths.csv"  # Output CSV file

    # Specify the plate number for each file
    plate_numbers = ["234KAZ", "232KAZ", "231KAZ"]  # Plate numbers corresponding to each file

    # Iterate over files and plate numbers and process them
    for i, json_file in enumerate(json_input_files):
        convert_json_to_csv([json_file], csv_output, plate_numbers[i])

    print(f"Data has been successfully written to {csv_output}")
