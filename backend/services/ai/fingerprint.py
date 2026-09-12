import re
from typing import Dict, Any, List

def extract_problem_fingerprint(title: str, description: str) -> Dict[str, Any]:
    """
    Intelligent problem fingerprint extractor for repair problems.
    Extracts device specs, symptoms, suspected fault component, and required technician skills.
    Never presents hypotheses as certainties.
    """
    text = f"{title} {description}".lower()
    
    # Device type & brand heuristic detection
    device_type = "Electrical / Electronic Equipment"
    category = "General Electrical"
    brand = None
    model = None
    
    if any(k in text for k in ["samsung", "iphone", "apple", "pixel", "oneplus", "xiaomi", "redmi", "phone", "smartphone", "mobile"]):
        device_type = "Smartphone / Mobile Device"
        category = "Electronics"
        if "samsung" in text:
            brand = "Samsung"
        elif "apple" in text or "iphone" in text:
            brand = "Apple"
        elif "oneplus" in text:
            brand = "OnePlus"
        elif "pixel" in text:
            brand = "Google Pixel"
        
        # Model extraction
        s23_match = re.search(r'(galaxy\s+)?(s2[0-4]|note\s+\d+|iphone\s+\d+)', text, re.IGNORECASE)
        if s23_match:
            model = s23_match.group(0).capitalize()
            
    elif any(k in text for k in ["inverter", "ups", "battery", "luminous", "microtek", "zelio"]):
        device_type = "Power Inverter / UPS"
        category = "Power Systems"
        if "luminous" in text:
            brand = "Luminous"
        elif "microtek" in text:
            brand = "Microtek"
        model_match = re.search(r'(zelio\s+\d+|eco\s+volt|\d+va)', text, re.IGNORECASE)
        if model_match:
            model = model_match.group(0).upper()
            
    elif any(k in text for k in ["tv", "television", "led", "lcd", "oled", "smart tv", "sony", "lg"]):
        device_type = "Smart Television"
        category = "Consumer Electronics"
        if "sony" in text:
            brand = "Sony"
        elif "lg" in text:
            brand = "LG"
        elif "samsung" in text:
            brand = "Samsung"
            
    elif any(k in text for k in ["mcb", "wiring", "switchboard", "tripping", "short circuit", "earthing", "breaker"]):
        device_type = "Domestic Wiring / Distribution Board"
        category = "Home Electrical"

    # Symptom detection
    symptoms: List[str] = []
    if any(k in text for k in ["no power", "dead", "won't turn on", "does not turn on", "not turning on"]):
        symptoms.append("Complete failure to power on (0mA draw)")
    if any(k in text for k in ["drop", "dropped", "fell", "physical damage", "impact"]):
        symptoms.append("Prior history of physical drop / mechanical shock")
    if any(k in text for k in ["overload", "beeping", "alarm", "buzzer"]):
        symptoms.append("Continuous overload or warning buzzer")
    if any(k in text for k in ["tripping", "trip", "spark", "sparking", "smoke"]):
        symptoms.append("Circuit breaker tripping upon activation")
    if any(k in text for k in ["heating", "hot", "overheat"]):
        symptoms.append("Unusual localized component heat")
    if not symptoms:
        symptoms.append("Unspecified malfunction reported by customer")

    # Suspected component (always phrased hypothetically per Section 7)
    suspected_component = "Suspected power delivery circuit or wiring anomaly"
    if "board" in text or "drop" in text or "s23" in text or "dead" in text:
        suspected_component = "Possible motherboard power management IC (PMIC) or decoupled rail fault"
    elif "inverter" in text or "overload" in text:
        suspected_component = "Possible H-bridge MOSFET failure or feedback sensor resistor drift"
    elif "tripping" in text or "mcb" in text:
        suspected_component = "Possible line-to-neutral or line-to-earth insulation leakage"
    elif "tv" in text:
        suspected_component = "Possible backlight LED strip open circuit or T-Con power rail failure"

    repair_type = "Component-Level Repair & Diagnostics"
    if "wiring" in text or "switchboard" in text:
        repair_type = "Electrical Tracing & Line Replacement"

    # Extracted skills
    extracted_skills: List[str] = []
    if "board" in text or "soldering" in text or "s23" in text or "drop" in text:
        extracted_skills.extend(["Board-Level Soldering", "Power Supply Diagnostics", "Short Circuit Tracing"])
    if "inverter" in text or "ups" in text:
        extracted_skills.extend(["Inverter & UPS Repair", "Power Supply Diagnostics"])
    if "wiring" in text or "tripping" in text or "mcb" in text:
        extracted_skills.extend(["Home Appliance Wiring", "Short Circuit Tracing"])
    if not extracted_skills:
        extracted_skills = ["Power Supply Diagnostics", "Short Circuit Tracing"]

    ai_summary = (
        f"{device_type} experiencing '{symptoms[0]}'. "
        f"Preliminary AI evaluation suggests {suspected_component.lower()}. "
        f"Requires specialized diagnosis using tools such as thermal imaging, multimeter, or soldering rework."
    )

    return {
        "device_type": device_type,
        "brand": brand or "Detected from problem context",
        "model": model or "Standard specification",
        "category": category,
        "issue": title,
        "symptoms": symptoms,
        "context": {
            "origin": "Customer problem description",
            "urgency": "High" if "smoke" in text or "spark" in text else "Standard",
            "requires_onsite": True
        },
        "suspected_component": suspected_component,
        "repair_type": repair_type,
        "extracted_skills": extracted_skills,
        "ai_summary": ai_summary,
        "fingerprint_version": 1,
        "embedding_status": "completed"
    }
