import os
from dotenv import load_dotenv
import streamlit as st
import requests
from openai import OpenAI

load_dotenv()

st.title("Protocol Summarizer")

st.markdown("""
Search for clinical trials by keyword, select a study, and generate a protocol summary using an LLM.
""")

# 搜索输入

# 仅在用户提交表单后展示结果
with st.form(key="search_form"):
    query = st.text_input("Enter a disease, study title, or keyword:")
    max_results = st.slider("Number of results", 1, 20, 5)
    submitted = st.form_submit_button("Search")

@st.cache_data(show_spinner=False)
def search_clinical_trials(query, max_results=5):
    # 调用 ClinicalTrials.gov v2 按关键词检索研究
    if not query:
        return []
    url = f"https://clinicaltrials.gov/api/v2/studies?query.term={query}&pageSize={max_results}&format=json"
    resp = requests.get(url)
    studies = []
    if resp.status_code == 200:
        data = resp.json()
        for study in data.get('studies', []):
            nct = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'N/A')
            title = study.get('protocolSection', {}).get('identificationModule', {}).get('officialTitle', 'N/A')
            studies.append({'nct': nct, 'title': title})
    return studies

results = search_clinical_trials(query, max_results) if query else []

if results:
    st.subheader("Search Results")
    for i, study in enumerate(results):
        st.markdown(f"**{i+1}. {study['title']}** (NCT: {study['nct']})")
    selected = st.number_input("Select study number to summarize", min_value=1, max_value=len(results), value=1)
    selected_study = results[selected-1]
    st.markdown(f"### Selected Study\n**{selected_study['title']}** (NCT: {selected_study['nct']})")
    if st.button("Summarize Protocol"):
        # 拉取所选研究的简要说明
        nct_id = selected_study['nct']
        
        # 使用已知稳定的 V2 API
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?format=json"
        with st.spinner("Fetching study details..."):
            resp = requests.get(url)
            brief = ""
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    
                    # V2 API 在根级提供 protocolSection
                    if 'protocolSection' in data:
                        desc_mod = data.get('protocolSection', {}).get('descriptionModule', {})
                        brief = desc_mod.get('briefSummary', '')
                        
                        # briefSummary 为空时尝试 detailedDescription
                        if not brief:
                            brief = desc_mod.get('detailedDescription', '')
                except Exception as e:
                    st.error(f"Error parsing study data: {e}")
            
            # API 失败时回退到 HTML 抓取
            if not brief and resp.status_code != 200:
                st.warning(f"API returned status code {resp.status_code}. Trying alternative method...")
                html_url = f"https://clinicaltrials.gov/ct2/show/{nct_id}"
                html_resp = requests.get(html_url)
                
                if "Brief Summary:" in html_resp.text:
                    start = html_resp.text.find("Brief Summary:") + 15
                    excerpt = html_resp.text[start:start+1000]
                    
                    # 清理 HTML 标签与多余空白
                    import re
                    excerpt = re.sub('<[^<]+?>', ' ', excerpt)
                    excerpt = re.sub('\\s+', ' ', excerpt)
                    brief = excerpt.strip()
            
            if not brief:
                st.error("No brief summary or detailed description found for this study.")
                st.stop()
            
        # 将简要说明送给 LLM 做结构化抽取
        openai = OpenAI()
        def user_prompt_for_protocol_brief(brief_text):
            return (
                "Extract the following details from the clinical trial brief summary in markdown format with clear section headings (e.g., ## Study Design, ## Population, etc.):\n"
                "- Study design\n"
                "- Population\n"
                "- Interventions\n"
                "- Primary and secondary endpoints\n"
                "- Study duration\n\n"
                f"Brief summary text:\n{brief_text}"
            )
        system_prompt = "You are a clinical research assistant. Extract and list the requested protocol details in markdown format with clear section headings."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_for_protocol_brief(brief)}
        ]
        with st.spinner("Summarizing with LLM..."):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages
                )
                summary = response.choices[0].message.content
                st.markdown(summary)
            except Exception as e:
                st.error(f"LLM call failed: {e}")
else:
    if query:
        st.info("No results found. Try a different keyword.")
