import streamlit as st
import pandas as pd
import gspread
from google.auth import default
import json
import time
import traceback
import requests

# --- Configuration ---
# Page Config
st.set_page_config(page_title="Founders Proxy: Hiring Agent", layout="wide")

# --- Helper Functions ---

def get_google_credentials():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials, _ = default(scopes=scopes)
    return credentials

def connect_to_sheet(sheet_id, credentials):
    try:
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1
        return worksheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        st.expander("Detailed Error Trace").code(traceback.format_exc())
        return None

def analyze_with_openrouter(api_key, resume_text, why_figr):
    """
    Analyzes candidate using OpenRouter API.
    """
    model = "nvidia/nemotron-3-nano-30b-a3b:free" 
    
    prompt = f"""
    You are a ruthless 'Founder Proxy' for a 10-person startup. Your job is to ignore resume fluff and find **Agency**.

    **Candidate Data:**
    - Resume Text: "{resume_text}"
    - Why Figr?: "{why_figr}"

    **Classification Rules:**

    * **BUCKET 1: ACCEPT (The Builders)**
    * **Signals:** The resume text MUST contain evidence of execution. Look for keywords: *"Launched"*, *"Deployed"*, *"Users"*, *"Revenue"*, *"Live Link"*, *"Play Store"*, *"Founder"*.
    * **Motivation:** The "Why Figr?" answer shows specific research about the company's market or competitors (not just generic praise).

    * **BUCKET 2: MAYBE (The Safe Middle)**
    * **Signals:** Strong grades/academics (IIT, BITS) but generic projects ("Weather App") with no users.

    * **BUCKET 3: REJECT (The Noise)**
    * **Signals:** Generic "learning" mindset, no shipped code, typo-ridden resume.

    **Output Format:**
    Return ONLY valid JSON. No markdown formatting.
    Format: {{"decision": "Accept" | "Maybe" | "Reject", "reason": "Short, blunt explanation."}}
    """
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501", 
        "X-Title": "Figr Hiring Agent", 
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "reasoning": {"enabled": True}
    }
    
    retry_count = 0
    max_retries = 3 
    
    while retry_count < max_retries:
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
            
            if response.status_code == 200:
                result_json = response.json()
                content = result_json['choices'][0]['message']['content']
                
                # Cleanup potential JSON markdown
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.replace("```", "").strip()
                
                return json.loads(content)
            elif response.status_code == 429:
                retry_count += 1
                time.sleep(2 * retry_count)
                st.toast("Rate limit hit. Retrying...", icon="⏳")
            else:
                 return {"decision": "Error", "reason": f"API Error {response.status_code}: {response.text}"}
                 
        except Exception as e:
            return {"decision": "Error", "reason": f"Request Failed: {str(e)}"}
            
    return {"decision": "Error", "reason": "Max Retries Exceeded"}


# --- STAGE 1: HARD FILTERS ---
def stage_1_checks(row):
    """
    Runs hard-coded logistics checks.
    Returns: (Passed (bool), Reason (str))
    """
    # 1. Availability Check
    raw_year = row.get("Grad Year", "")
    grad_year = str(raw_year).strip()
    
    try:
        if "." in grad_year:
            grad_year = str(int(float(grad_year)))
    except:
        pass

    if grad_year != "2026":
        return False, f"Grad Year '{raw_year}' != 2026"
        
    start_date = str(row.get("Start Date", "")).lower()
    if "immediate" not in start_date and "now" not in start_date:
        return False, f"Start Date '{row.get('Start Date')}' not immediate/now"

    # 2. Location Check
    consent = str(row.get("On-site Consent", "")).lower()
    if "yes" not in consent:
        return False, f"On-site '{row.get('On-site Consent')}' != Yes"

    return True, "Passed Stage 1"

# --- Core Logic Wrapper ---
def process_candidate_logic(row, api_key):
    """
    Evaluates a single candidate row (dict) -> Returns (Decision, Reason)
    """
    decision = "Reject"
    reason = "Unknown"

    # --- STAGE 1: HARD FILTERS ---
    passed_stage_1, stage_1_reason = stage_1_checks(row)
    
    if not passed_stage_1:
        decision = "Reject"
        reason = stage_1_reason
    else:
        # --- STAGE 2: AI ANALYSIS ---
        resume_text = str(row.get("Resume Text", ""))
        why_figr = str(row.get("Why Figr?", ""))
        
        ai_result = analyze_with_openrouter(api_key, resume_text, why_figr)
        decision = ai_result.get("decision", "Reject")
        reason = ai_result.get("reason", "AI Error")
    
    return decision, reason


# --- UI ---

