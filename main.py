# main.py
import streamlit as st
import shopify
import re
import os
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
import warnings

warnings.filterwarnings("ignore")

# Configuration from environment variables
SHOPIFY_CONFIG = {
    "API_KEY": st.secrets["SHOPIFY_API_KEY"],
    "ACCESS_TOKEN": st.secrets["SHOPIFY_ACCESS_TOKEN"],
    "SHOP_URL": st.secrets["SHOPIFY_SHOP_URL"]
}

# Initialize OpenAI with Streamlit secrets
openai_api_key = st.secrets["OPENAI_API_KEY"]

# Shopify Setup
def configure_shopify():
    try:
        shopify.ShopifyResource.set_site(
            f"https://{SHOPIFY_CONFIG['API_KEY']}:{SHOPIFY_CONFIG['ACCESS_TOKEN']}"
            f"@{SHOPIFY_CONFIG['SHOP_URL']}/admin/api/2024-01"
        )
    except Exception as e:
        st.error(f"Shopify configuration failed: {str(e)}")
        st.stop()

def enhance_product_display(response):
    """Convert product mentions to proper cards with images"""
    try:
        products = shopify.Product.find()
        
        pattern = r'<h3>(.*?)<\/h3>'
        matches = list(re.finditer(pattern, response))
        
        for match in reversed(matches):
            title = match.group(1).strip()
            for product in products:
                if product.title.strip() == title:
                    card_html = f"""
                    <div class="product-card" style="
                        border: 1px solid #e0e0e0;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 15px 0;
                    ">
                        <h3>{product.title}</h3>
                        <img src="{product.images[0].src if product.images else ''}" 
                             width="100" 
                             style="max-width:100%; height:auto; border-radius:5px;"
                             alt="{product.title}">
                        <p style="margin: 10px 0;">Price: {product.variants[0].price if product.variants else 'N/A'}</p>
                        <a href="https://{SHOPIFY_CONFIG['SHOP_URL']}/products/{product.handle}" 
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
                    response = response[:match.start()] + card_html + response[match.end():]
                    break
        return response
    except Exception as e:
        st.error(f"Display enhancement error: {str(e)}")
        return response

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        configure_shopify()
        
        def get_products(query: str) -> str:
            try:
                products = shopify.Product.find()
                return "\n".join([f"<h3>{p.title}</h3>" for p in products[:3]])
            except Exception as e:
                return f"Error: {str(e)}"

        shopify_tool = FunctionTool.from_defaults(
            fn=get_products,
            name="get_products",
            description="Retrieve product listings with titles"
        )

        try:
            llm = OpenAI(
                api_key=openai_api_key,
                model="gpt-3.5-turbo-0125"
            )
        except Exception as e:
            st.error(f"OpenAI initialization failed: {str(e)}")
            st.stop()
        
        st.session_state.agent = ReActAgent.from_tools(
            tools=[shopify_tool],
            llm=llm,
            verbose=False,
            context=f"""
            You are a product display assistant. Follow these rules:
            1. Always respond with product titles wrapped in <h3> tags
            2. List 3 products maximum
            3. Keep descriptions concise
            4. Let the system handle images and buttons
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
    st.title("🛍️ Shop Assistant")
    init_session()
    apply_styles()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask about products..."):
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
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
