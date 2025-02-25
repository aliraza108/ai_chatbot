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
from urllib.parse import quote

warnings.filterwarnings("ignore")

# Load environment variables from .env file
load_dotenv()

# Configuration
DOMAIN = "https://your-domain.com"  # Replace with your actual domain
CSV_PATH = os.path.join("data", "pro.csv")
OPENAI_API_KEY = "sk-proj-" + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"

def create_product_url(title):
    """Generate proper product URL from title"""
    handle = title.lower().replace(" ", "-").replace("'", "").replace(",", "")
    return f"{DOMAIN}/products/{quote(handle)}"

def enhance_product_display(response):
    """Convert product mentions to proper cards with images"""
    try:
        products_df = st.session_state.products_df
        
        # Find all product titles in response
        pattern = r'<h3>(.*?)<\/h3>'
        matches = list(re.finditer(pattern, response))
        
        for match in reversed(matches):
            title = match.group(1).strip()
            product_match = products_df[products_df['title'] == title]
            
            if not product_match.empty:
                product = product_match.iloc[0]
                image_url = product['image_url'] if pd.notna(product['image_url']) else "https://via.placeholder.com/100"
                product_url = create_product_url(product['title'])
                
                card_html = f"""
                <div class="product-card">
                    <h3>{product['title']}</h3>
                    <img src="{image_url}" 
                         style="max-width:100%; height:auto; border-radius:5px; margin:10px 0;"
                         alt="{product['title']}">
                    <p style="margin: 10px 0;">Price: ${product['price']:.2f}</p>
                    <a href="{product_url}" 
                       target="_blank"
                       class="product-button">
                        View Product
                    </a>
                </div>
                """
                response = response[:match.start()] + card_html + response[match.end():]
        return response
    except Exception as e:
        print(f"Display enhancement error: {e}")
        return response

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        # Load and prepare CSV data
        products_df = pd.read_csv(CSV_PATH)
        products_df['title'] = products_df['title'].str.strip()
        st.session_state.products_df = products_df
        
        def get_products(query: str) -> str:
            """Retrieve products from CSV data"""
            try:
                # Clean and split query into search terms
                search_terms = [term.strip().lower() for term in re.split(r'\W+', query) if term]
                
                # Find matching products
                mask = products_df['title'].apply(
                    lambda x: any(term in x.lower() for term in search_terms)
                )
                matches = products_df[mask]
                
                if matches.empty:
                    return "No products found."
                
                return "\n".join([f"<h3>{row['title']}</h3>" 
                                for _, row in matches.head(3).iterrows()])
            except Exception as e:
                return f"Error: {str(e)}"

        shopify_tool = FunctionTool.from_defaults(
            fn=get_products,
            name="product_search",
            description=(
                "Access this tool to find clothing products by type, name, or keywords. "
                "Always use when users ask about suits, clothing items, or specific products."
            )
        )

        llm = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo-0125"
        )
        
        st.session_state.agent = ReActAgent.from_tools(
            tools=[shopify_tool],
            llm=llm,
            verbose=True,
            context=f"""You are an e-commerce fashion assistant. Strict rules:
            1. Always respond with product titles wrapped in <h3> tags
            2. Never mention HTML or technical details
            3. List max 3 products
            4. For product requests, ALWAYS use the product_search tool
            5. Maintain friendly, helpful tone"""
        )

def apply_styles():
    st.markdown("""
    <style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        background: white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .product-card img {
        max-width: 200px;
        height: auto;
        display: block;
        margin: 0 auto;
    }
    .product-button {
        display: inline-block;
        background: #4CAF50;
        color: white !important;
        padding: 8px 16px;
        border-radius: 5px;
        text-decoration: none !important;
        margin-top: 10px;
    }
    .product-button:hover {
        background: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🛍️✨ Fashion Assistant Pro")
    init_session()
    apply_styles()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask about our fashion collection..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                response = st.session_state.agent.query(prompt)
                processed = enhance_product_display(response.response)
                st.markdown(processed, unsafe_allow_html=True)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": processed
                })
        except Exception as e:
            st.error(f"Error processing request: {str(e)}")

if __name__ == "__main__":
    main()
