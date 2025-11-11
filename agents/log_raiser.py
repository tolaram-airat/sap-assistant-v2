import json
import os
from datetime import datetime
import requests

# File pathways
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs.json")
COMPANIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "company.json")

# API endpoint
API_ENDPOINT = "https://revion-aws-eu-uk-ldb2.revion.com/ords/a172083_test/helpdeskapi%20/issues"
API_HEADERS = {"Content-Type": "application/json"}

def load_companies():
    """Load company.json and return company data."""
    try:
        with open(COMPANIES_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {COMPANIES_PATH} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: {COMPANIES_PATH} is corrupted")
        return []

def map_company_code(input_code):
    """Map input company/plant code to a valid companyID."""
    companies = load_companies()
    for company in companies:
        if str(company.get("companyID")) == str(input_code):
            return company.get("companyID")
    return 490518  # Default to ZA10-ZA10-KTSA from your sample

def map_profit_center(input_code):
    """Map input profit center to a valid ProfitCenterID."""
    companies = load_companies()
    for company in companies:
        if str(company.get("ProfitCenterID")) == str(input_code):
            return company.get("ProfitCenterID")
    return 3410  # Default to 3410-CAPETOWN from your sample

def extract_logged_by(mail_id):
    """Extract logged_by from mail_id (e.g., 'airat.test@tolaram.com' -> 'airat')."""
    if not mail_id:
        return "unknown"
    local_part = mail_id.split('@')[0]
    return local_part.split('.')[0]

def raise_log(params):
    """Generate a structured log entry and send to helpdesk API."""
    user_input = params.get("user_input")
    matches = params.get("matches", [])
    company_code = params.get("company_code")
    profit_center = params.get("profit_center")
    extracted_phrase = params.get("extracted_phrase")
    contact_no = params.get("contact_no")
    mail_id = params.get("mail_id")
    cc_to = params.get("cc_to")

    if not user_input:
        return {
            "status": "error",
            "message": "user_input is required",
            "response": {}
        }
    if not matches or not isinstance(matches, list):
        matches = [{
            "id": None,
            "module": "Unknown",
            "issuename": "No matching error found",
            "issuedescription": user_input,
            "solution": "Sorry no match found, I'm still learning",
            "solutiontype": None,
            "logcategory": None,
            "logsubcategory": None,
            "notes": None,
            "score": 0
        }]

    # Prepare local log entry
    local_log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_input": user_input,
        "company_code": company_code,
        "profit_center": profit_center,
        "extracted_phrase": extracted_phrase,
        "contact_no": contact_no,
        "mail_id": mail_id,
        "cc_to": cc_to,
        "matches": [
            {
                "id": match["id"],
                "module": match["module"],
                "issuename": match["issuename"],
                "issuedescription": match["issuedescription"],
                "solution": match["solution"],
                "solutiontype": match.get("solutiontype"),
                "notes": match["notes"],
                "score": match["score"],
                "logcategory": match["logcategory"],
                "logsubcategory": match["logsubcategory"]
            }
            for match in matches
        ]
    }

    # Save to logs.json
    logs = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, 'r') as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            print("Warning: logs.json is corrupted, starting fresh.")
            logs = []
    
    logs.append(local_log_entry)
    
    try:
        with open(LOG_PATH, 'w') as f:
            json.dump(logs, f, indent=4)
        print(f"Log entry saved to {LOG_PATH} for input: {user_input}")
    except Exception as e:
        print(f"Error saving to {LOG_PATH}: {e}")

    # Prepare API payload
    top_match = matches[0] if matches and matches[0]["score"] > 0 else None
    entity_code = extracted_phrase.split()[1] if extracted_phrase and len(extracted_phrase.split()) > 1 else user_input.split()[0] if user_input.split() else "unknown"
    location_code = company_code or (extracted_phrase.split()[-1].rstrip(',') if extracted_phrase and len(extracted_phrase.split()) > 3 else "unknown")
    
    company_id = int(map_company_code(company_code)) if company_code else 490518
    profit_center_id = int(map_profit_center(profit_center)) if profit_center else 3410
    product_name = int(top_match["logcategory"]) if top_match and top_match.get("logcategory") else 3421
    sub_category = int(top_match["logsubcategory"]) if top_match and top_match.get("logsubcategory") else 3425
    
    api_payload = {
        "type": "Normal",
        "company": company_id,
        "location": 234,
        "profit_center": profit_center_id,
        "product_name": product_name,
        "sub_category": sub_category,
        "contact_no": contact_no or "08143556110",
        "logged_by": extract_logged_by(mail_id) if mail_id else "unknown",
        "mail_id": mail_id or "unknown@tolaram.com",
        "cc_to": cc_to or "",
        "impact": "Month End",
        "subject": (top_match["issuename"].replace("XXXX", entity_code).replace("YYYY", location_code) if top_match 
                    else extracted_phrase or user_input),
        "description": f"User encountered an error in SAP system: {user_input}. {top_match['issuedescription'] if top_match else 'No matching error found.'}"
    }

    # Send HTTP POST request
    api_response = {"status_code": None, "response_text": "", "response_json": None, "issue_number": None, "zhi_id": None}
    try:
        response = requests.post(API_ENDPOINT, json=api_payload, headers=API_HEADERS)
        api_response = {
            "status_code": response.status_code,
            "response_text": response.text[:500],
            "response_json": response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
        if response.status_code in (200, 201):
            print(f"Log entry sent to API: {response.status_code}")
            if api_response["response_json"] and "response" in api_response["response_json"]:
                try:
                    nested_response = json.loads(api_response["response_json"]["response"])
                    api_response["issue_number"] = nested_response.get("issue_number")
                    api_response["zhi_id"] = nested_response.get("zhi_id")
                    print(f"Ticket created: Issue Number = {api_response['issue_number']}, zhi_id = {api_response['zhi_id']}")
                except json.JSONDecodeError:
                    print("Warning: Failed to parse nested JSON response")
        else:
            print(f"Failed to send log to API: {response.status_code} - {response.text[:500]}")
    except requests.RequestException as e:
        print(f"Error sending POST request: {e}")
        api_response = {"status_code": None, "response_text": str(e), "response_json": None, "issue_number": None, "zhi_id": None}

    print(f"API response: {api_response}")
    return {
        "status": "success" if api_response["status_code"] in (200, 201) else "error",
        "message": f"Log raised with status {api_response['status_code']}: {api_response['response_text']}",
        "response": api_response
    }

if __name__ == "__main__":
    # Test function (optional)
    test_params = {
        "user_input": "Routing not found for material 0001000738",
        "matches": [
            {
                "id": 1,
                "module": "PP (Production Planning)", 
                "issuename": "Routing not found for material 0001000738",
                "issuedescription": "Routing master data missing for production",
                "solution": "1. Check routing in CA03.2. Request creation if missing.3. Raise a log and assign to master data consultant.",
                "solutiontype": "User Guidance + Mandatory Escalation",
                "logcategory": 3421,
                "logsubcategory": 3429,
                "notes": "",
                "score": 95
            }
        ],
        "company_code": "283271",
        "profit_center": "7001",
        "extracted_phrase": "Routing not found for material 0001000738",
        "contact_no": "0802375037",
        "mail_id": "test.role@tolaram.com",
        "cc_to": "sab.das@kelloggs.com"
    }
    result = raise_log(test_params)
    print(result)