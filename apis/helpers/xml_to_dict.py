from xml.etree import ElementTree as ET


def xml_to_dict(xml_string):
    # Parse XML string to Element
    root = ET.fromstring(xml_string)

    # Define a recursive function to convert XML to dict
    def parse_element(element):
        # Special case for geraScriptReturn with specific attributes
        tag = element.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]

        # Check if this is the geraScriptReturn element with the specific attributes
        if (
            tag == "geraScriptReturn"
            and "{http://www.w3.org/2001/XMLSchema-instance}type" in element.attrib
            and element.attrib["{http://www.w3.org/2001/XMLSchema-instance}type"]
            == "soapenc:string"
        ):
            # Return just the text content
            return element.text.strip() if element.text else ""

        result = {}

        # Check if element has xsi:nil="true"
        nil_attr = "{http://www.w3.org/2001/XMLSchema-instance}nil"
        if nil_attr in element.attrib and element.attrib[nil_attr] == "true":
            return None

        # Add element's attributes (except nil attribute)
        for key, value in element.attrib.items():
            if key != nil_attr:  # Skip the nil attribute
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
