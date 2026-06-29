import re
import json

def correct_json_format(json_str):
    corrected_str = "[\n"

    while True:

        index = json_str.find("\"node_1\"")  # Find item index

        if (index < 0):  # No more items (need to close brackets)
            # print("End of items")
            corrected_str = corrected_str[:-2]  # Remove trailing comma and newline (no new item)
            break

        corrected_str += "  {\n"  # Open brace

        json_str = json_str[index:]  # Trim front

        index = json_str.find("\"node_2\"")  # Up to the part to write
        node_1_sentence = json_str[:index]  # Slice and process

        index = node_1_sentence.rfind("\"")  # Trim if there are unnecessary parts

        corrected_str += "    " + node_1_sentence[:index + 1] + ",\n"  # Insert sentence

        index = json_str.find("\"node_2\"")  # Find item index

        json_str = json_str[index:]  # Trim front

        index = json_str.find("\"edge\"")  # Up to the part to write
        node_2_sentence = json_str[:index]  # Slice and process

        index = node_2_sentence.rfind("\"")  # Trim if there are unnecessary parts

        corrected_str += "    " + node_2_sentence[:index + 1] + ",\n"  # Insert sentence

        index = json_str.find("\"edge\"")  # Find item index
        json_str = json_str[index:]

        index = json_str.find("\"node_1\"")  # Find next item
        if (index < 0):
            edge_sentence = json_str  # If it's the last item
        else:
            edge_sentence = json_str[:index]  # Process

        index = edge_sentence.rfind("\"")  # Trim if there are unnecessary parts

        corrected_str += "    " + edge_sentence[:index + 1] + "\n"  # Insert sentence
        corrected_str += "  },\n"  # Close brace

    corrected_str += '\n' + ']'
    return corrected_str

def make_response_content_json(response_content, metadata):
    first_bracket_index = response_content.rfind('[')
    response_content = response_content[first_bracket_index:].strip()
    response_content = correct_json_format(response_content)

    # try-except in case response is still not in json format
    try:
        result = json.loads(response_content)
        result = [dict(item, **metadata) for item in result]  # Add metadata to each relationship
        return result
    except json.JSONDecodeError:
        # If it fails, try to parse each JSON object individually
        json_segments = re.split(r'}\s*,\s*\{', response_content.strip()[1:-1])
        valid_jsons = []
        invalid_jsons = []

        for i, segment in enumerate(json_segments):
            # Properly enclose each segment in curly braces
            if i != 0:  # If it's not the first segment, add an opening brace
                segment = '{' + segment
            if i != len(json_segments) - 1:  # If it's not the last segment, add a closing brace
                segment = segment + '}'

            try:
                # Attempt to parse the segment
                json_obj = json.loads(segment)
                # Here you can add your metadata as you did before
                json_obj = dict(json_obj, **metadata)
                valid_jsons.append(json_obj)

            except json.JSONDecodeError as e:
                # Log invalid segment
                invalid_jsons.append((segment, str(e)))

        # If there are valid JSONs, use them
        if valid_jsons:
            result = valid_jsons
        else:
            # If no valid JSONs, handle the error accordingly
            result = []
        return result