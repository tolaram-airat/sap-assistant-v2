import streamlit as st
import os
import re
import json
import sqlite3
from dotenv import load_dotenv
from anthropic import Anthropic, AnthropicError
from datetime import datetime
from agents.retrieval_new import retrieve_errors, extract_error_phrase
from agents.log_raiser import raise_log

# ------------------------------------------------------------------
# 1. PATHS – always absolute, works locally AND on Streamlit Cloud
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ERROR_DATA_DIR = os.path.join(BASE_DIR, "sap-kb-app")
DB_PATH = os.path.join(DATA_DIR, "errors.db")
ERRORS_JSON = os.path.join(ERROR_DATA_DIR, "errors.json")
COMPANY_JSON = os.path.join(DATA_DIR, "company.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ERROR_DATA_DIR, exist_ok=True)
# ------------------------------------------------------------------
# 2. DATABASE INITIALISATION – **idempotent** (runs only once)
# ------------------------------------------------------------------
def init_db():
    """Create DB + tables + seed data **only if DB does not exist**."""
    if os.path.exists(DB_PATH):
        return  # DB already seeded

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ---- errors table ------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT,
        issuename TEXT,
        issuedescription TEXT,
        solutiontype TEXT,
        stepbystep TEXT,
        logcategory INTEGER,
        logsubcategory INTEGER,
        notes TEXT
    )
    """)

    # ---- mappings table ----------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        code TEXT,
        name TEXT,
        logcategory INTEGER,
        logsubcategory INTEGER
    )
    """)

    # ---- seed errors -------------------------------------------------
    if os.path.exists(ERRORS_JSON):
        with open(ERRORS_JSON, 'r', encoding='utf-8') as f:
            errors = json.load(f)
            for error in errors:
                cursor.execute("""
                INSERT INTO errors (module, issuename, issuedescription, solutiontype, stepbystep, logcategory, logsubcategory, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    error['module'],
                    error['issuename'],
                    error['issuedescription'],
                    error['solutiontype'],
                    error['stepbystep'],
                    error['logcategory'],
                    error['logsubcategory'],
                    error['notes']
                ))

    # ---- seed companies -----------------------------------------------
    if os.path.exists(COMPANY_JSON):
        with open(COMPANY_JSON, 'r', encoding='utf-8') as f:
            companies = json.load(f)
            for item in companies:
                cursor.execute("""
                INSERT INTO mappings (type, code, name, logcategory, logsubcategory)
                VALUES (?, ?, ?, ?, ?)
                """, ('company', item['companyID'], item['companyname'], 3421, 3422))
                cursor.execute("""
                INSERT INTO mappings (type, code, name, logcategory, logsubcategory)
                VALUES (?, ?, ?, ?, ?)
                """, ('profit_center', item['ProfitCenterID'], item['ProfitCenterName'], 3421, 3423))

    conn.commit()
    conn.close()
    st.success("Database initialized successfully.")  # optional, remove if you don’t want a flash

# Run DB init **once** at app start
init_db()

# ------------------------------------------------------------------
# 3. LOAD COMPANY DATA (fallback if file missing)
# ------------------------------------------------------------------
def load_company_data():
    try:
        with open(COMPANY_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.warning(f"company.json not found or invalid ({e}). Using fallback data.")
        return [
            {"companyID": 490518, "ProfitCenterID": 3410, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3410-CAPETOWN"},
            {"companyID": 490518, "ProfitCenterID": 3400, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3400-JO BURG"}
        ]

company_data = load_company_data()

# ------------------------------------------------------------------
# 4. ENV + ANTHROPIC
# ------------------------------------------------------------------
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    st.error("Anthropic API key not found. Add it in Streamlit Secrets or .env.")
    st.stop()

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ------------------------------------------------------------------
# 5. TOOLS (unchanged)
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# 6. SYSTEM PROMPT (unchanged – copy-paste exactly)
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# 7. SESSION STATE (unchanged)
# ------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_details" not in st.session_state:
    st.session_state.pending_details = None
if "last_matches" not in st.session_state:
    st.session_state.last_matches = None
if "last_user_error" not in st.session_state:
    st.session_state.last_user_error = None

st.title("SAP Assistant")

# ------------------------------------------------------------------
# 8. CHAT HISTORY (unchanged)
# ------------------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ------------------------------------------------------------------
# 9. CHAT INPUT
# ------------------------------------------------------------------
if prompt := st.chat_input("Type your SAP error or message"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Escalation intent detection ---
    if re.search(r'\b(yes|yeah|ok|sure|please|raise|escalate|log|ticket)\b.*\b(raise|escalate|log|ticket|yes|yeah)\b', prompt.lower()):
        print("Debug: Escalation intent detected.")
        with st.chat_message("assistant"):
            user_input_for_escalation = st.session_state.last_user_error or prompt
            extracted_phrase = extract_error_phrase(user_input_for_escalation)
            matches = st.session_state.last_matches or [{
                "id": None, "module": "Unknown", "issuename": "No matching error found",
                "issuedescription": user_input_for_escalation, "solution": "Sorry no match found",
                "solutiontype": "consult", "logcategory": None, "logsubcategory": None,
                "notes": None, "score": 0
            }]
            st.session_state.pending_details = {
                "user_input": user_input_for_escalation,
                "matches": matches,
                "extracted_phrase": extracted_phrase
            }
            st.markdown("Okay, let's get started with raising a log ticket for your issue. Could you please provide me with the details I'll need to escalate this?")
            st.session_state.messages.append({"role": "assistant", "content": "Okay, let's get started with raising a log ticket for your issue. Could you please provide me with the details I'll need to escalate this?"})
    else:
        # --- Normal Anthropic call ---
        print("Debug: Calling Anthropic API.")
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
                print(f"Debug: Anthropic response: {response}")

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        print(f"Debug: Tool call → {tool_name}: {tool_input}")

                        if tool_name == "retrieve_errors":
                            try:
                                result = retrieve_errors(**tool_input)
                                if isinstance(result, list) and result:
                                    result = sorted(result, key=lambda x: x["score"], reverse=True)
                                    st.session_state.last_matches = result
                                    st.session_state.last_user_error = tool_input["user_input"]
                                    top = result[0]

                                    if top.get("solutiontype", "").lower() in ["", "consult", "user guidance"]:
                                        suggestion_resp = client.messages.create(
                                            model="claude-3-haiku-20240307",
                                            max_tokens=200,
                                            temperature=0.7,
                                            system="You are an SAP consultant. Provide 1-2 concise, practical suggestions (transaction codes, checks, steps). Do NOT mention databases or escalation.",
                                            messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                        )
                                        suggestion = suggestion_resp.content[0].text if suggestion_resp.content else "Check relevant transaction codes or master data."
                                        txt = f"Sorry, I couldn’t find a match in my database. Based on my SAP expertise: {suggestion} Would you like to escalate?"
                                        st.markdown(txt)
                                        st.session_state.messages.append({"role": "assistant", "content": txt})

                                    elif "escalation" in top.get("solutiontype", "").lower():
                                        extracted = extract_error_phrase(prompt)
                                        st.session_state.pending_details = {
                                            "user_input": prompt,
                                            "matches": result,
                                            "extracted_phrase": extracted
                                        }
                                        st.markdown(f"**Try this first:**\n\n{top['solution']}\n\n**Still needs escalation.** Please provide contact details.")
                                        st.session_state.messages.append({"role": "assistant", "content": "This issue requires escalation. Please provide contact details."})

                                    else:
                                        st.markdown(f"Looks like you're facing **{top['issuename']}**. Here's how to resolve it:\n\n{top['solution']}")
                                        st.session_state.messages.append({"role": "assistant", "content": f"Looks like you're facing **{top['issuename']}**. Here's how to resolve it:\n\n{top['solution']}"})
                                else:
                                    # No match → LLM suggestion
                                    suggestion_resp = client.messages.create(
                                        model="claude-3-haiku-20240307",
                                        max_tokens=200,
                                        temperature=0.7,
                                        system="You are an SAP consultant. Provide 1-2 concise, practical suggestions. No mention of DB/escalation.",
                                        messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                    )
                                    suggestion = suggestion_resp.content[0].text if suggestion_resp.content else "Check transaction codes or master data."
                                    txt = f"Sorry, no match found. Based on my SAP expertise: {suggestion} Would you like to escalate?"
                                    st.markdown(txt)
                                    st.session_state.messages.append({"role": "assistant", "content": txt})
                                    st.session_state.last_matches = None
                                    st.session_state.last_user_error = None

                            except Exception as e:
                                print(f"Debug: retrieve_errors error: {e}")
                                suggestion_resp = client.messages.create(
                                    model="claude-3-haiku-20240307",
                                    max_tokens=200,
                                    temperature=0.7,
                                    system="You are an SAP consultant. Provide 1-2 concise suggestions.",
                                    messages=[{"role": "user", "content": f"User query: {prompt}"}]
                                )
                                suggestion = suggestion_resp.content[0].text if suggestion_resp.content else "Check relevant T-codes."
                                txt = f"Error searching DB. Suggestion: {suggestion} Escalate?"
                                st.markdown(txt)
                                st.session_state.messages.append({"role": "assistant", "content": txt})

                    elif block.type == "text":
                        st.markdown(block.text)
                        st.session_state.messages.append({"role": "assistant", "content": block.text})

            except AnthropicError as e:
                st.error(f"API Error: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})

# ------------------------------------------------------------------
# 10. ESCALATION FORM (unchanged logic)
# ------------------------------------------------------------------
if st.session_state.pending_details:
    print("Debug: Showing escalation form.")
    with st.form(key="escalation_form"):
        contact_no = st.text_input("Contact Number", key="contact_no")
        mail_id = st.text_input("Email Address", key="mail_id")
        cc_to = st.text_input("CC Email", key="cc_to")
        company_code = st.selectbox("Company", options=[c["companyID"] for c in company_data],
                                   format_func=lambda x: next(c["companyname"] for c in company_data if c["companyID"] == x))
        profit_center = st.selectbox("Profit Center", options=[c["ProfitCenterID"] for c in company_data],
                                    format_func=lambda x: next(c["ProfitCenterName"] for c in company_data if c["ProfitCenterID"] == x))
        submit = st.form_submit_button("Submit Details")

        if submit:
            if all([contact_no, mail_id, company_code, profit_center]):
                details = st.session_state.pending_details.copy()
                details.update({
                    "contact_no": contact_no,
                    "mail_id": mail_id,
                    "cc_to": cc_to or "",
                    "company_code": str(company_code),
                    "profit_center": str(profit_center)
                })
                with st.chat_message("assistant"):
                    try:
                        result = raise_log(details)
                        st.markdown(f"**Log created!** Ticket: `{result['response'].get('issue_number')}`, zHI: `{result['response'].get('zhi_id')}`")
                        st.session_state.messages.append({"role": "assistant", "content": f"Log created! Ticket: {result['response'].get('issue_number')}, zHI: {result['response'].get('zhi_id')}"})
                        st.session_state.pending_details = None
                        st.session_state.last_matches = None
                        st.session_state.last_user_error = None
                    except Exception as e:
                        st.markdown(f"Error raising log: {e}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
            else:
                st.error("Please fill all required fields.")