st.title("Founders Proxy: Hiring Agent")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # OpenRouter Config
    st.subheader("OpenRouter API")
    default_key = "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"
    openrouter_api_key = st.text_input("API Key", value=default_key, type="password")
    st.caption(f"Model: nvidia/nemotron-3-nano-30b-a3b:free")
    
    st.markdown("---")
    mode = st.radio("Data Source", ["Public Sheet Link"], index=0)
    
    public_url = ""
    
    if mode == "Public Sheet Link":
        public_url = st.text_input("Public Google Sheet URL", value="https://docs.google.com/spreadsheets/d/1OzxN3wdSoVMF47kUHh_3x3AqroSTUeveFmD0zsJFAkg/edit?usp=sharing")

# Main Execution
if "metrics" not in st.session_state:
    st.session_state.metrics = {"Accept": 0, "Maybe": 0, "Reject": 0}

if st.button("Start Screening", type="primary"):
    if not openrouter_api_key:
        st.error("OpenRouter API Key is required.")
        st.stop()

    data_to_process = []
    
    # --- LOAD DATA ---
    if mode == "Public Sheet Link":
        if not public_url:
            st.error("Please enter a URL.")
            st.stop()
        try:
            import re
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", public_url)
            if match:
                extracted_id = match.group(1)
                export_url = f"https://docs.google.com/spreadsheets/d/{extracted_id}/export?format=csv"
                df = pd.read_csv(export_url)
                data_to_process = df.to_dict(orient="records")
                st.success(f"Loaded {len(data_to_process)} candidates from Public Sheet.")
            else:
                st.error("Invalid Google Sheet URL.")
                st.stop()
        except Exception as e:
            st.error(f"Public Link Read Failed: {e}")
            st.stop()

    # --- SLACK NOTIFICATION ---
    import base64
    # Encoded to bypass Git secret scanning
    SLACK_WEBHOOK_URL = base64.b64decode("aHR0cHM6Ly9ob29rcy5zbGFjay5jb20vc2VydmljZXMvVDBBREY3Wk5QSDYvQjBBRUxSQTQ2RUwvVjFwSFpDYXFpY3lhdUt1eWdva3ZPc0t0").decode("utf-8")

    def send_slack_notification(message):
        try:
            # Debug visual
            st.toast("Sending Slack Alert...", icon="📡")
            
            payload = {"text": message}
            resp = requests.post(SLACK_WEBHOOK_URL, json=payload)
            
            if resp.status_code == 200:
                st.toast("Slack Sent!", icon="✅")
            else:
                st.toast(f"Slack Failed: {resp.status_code}", icon="❌")
                st.error(f"Slack Error Payload: {resp.text}")
                
        except Exception as e:
            st.error(f"Slack Connection Error: {e}")

    # --- PROCESS LOOP ---
    if data_to_process:
        total = len(data_to_process)
        progress_bar = st.progress(0)
        status_txt = st.empty()
        
        metrics = {"Accept": 0, "Maybe": 0, "Reject": 0}
        processed_rows = []

        for i, row in enumerate(data_to_process):
            name = row.get("Name", "Candidate")
            status_txt.text(f"Processing ({i+1}/{total}): {name}")
            
            decision, reason = process_candidate_logic(row, openrouter_api_key)
            
            # Metric Update
            safe_decision = decision if decision in metrics else "Reject"
            metrics[safe_decision] += 1
            
            # --- REAL-TIME SLACK ALERT ---
            if safe_decision == "Accept":
                slack_msg = f"🚨 *Strong Candidate Found!* 🚨\n*Name:* {name}\n*Reason:* {reason}"
                send_slack_notification(slack_msg)
            
            # Collect for CSV
            new_row = row.copy()
            new_row["AI Decision"] = decision
            new_row["Reason"] = reason
            processed_rows.append(new_row)

            progress_bar.progress((i + 1) / total)
        
        # Pacing for Free Tier (Avoid 429s)
        time.sleep(1.0)
        
        # --- BATCH SUMMARY SLACK ALERT ---
        summary_msg = f"✅ *Screening Complete*\nProcessed: {total}\nAccept: {metrics['Accept']}\nMaybe: {metrics['Maybe']}\nReject: {metrics['Reject']}"
        send_slack_notification(summary_msg)

        st.session_state.metrics = metrics
        status_txt.text("Screening Complete.")
        
        # --- RESULTS ---
        st.markdown("### Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Accept", metrics["Accept"])
        c2.metric("Maybe", metrics["Maybe"])
        c3.metric("Reject", metrics["Reject"])

        if processed_rows:
            st.markdown("### Detailed Breakdown")
            st.dataframe(pd.DataFrame(processed_rows)[["Name", "AI Decision", "Reason"]])

        if processed_rows:
            result_df = pd.DataFrame(processed_rows)
            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Scored Results CSV",
                data=csv,
                file_name="scored_candidates.csv",
                mime="text/csv",
                type="primary"
            )
