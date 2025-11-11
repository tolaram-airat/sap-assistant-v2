import streamlit as st
import os
import re
from dotenv import load_dotenv
from anthropic import Anthropic, AnthropicError
import json
from datetime import datetime
from agents.retrieval_new import retrieve_errors, extract_error_phrase  # CHANGED: Import from retrieval_new.py
from agents.log_raiser import raise_log

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    st.error("Anthropic API key not found. Please add it in **Streamlit Cloud → Settings → Secrets**.")
    st.stop()

# Initialize Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

try:
    import setup_db          # creates data/errors.db if it does not exist
except Exception as e:
    st.error(f"Failed to initialize database: {e}")
    st.stop()

# Load company data from company.json
def load_company_data():
    company_path = os.path.join(os.path.dirname(__file__), "data", "company.json")
    try:
        with open(company_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading company.json: {str(e)}. Using default data.")
        return [
            {"companyID": 490518, "ProfitCenterID": 3410, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3410-CAPETOWN"},
            {"companyID": 490518, "ProfitCenterID": 3400, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3400-JO BURG"}
        ]

company_data = load_company_data()

# Tool definitions
tools = [
    {
        "name": "retrieve_errors",
        "description": "Retrieve matching SAP errors from the database based on user input. Only use for explicit error messages or issues likely to be in the database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_input": {"type": "string", "description": "The user's error description"},
                "company_code": {"type": ["string", "null"], "description": "The company code (e.g., 490518)"},
                "profit_center": {"type": ["string", "null"], "description": "The profit center (e.g., 3410)"}
            },
            "required": ["user_input"]
        }
    }
]

# Updated system prompt (minor tweak to emphasize knowledge-based suggestions for low-score matches)
SYSTEM_PROMPT = """
You are an SAP Error Handling Assistant, designed to assist users with SAP-related issues efficiently. You have comprehensive knowledge of SAP systems, including tables, processes, and common issues, and can act as an SAP consultant.

**Role**: Act as a friendly, professional SAP support agent, guiding users through error resolution, escalation processes, and answering S4HANA SAP questions using your expertise.

**Objective**: Help users resolve SAP errors by retrieving relevant solutions from a database and escalating unresolved issues by raising logs with accurate ticket details. For SAP-related questions or issues with no database matches, provide informed, conversational responses based on your SAP consultant expertise.

**Context**: You operate within a Streamlit application integrated with the Anthropic API (claude-3-haiku-20240307) and a SQLite database (errors.db) containing SAP error data (e.g., issuename, issuedescription, solutiontype, stepbystep). The system uses company data from company.json (e.g., {"companyID": 490518, "ProfitCenterID": 3410, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3410-CAPETOWN"}) and logs escalations to logs.json via an API.

**Tools**: 
- `retrieve_errors`: Retrieves matching SAP errors from errors.db based on user input, company_code, and profit_center, returning a list of matches with scores. Use only for explicit errors (e.g., containing "error," "blocked," "not found," "missing," "failed," "does not exist").

**Tasks**: 
1. Analyze user input for SAP-related issues or questions using keywords (e.g., "error," "blocked," "not found," "missing," "failed," "does not exist") or SAP terms (e.g., "Cost center," "Material," "Plant," "PO," "Purchase Order," "OBD," "Outbound Delivery").
2. For general SAP questions or ambiguous inputs without explicit error keywords (e.g., "I am unable to receive materials on the PO using the obd sent," "How do I create a material in SAP?"), respond conversationally with suggestions based on your SAP expertise (e.g., "This could be due to an issue with the outbound delivery status. Check the delivery in VL03N or verify the PO status in ME23N."). Do NOT call `retrieve_errors` for these inputs. Examples of non-error inputs include:
   - Process questions (e.g., "How do I post a goods receipt?").
   - General issues without error codes (e.g., "Unable to receive materials on PO").
   - Requests for explanations or guidance (e.g., "What is a cost center?").
3. If the input contains explicit error keywords or matches database error patterns (e.g., "Cost center MA108 is blocked for postings"):
   a. Call `retrieve_errors` with the user input.
   b. Select the highest-scoring match from the results.
   c. If the match has a score of 0 or `solutiontype` is empty/"User Guidance," treat it as no match and respond with: "Sorry, I couldn’t find a match for that issue in my database. Based on my SAP expertise, here are some suggestions: [provide 1-2 concise suggestions, e.g., check transaction codes, authorizations, or master data]. Would you like to escalate it?"
   d. If a valid match is found, check if its `solutiontype` contains "Escalation."
      - If it does, respond with a message prompting the user to provide contact details (contact_no, mail_id, cc_to, company_code, profit_center) for escalation.
      - If `solutiontype` does not contain "Escalation," return the stepbystep solution concisely.
4. If the user explicitly requests to raise a log (e.g., "Yes, I want to raise a ticket log"), respond with a message prompting the user to provide contact details for escalation, using the previous error’s matches if available.
5. For non-SAP-related inputs (e.g., greetings), respond conversationally without tools.
6. If the input is ambiguous, ask a clarifying question (e.g., "Could you specify if you're seeing an error message or describe the issue further?") before deciding on a tool call or knowledge response.

**Operational Guidelines**: 
- Respond briefly, friendly, and professionally (e.g., "Oh, sorry about that!" or "Let’s get that sorted for you.").
- Always prefer knowledge-based responses for general SAP questions unless explicit error keywords are detected.
- Use tool calls as JSON objects with `name` and `input` fields (e.g., {"name": "retrieve_errors", "input": {"user_input": "Cost center MA108 is blocked for postings"}}).
- When escalation is needed or requested, respond with a prompt like: "Okay, let's raise a log for this. Please provide your contact number, email, CC email, company, and profit center."
- If `retrieve_errors` returns no matches or a match with a score of 0, always provide 1-2 concise suggestions based on your SAP expertise before offering escalation.
- Ask clarifying questions for ambiguous inputs to avoid incorrect tool calls.
- Log all API responses and tool results to the console for debugging.
- Go through the steps again from beginning when you sense a new input.
"""

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_details" not in st.session_state:
    st.session_state.pending_details = None
if "last_matches" not in st.session_state:
    st.session_state.last_matches = None
if "last_user_error" not in st.session_state:
    st.session_state.last_user_error = None

st.title("SAP Assistant")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input and form handling
if prompt := st.chat_input("Type your SAP error or message"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Check for user-requested escalation (broad intent detection)
    if re.search(r'\b(yes|yeah|ok|sure|please|raise|escalate|log|ticket)\b.*\b(raise|escalate|log|ticket|yes|yeah)\b', prompt.lower()):
        print("Debug: Escalation intent detected. Triggering form using stored matches or default.")
        with st.chat_message("assistant"):
            user_input_for_escalation = st.session_state.last_user_error if st.session_state.last_user_error else prompt
            extracted_phrase = extract_error_phrase(user_input_for_escalation)
            if st.session_state.last_matches:
                matches = st.session_state.last_matches
            else:
                # Default match if no previous matches
                matches = [{
                    "id": None,
                    "module": "Unknown",
                    "issuename": "No matching error found",
                    "issuedescription": user_input_for_escalation,
                    "solution": "Sorry no match found, I'm still learning",
                    "solutiontype": "consult",
                    "logcategory": None,
                    "logsubcategory": None,
                    "notes": None,
                    "score": 0
                }]
            st.session_state.pending_details = {
                "user_input": user_input_for_escalation,
                "matches": matches,
                "extracted_phrase": extracted_phrase
            }
            st.markdown("Okay, let's get started with raising a log ticket for your issue. Could you please provide me with the details I'll need to escalate this?")
            st.session_state.messages.append({"role": "assistant", "content": "Okay, let's get started with raising a log ticket for your issue. Could you please provide me with the details I'll need to escalate this?"})
    else:
        # No escalation intent detected; proceed with API call
        print("Debug: No escalation intent detected. Calling Anthropic API.")
        with st.chat_message("assistant"):
            try:
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=500,
                    temperature=0.7,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools
                )
                # Log API response for debugging
                print(f"Debug: Anthropic API response: {response}")

                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        print(f"Debug: Tool call: {tool_name} with input: {json.dumps(tool_input)}")

                        if tool_name == "retrieve_errors":
                            try:  # CHANGED: Wrapped for safety
                                result = retrieve_errors(**tool_input)
                                # Handle result as a list of matches
                                if isinstance(result, list) and result:
                                    result = sorted(result, key=lambda x: x["score"], reverse=True)
                                    st.session_state.last_matches = result
                                    st.session_state.last_user_error = tool_input["user_input"]
                                    print(f"Debug: retrieve_errors result: {json.dumps(result, indent=2)}")
                                    top_match = result[0]
                                    if top_match.get("solutiontype", "").lower() in ["", "consult"]:  # CHANGED: Adjusted for new default
                                        # CHANGED: Dynamic LLM call for flexible suggestions
                                        print("Debug: Generating dynamic suggestion via LLM.")
                                        suggestion_response = client.messages.create(
                                            model="claude-3-haiku-20240307",
                                            max_tokens=200,
                                            temperature=0.7,
                                            system="You are an SAP consultant with comprehensive knowledge of all SAP modules and processes. Provide 1-2 concise, practical suggestions to resolve or investigate the user's SAP-related issue, based on standard practices. Focus on transaction codes, checks, or steps. Do not mention databases, tools, or escalation.",
                                            messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                        )
                                        suggestion = suggestion_response.content[0].text if suggestion_response.content else "Check relevant transaction codes (e.g., ME23N for POs) or verify master data and authorizations."
                                        response_text = (
                                            f"Sorry, I couldn’t find a match for that issue in my database. " #can be updated to only show based on your knowlegde
                                            f"Based on my SAP expertise, here are some suggestions: {suggestion} "
                                            f"Would you like to escalate this issue?"
                                        )
                                        st.markdown(response_text)
                                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                                    elif "escalation" in top_match.get("solutiontype", "").lower():
                                        print("Debug: Escalation required in Solutiontype. Triggering form.")
                                        extracted_phrase = extract_error_phrase(prompt)
                                        st.session_state.pending_details = {
                                            "user_input": prompt,
                                            "matches": result,
                                            "extracted_phrase": extracted_phrase
                                        }
                                        st.markdown(f"**Here's how to try resolving it first:**\n\n{top_match['solution']}\n\n**This issue still requires escalation.** I will need to raise a log for you. Please provide your contact number, email address, CC email (if any), company, and profit center.")
                                        st.session_state.messages.append({"role": "assistant", "content": "This issue requires escalation. I will need to raise a log for you. Please provide your contact number, email address, CC email (if any), company, and profit center."})
                                    else:
                                        st.markdown(f"Looks like you're facing '{top_match['issuename']}'. Here's how to resolve it: {top_match['solution']}")
                                        st.session_state.messages.append({"role": "assistant", "content": f"Looks like you're facing '{top_match['issuename']}'. Here's how to resolve it: **\n\n{top_match['solution']}"})
                                else:
                                    # CHANGED: Dynamic LLM call for flexible suggestions
                                    print("Debug: No results - Generating dynamic suggestion via LLM.")
                                    suggestion_response = client.messages.create(
                                        model="claude-3-haiku-20240307",
                                        max_tokens=200,
                                        temperature=0.7,
                                        system="You are an SAP consultant with comprehensive knowledge of all SAP modules and processes. Provide 1-2 concise, practical suggestions to resolve or investigate the user's SAP-related issue, based on standard practices. Focus on transaction codes, checks, or steps. Do not mention databases, tools, or escalation.",
                                        messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                    )
                                    suggestion = suggestion_response.content[0].text if suggestion_response.content else "Check relevant transaction codes (e.g., ME23N for POs) or verify master data and authorizations."
                                    response_text = (
                                        f"Sorry, I couldn’t find a match for that issue in my database. "
                                        f"Based on my SAP expertise, here are some suggestions: {suggestion} "
                                        f"Would you like to escalate this issue?"
                                    )
                                    st.markdown(response_text)
                                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                                    st.session_state.last_matches = None
                                    st.session_state.last_user_error = None
                            except Exception as e:
                                print(f"Debug: Error processing retrieve_errors: {str(e)}")
                                # CHANGED: Dynamic LLM call for flexible suggestions in error case
                                suggestion_response = client.messages.create(
                                    model="claude-3-haiku-20240307",
                                    max_tokens=200,
                                    temperature=0.7,
                                    system="You are an SAP consultant with comprehensive knowledge of all SAP modules and processes. Provide 1-2 concise, practical suggestions to resolve or investigate the user's SAP-related issue, based on standard practices. Focus on transaction codes, checks, or steps. Do not mention databases, tools, or escalation.",
                                    messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                )
                                suggestion = suggestion_response.content[0].text if suggestion_response.content else "Check relevant transaction codes (e.g., ME23N for POs) or verify master data and authorizations."
                                response_text = (
                                    f"Sorry, an error occurred while searching for a solution. "
                                    f"Based on my SAP expertise, here are some suggestions: {suggestion} "
                                    f"Would you like to escalate this issue?"
                                )
                                st.markdown(response_text)
                                st.session_state.messages.append({"role": "assistant", "content": response_text})
                    elif content_block.type == "text":
                        st.markdown(content_block.text)
                        st.session_state.messages.append({"role": "assistant", "content": content_block.text})

            except AnthropicError as e:
                print(f"Debug: Anthropic API error: {str(e)}")
                st.error(f"API Error: {str(e)}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})

# Handle escalation form (always checked outside input loop)
if st.session_state.pending_details:
    print("Debug: Pending details found. Displaying escalation form.")
    with st.form(key="escalation_form"):
        contact_no = st.text_input("Contact Number", key="contact_no")
        mail_id = st.text_input("Email Address", key="mail_id")
        cc_to = st.text_input("CC Email", key="cc_to")
        company_code = st.selectbox("Company", options=[c["companyID"] for c in company_data], format_func=lambda x: next(c["companyname"] for c in company_data if c["companyID"] == x))
        profit_center = st.selectbox("Profit Center", options=[c["ProfitCenterID"] for c in company_data], format_func=lambda x: next(c["ProfitCenterName"] for c in company_data if c["ProfitCenterID"] == x))
        submit_button = st.form_submit_button(label="Submit Details")

        if submit_button:
            if all([contact_no, mail_id, company_code, profit_center]):
                print("Debug: Form submitted with all required fields.")
                details = st.session_state.pending_details.copy()
                details.update({
                    "contact_no": contact_no,
                    "mail_id": mail_id,
                    "cc_to": cc_to,
                    "company_code": str(company_code),
                    "profit_center": str(profit_center)
                })
                with st.chat_message("assistant"):
                    try:
                        result = raise_log(details)
                        print(f"Debug: raise_log result (form): {json.dumps(result, indent=2)}")
                        st.markdown(f"Your log has been created! Ticket Number: {result['response'].get('issue_number')}, zHI ID: {result['response'].get('zhi_id')}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Your log has been created! Ticket Number: {result['response'].get('issue_number')}, zHI ID: {result['response'].get('zhi_id')}"})
                        st.session_state.pending_details = None
                        st.session_state.last_matches = None
                        st.session_state.last_user_error = None
                    except Exception as e:
                        print(f"Debug: Error in raise_log (form): {str(e)}")
                        st.markdown(f"Error raising log: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error raising log: {str(e)}"})
            else:
                print("Debug: Form submission attempted but missing required fields.")
                st.error("Please fill all required fields.")