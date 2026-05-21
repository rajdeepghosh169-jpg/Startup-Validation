import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import random
import time
import re
import plotly.express as px

# --- Setup & Config ---
st.set_page_config(page_title="GLIM Startup Validator", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- Fetch API Key Safely ---
# This tries to get the key from Streamlit Secrets (for cloud) or Environment Variables (for local)
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = "AIzaSyAVyLL04VO8iBOdlK_ots3ZpQAASxRHw2o"
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if not api_key:
        raise ValueError("No API Key found.")
except Exception:
    st.error("API Key not found. Please add GEMINI_API_KEY to your Streamlit secrets or local environment variables.")
    st.stop()

# Configure the API and update to the active model
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- Load CSV ---
# Changed to look in the same folder as the script (Cloud-friendly)
csv_path = "alumni.csv" 
try:
    df = pd.read_csv(csv_path)
    
    # Safeguard: Check if the CSV parsed correctly
    if len(df) == 0:
        st.error("The CSV file was loaded but contains 0 rows. Please open alumni.csv in a text editor and remove the surrounding double quotes.")
        st.stop()
        
except FileNotFoundError:
    st.error(f"Could not find the file '{csv_path}'. Please ensure it is in the same folder as this Python script.")
    st.stop()

# --- UI Header ---
st.title("🚀 GLIM Startup Feasibility Dashboard")
st.markdown("Automate outreach, simulate market feedback, and generate actionable insights instantly.")

# --- Sidebar Input ---
with st.sidebar:
    st.header("Campaign Setup")
    startup_idea = st.text_area("Describe your startup idea:", height=150, placeholder="e.g., An AI-driven supply chain optimizer for independent pharmacies.")
    run_campaign = st.button("Launch Outreach & Generate Dashboard", type="primary", use_container_width=True)

# --- Main Logic ---
if run_campaign:
    if not startup_idea:
        st.sidebar.warning("Please enter an idea to begin.")
    else:
        results = []
        counters = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0, "NO_REPLY": 0}
        
        # --- Processing & AI Generation ---
        st.subheader("⚙️ Processing Campaign...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, row in df.iterrows():
            status_text.text(f"Contacting {row['Name']} ({row['Industry']})...")
            
            # Simulate a 75% chance they reply to make the demo realistic
            did_reply = random.choice([True, True, True, False])
            reply_instruction = "The alumnus REPLIED." if did_reply else "The alumnus DID NOT REPLY."
            
            prompt = f"""
            Startup Idea: {startup_idea}
            Target Profile: {row['Name']}, {row['Role']} at {row['Current_Company']} ({row['Industry']}).
            
            Task 1: Write a short, highly compelling 3-sentence cold email to this person.
            Task 2: {reply_instruction}
            If they REPLIED: Simulate a realistic 1-sentence reply based on their industry.
            If they DID NOT REPLY: Draft a 2-sentence follow-up email to send 3 days later.
            
            Analyze the outcome and extract the following:
            1. VIBE: Categorize the overall tone strictly as POSITIVE, NEGATIVE, NEUTRAL, or NO_REPLY.
            2. FEEDBACK: Summarize their actual business feedback in one conversational, human-like sentence (or state "No feedback yet" if no reply).
            3. ACTION: What should the founder do next based on this email? (e.g., "Schedule a call", "Pivot pricing", "Follow up in 3 days").
            
            Format strictly as:
            EMAIL: [First email text]
            VIBE: [POSITIVE/NEGATIVE/NEUTRAL/NO_REPLY]
            FEEDBACK: [1 sentence human summary]
            ACTION: [Next step]
            """
            
            # --- Safety Net for API Calls ---
            try:
                response = model.generate_content(prompt)
                resp_text = response.text
                
                # Regex Extraction for bulletproof text parsing
                email_match = re.search(r'EMAIL:\s*(.*?)(?=VIBE:|$)', resp_text, re.DOTALL | re.IGNORECASE)
                vibe_match = re.search(r'VIBE:\s*(.*?)(?=FEEDBACK:|$)', resp_text, re.DOTALL | re.IGNORECASE)
                feedback_match = re.search(r'FEEDBACK:\s*(.*?)(?=ACTION:|$)', resp_text, re.DOTALL | re.IGNORECASE)
                action_match = re.search(r'ACTION:\s*(.*)', resp_text, re.DOTALL | re.IGNORECASE)

                email = email_match.group(1).strip() if email_match else "Draft failed."
                
                raw_vibe = vibe_match.group(1).upper().strip() if vibe_match else "NEUTRAL"
                if "POS" in raw_vibe: vibe = "POSITIVE"
                elif "NEG" in raw_vibe: vibe = "NEGATIVE"
                elif "NO" in raw_vibe: vibe = "NO_REPLY"
                else: vibe = "NEUTRAL"
                
                feedback = feedback_match.group(1).strip() if feedback_match else "Content missing."
                action = action_match.group(1).strip() if action_match else "Follow up."

                counters[vibe] += 1
                
                results.append({
                    "Name": row['Name'],
                    "Company": row['Current_Company'],
                    "Email Sent": email,
                    "Vibe": vibe,
                    "Feedback": feedback,
                    "Action": action
                })
                
            except Exception as e:
                # If an error happens, show it but don't crash the whole app
                st.error(f"Failed to process {row['Name']}. API Error: {e}")
            
            # Update UI and sleep for 4 seconds to respect Gemini API rate limits
            progress_bar.progress((index + 1) / len(df))
            time.sleep(4) 
            
        status_text.empty()
        progress_bar.empty()

        # --- Dashboard Metrics ---
        st.divider()
        st.subheader("📈 Campaign Analytics")
        
        total_contacted = len(df)
        replies_received = counters["POSITIVE"] + counters["NEGATIVE"] + counters["NEUTRAL"]
        reply_rate = int((replies_received / total_contacted) * 100) if total_contacted > 0 else 0
        
        pos_rate = int((counters["POSITIVE"] / replies_received) * 100) if replies_received > 0 else 0
        neg_rate = int((counters["NEGATIVE"] / replies_received) * 100) if replies_received > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Reached", total_contacted)
        col2.metric("Reply Rate", f"{reply_rate}%")
        col3.metric("Positive Sentiment", f"{pos_rate}%")
        col4.metric("Negative Sentiment", f"{neg_rate}%")

        # --- Professional Graphs (Plotly) ---
        st.markdown("<br>", unsafe_allow_html=True)
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            reply_data = pd.DataFrame({
                "Status": ["Replied", "Awaiting Reply"],
                "Count": [replies_received, counters["NO_REPLY"]]
            })
            fig_donut = px.pie(reply_data, values='Count', names='Status', hole=0.6, 
                               title="Engagement Status", color_discrete_sequence=['#4CAF50', '#9E9E9E'])
            fig_donut.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_donut, use_container_width=True)

        with chart_col2:
            sentiment_data = pd.DataFrame({
                "Sentiment": ["Positive", "Neutral", "Negative"],
                "Count": [counters["POSITIVE"], counters["NEUTRAL"], counters["NEGATIVE"]]
            })
            fig_bar = px.bar(sentiment_data, x='Sentiment', y='Count', 
                             title="Feedback Distribution", 
                             color='Sentiment',
                             color_discrete_map={"Positive": "#4CAF50", "Neutral": "#FFC107", "Negative": "#F44336"})
            fig_bar.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)

        # --- AI Startup Mentor Summary ---
        st.divider()
        st.subheader("🧠 Executive Mentor Memo")
        with st.spinner("Analyzing market feedback and generating mentor memo..."):
            all_insights = " ".join([f"Feedback: {r['Feedback']} | Action: {r['Action']}" for r in results if r['Vibe'] != "NO_REPLY"])
            
            if all_insights:
                try:
                    summary_prompt = f"""
                    Act as a candid, expert startup mentor. Read these summaries of real market feedback for the startup idea '{startup_idea}'. 
                    
                    Feedback & Actions: {all_insights}
                    
                    Write a human-sounding, candid 3-paragraph memo to the founder detailing exactly what the market thinks and what their immediate next steps should be. Do not sound like a robot.
                    """
                    summary = model.generate_content(summary_prompt).text
                    st.info(summary)
                except Exception as e:
                    st.error(f"Could not generate summary due to API error: {e}")
            else:
                st.warning("No replies received yet. Awaiting follow-ups to generate mentor memo.")

        # --- Detailed Outreach Log ---
        st.divider()
        st.subheader("🗂️ Action Items & Outreach Log")
        
        for res in results:
            status_icon = "🟢" if res["Vibe"] == "POSITIVE" else "🔴" if res["Vibe"] == "NEGATIVE" else "🟡" if res["Vibe"] == "NEUTRAL" else "⏳"
            
            with st.expander(f"{status_icon} {res['Name']} ({res['Company']}) | Vibe: {res['Vibe']}"):
                st.markdown("**Initial Cold Email:**")
                st.write(res['Email Sent'])
                st.markdown("---")
                if res['Vibe'] == "NO_REPLY":
                    st.markdown("**Scheduled 3-Day Follow-Up:**")
                    st.write(res['Action'])
                else:
                    st.markdown("**Received Feedback:**")
                    st.write(res['Feedback'])
                    st.markdown("**Recommended Action:**")
                    st.write(res['Action'])