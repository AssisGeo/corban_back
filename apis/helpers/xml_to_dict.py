from xml.etree import ElementTree as ET


def xml_to_dict(xml_string):
    # Parse XML string to Element
    root = ET.fromstring(xml_string)

    # Define a recursive function to convert XML to dict
    def parse_element(element):
        result = {}

        # Add element's attributes
        for key, value in element.attrib.items():
            result[key] = value

        # Process child elements
        for child in element:
            child_data = parse_element(child)

            # Handle the tag name
            tag = child.tag
            # Remove namespace prefix if present
            if "}" in tag:
                tag = tag.split("}", 1)[1]

            # If we already have this tag, convert to list
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data

        # If element has text and no children, just return the text
        if not result and element.text and element.text.strip():
            return element.text.strip()

        # If there's text but also children/attributes, add text as a special key
        elif element.text and element.text.strip():
            result["_text"] = element.text.strip()

        return result

    return parse_element(root)
