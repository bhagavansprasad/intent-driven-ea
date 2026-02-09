import streamlit as st
from agent_core.agent import Agent

# Initialize agent once
agent = Agent()

st.set_page_config(page_title="Intent-Driven Enterprise Assistant")

st.title("🧠 Intent-Driven Enterprise Assistant")

st.markdown(
    "Enter a request like:\n"
    "- **Show invoice 493527**\n"
    "- **Why am I getting ORA-01403?**"
)

user_input = st.text_input("Your request")

if st.button("Submit"):
    if not user_input.strip():
        st.warning("Please enter a request")
    else:
        with st.spinner("Thinking..."):
            try:
                response = agent.handle(user_input)
                st.success("Response")
                st.json(response)
            except Exception as e:
                st.error(str(e))
