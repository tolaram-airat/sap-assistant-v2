import streamlit as st
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic, AnthropicError
from agents.retrieval_new import retrieve_errors, extract_error_phrase
from agents.log_raiser import raise_log

# ========================================
# 1. LOAD ENV & INITIALIZE DATABASE SAFELY
# ========================================
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    st.error("Anthropic API key not found. Please check Streamlit Secrets.")
    st.stop()

# Auto-create database on first run (safe)
try:
    import setup_db  # This creates errors.db if missing
except Exception as e:
    st.error(f"Failed to initialize database: {e}")
    st.stop()

# Initialize Anthropic client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ========================================
# 2. LOAD COMPANY DATA (with fallback)
# ========================================
def load_company_data():
    company_path = os.path.join(os.path.dirname(__file__), "data", "company.json")
    try:
        with open(company_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Using default company data: {e}")
        return [
            {"companyID": 490518, "ProfitCenterID": 3410, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3410-CAPETOWN"},
            {"companyID": 490518, "ProfitCenterID": 3400, "companyname": "ZA10-ZA10-KTSA", "ProfitCenterName": "3400-JO BURG"}
        ]

company_data = load_company_data()

# ========================================
# 3. TOOL & PROMPT (unchanged)
# ========================================
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

# ========================================
# 4. SESSION STATE & UI
# ========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_details" not in st.session_state:
    st.session_state.pending_details = None
if "last_matches" not in st.session_state:
    st.session_state.last_matches = None
if "last_user_error" not in st.session_state:
    st.session_state.last_user_error = None

st.title("Tolaram SAP Assistant")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# ========================================
# 5. CHAT INPUT & LOGIC
# ========================================
if prompt := st.chat_input("Type your SAP error or question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Escalation intent detection
    if re.search(r'\b(yes|yeah|ok|sure|please|raise|escalate|log|ticket)\b.*\b(raise|escalate|log|ticket|yes|yeah)\b', prompt.lower()):
        with st.chat_message("assistant"):
            user_input = st.session_state.last_user_error or prompt
            extracted_phrase = extract_error_phrase(user_input)
            matches = st.session_state.last_matches or [{
                "id": None, "module": "Unknown", "issuename": "No match", "issuedescription": user_input,
                "solution": "Sorry, no match found.", "solutiontype": "consult", "score": 0
            }]
            st.session_state.pending_details = {
                "user_input": user_input, "matches": matches, "extracted_phrase": extracted_phrase
            }
            st.markdown("Okay, let's raise a log. Please provide your details below.")
            st.session_state.messages.append({"role": "assistant", "content": "Okay, let's raise a log. Please provide your details below."})
    else:
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

                for block in response.content:
                    if block.type == "tool_use" and block.name == "retrieve_errors":
                        tool_input = block.input
                        result = retrieve_errors(**tool_input)

                        if result and isinstance(result, list):
                            result = sorted(result, key=lambda x: x["score"], reverse=True)
                            st.session_state.last_matches = result
                            st.session_state.last_user_error = tool_input["user_input"]
                            top = result[0]

                            if top.get("solutiontype", "").lower() in ["", "consult", "user guidance"]:
                                suggestion = client.messages.create(
                                    model="claude-3-haiku-20240307",
                                    max_tokens=150,
                                    temperature=0.7,
                                    system="You are an SAP expert. Give 1-2 concise suggestions. No mention of DB or escalation.",
                                    messages=[{"role": "user", "content": f"Issue: {prompt}"}]
                                ).content[0].text

                                text = f"Sorry, no match found in database.\n\n**Suggestion:** {suggestion}\n\nWould you like to escalate?"
                                st.markdown(text)
                                st.session_state.messages.append({"role": "assistant", "content": text})

                            elif "escalation" in top.get("solutiontype", "").lower():
                                st.session_state.pending_details = {
                                    "user_input": prompt, "matches": result,
                                    "extracted_phrase": extract_error_phrase(prompt)
                                }
                                st.markdown(f"**Try this first:**\n\n{top.get('solution', 'N/A')}\n\n**Still need help?** I'll raise a ticket.")
                                st.session_state.messages.append({"role": "assistant", "content": "Still need help? I'll raise a ticket."})

                            else:
                                solution = top.get('solution') or top.get('stepbystep') or "No steps available."
                                st.markdown(f"**Issue:** {top['issuename']}\n\n**Solution:**\n{solution}")
                                st.session_state.messages.append({"role": "assistant", "content": f"**Issue:** {top['issuename']}\n\n**Solution:**\n{solution}"})
                        else:
                            suggestion = client.messages.create(
                                model="claude-3-haiku-20240307",
                                max_tokens=150,
                                temperature=0.7,
                                system="You are an SAP expert. Give 1-2 concise suggestions. No mention of DB or escalation.",
                                messages=[{"role": "user", "content": f"Issue: {prompt}"}]
                            ).content[0].text
                            text = f"Sorry, no match found.\n\n**Suggestion:** {suggestion}\n\nEscalate?"
                            st.markdown(text)
                            st.session_state.messages.append({"role": "assistant", "content": text})

                    elif block.type == "text":
                        st.markdown(block.text)
                        st.session_state.messages.append({"role": "assistant", "content": block.text})

            except AnthropicError as e:
                st.error(f"API Error: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})

# ========================================
# 6. ESCALATION FORM
# ========================================
if st.session_state.pending_details:
    with st.form("escalation_form"):
        col1, col2 = st.columns(2)
        with col1:
            contact_no = st.text_input("Contact Number", placeholder="+234...")
            mail_id = st.text_input("Email", placeholder="you@tolaram.com")
        with col2:
            cc_to = st.text_input("CC Email (optional)", placeholder="manager@tolaram.com")
            company_code = st.selectbox("Company", options=[c["companyID"] for c in company_data],
                                      format_func=lambda x: next(c["companyname"] for c in company_data if c["companyID"] == x))
            profit_center = st.selectbox("Profit Center", options=[c["ProfitCenterID"] for c in company_data],
                                        format_func=lambda x: next(c["ProfitCenterName"] for c in company_data if c["ProfitCenterID"] == x))

        if st.form_submit_button("Submit Ticket"):
            if contact_no and mail_id and company_code and profit_center:
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
                        ticket = result['response'].get('issue_number')
                        zhi = result['response'].get('zhi_id')
                        st.success(f"Ticket Created! **#{ticket}** | zHI: `{zhi}`")
                        st.session_state.messages.append({"role": "assistant", "content": f"Ticket #{ticket} created! zHI: {zhi}"})
                        st.session_state.pending_details = None
                        st.session_state.last_matches = None
                        st.session_state.last_user_error = None
                    except Exception as e:
                        st.error(f"Failed to raise ticket: {e}")
            else:
                st.error("Please fill all required fields.")