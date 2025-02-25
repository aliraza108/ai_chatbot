# main.py
import os
import streamlit as st
import re
import pandas as pd
from dotenv import load_dotenv
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms import openai
import warnings

warnings.filterwarnings("ignore")

# Load environment variables from .env file
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = "sk-proj-" + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"

def enhance_product_display(response):
    """Convert product mentions to proper cards with images using CSV data"""
    try:
        products_df = st.session_state.products_df
        
        # Find all product titles in response
        pattern = r'<h3>(.*?)<\/h3>'
        matches = list(re.finditer(pattern, response))
        
        for match in reversed(matches):
            title = match.group(1).strip()
            # Find product in DataFrame
            product_match = products_df[products_df['title'] == title]
            if not product_match.empty:
                product = product_match.iloc[0]
                # Build product card
                card_html = f"""
                <div class="product-card" style="
                    border: 1px solid #e0e0e0;
                    border-radius: 10px;
                    padding: 15px;
                    margin: 15px 0;
                ">
                    <h3>{product['title']}</h3>
                    <img src="{product['image_url']}" 
                         width="100" 
                         style="max-width:100%; height:auto; border-radius:5px;"
                         alt="{product['title']}">
                    <p style="margin: 10px 0;">Price: ${product['price']}</p>
                    <a href="{product['product_url']}" 
                       target="_blank"
                       style="text-decoration: none;">
                        <button style="
                            background: #4CAF50;
                            color: white;
                            padding: 8px 16px;
                            border: none;
                            border-radius: 5px;
                            cursor: pointer;
                        ">
                            View Product
                        </button>
                    </a>
                </div>
                """
                # Replace in reverse order to prevent offset issues
                response = response[:match.start()] + card_html + response[match.end():]
        return response
    except Exception as e:
        print(f"Display enhancement error: {e}")
        return response

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        # Load CSV data
        csv_path = os.path.join("data", "pro.csv")
        products_df = pd.read_csv(csv_path)
        st.session_state.products_df = products_df
        
        def get_products(query: str) -> str:
            """Retrieve products from CSV data"""
            return "\n".join([f"<h3>{row['title']}</h3>" 
                            for _, row in products_df.head(3).iterrows()])

        shopify_tool = FunctionTool.from_defaults(
            fn=get_products,
            name="get_products",
            description="Retrieve product listings with titles from inventory"
        )

        llm = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo-0125"
        )
        
        st.session_state.agent = ReActAgent.from_tools(
            tools=[shopify_tool],
            llm=llm,
            verbose=False,
            context=f"""
            You are a product display assistant. Follow these rules:
            1. Always respond with product titles wrapped in <h3> tags
            2. Never include raw HTML in responses
            3. List 3 products maximum
            4. Keep descriptions concise
            5. Let the system handle images and buttons
            """
        )

def apply_styles():
    st.markdown("""
    <style>
    .product-card {
        background: white;
        padding: 15px;
        margin: 15px 0;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .stChatMessage {
        background: #f5f5f5 !important;
        border-radius: 15px !important;
    }
    button {
        transition: transform 0.2s !important;
    }
    button:hover {
        transform: scale(1.05) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🛍️✨ Shop Assistant Pro")
    init_session()
    apply_styles()

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # Handle input
    if prompt := st.chat_input("Ask about products..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                # Get and process response
                response = st.session_state.agent.query(prompt)
                processed = enhance_product_display(response.response)
                st.markdown(processed, unsafe_allow_html=True)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": processed
                })
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
