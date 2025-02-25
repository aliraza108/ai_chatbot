# main.py
import os
import streamlit as st
import shopify
import re
from dotenv import load_dotenv
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.llms import openai
import warnings

warnings.filterwarnings("ignore")

# Load environment variables from .env file
load_dotenv()

# API Configuration from environment variables
OPENAI_API_KEY = "sk-proj-" + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"
SHOPIFY_CONFIG = {
    "API_KEY": os.environ.get("SHOPIFY_API_KEY"),
    "ACCESS_TOKEN": os.environ.get("SHOPIFY_ACCESS_TOKEN"),
    "SHOP_URL": os.environ.get("SHOPIFY_SHOP_URL")
}

# Shopify Setup
def configure_shopify():
    shopify.ShopifyResource.set_site(
        f"https://{SHOPIFY_CONFIG['API_KEY']}:{SHOPIFY_CONFIG['ACCESS_TOKEN']}"
        f"@{SHOPIFY_CONFIG['SHOP_URL']}/admin/api/2024-01"
    )

def enhance_product_display(response):
    """
    Enhance the response by replacing product placeholders or plain text product lines with full product cards.
    """
    try:
        products = shopify.Product.find()

        # 1. Replace placeholders (if any) where product names are wrapped in <div class="product-item"> tags.
        pattern_placeholder = r'<div class="product-item">(.*?)<\/div>'
        matches_placeholder = list(re.finditer(pattern_placeholder, response))
        for match in reversed(matches_placeholder):
            title = match.group(1).strip()
            for product in products:
                if product.title.strip().lower() == title.lower():
                    image_src = product.images[0].src if product.images else "https://via.placeholder.com/100?text=No+Image"
                    card_html = f"""
                    <div class="product-card" style="
                        border: 1px solid #e0e0e0;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 15px 0;
                    ">
                        <h3>{product.title}</h3>
                        <img src="{image_src}" 
                             width="100" 
                             style="max-width:100%; height:auto; border-radius:5px;"
                             alt="{product.title}">
                        <p style="margin: 10px 0;">Price: {product.variants[0].price}</p>
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

        # 2. Process plain text lines: If a line exactly matches a product title, replace that line.
        lines = response.splitlines()
        new_lines = []
        for line in lines:
            stripped_line = line.strip()
            replaced = False
            for product in products:
                if stripped_line.lower() == product.title.strip().lower():
                    image_src = product.images[0].src if product.images else "https://via.placeholder.com/100?text=No+Image"
                    card_html = f"""
                    <div class="product-card" style="
                        border: 1px solid #e0e0e0;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 15px 0;
                    ">
                        <h3>{product.title}</h3>
                        <img src="{image_src}" 
                             width="100" 
                             style="max-width:100%; height:auto; border-radius:5px;"
                             alt="{product.title}">
                        <p style="margin: 10px 0;">Price: {product.variants[0].price}</p>
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
                    new_lines.append(card_html)
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)
        return "\n".join(new_lines)
    except Exception as e:
        print(f"Display enhancement error: {e}")
        return response

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent" not in st.session_state:
        configure_shopify()
        
        def get_products(query: str) -> str:
            try:
                products = shopify.Product.find()
                # Return up to 3 products, each wrapped in the product placeholder tag.
                return "\n".join([f'<div class="product-item">{p.title}</div>' for p in products[:3]])
            except Exception as e:
                return f"Error: {str(e)}"

        shopify_tool = FunctionTool.from_defaults(
            fn=get_products,
            name="get_products",
            description='Retrieve product listings with titles. Returns up to 3 product titles wrapped in <div class="product-item"> tags.'
        )

        # Use GPT-4 for improved responses (if available)
        llm = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4"
        )
        
        st.session_state.agent = ReActAgent.from_tools(
            tools=[shopify_tool],
            llm=llm,
            verbose=False,
            context=f"""
            You are a friendly, human-like chat support agent named [Your Name] with 3 years of experience at FlexShopPk in Karachi, Pakistan.
            Greet customers warmly and engage in natural conversation.
            Only when a customer explicitly asks for product information should you list products.
            When listing products, respond with up to 3 product titles wrapped in <div class="product-item"> tags (do not include raw HTML).
            The system will convert these placeholders or plain text product lines into product cards with images, prices, and a 'View Product' button.
            Keep your responses personable and avoid jumping into product listings during casual greetings.
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

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # Handle user input
    if prompt := st.chat_input("Ask about products..."):
        # Save and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Handle greetings directly
        if prompt.lower().strip() in ["hi", "hello", "hey"]:
            human_reply = (
                "Hello! I'm [Your Name], your chat support agent with 3 years of experience at FlexShopPk in Karachi, Pakistan. "
                "How can I help you today?"
            )
            st.session_state.messages.append({"role": "assistant", "content": human_reply})
            with st.chat_message("assistant"):
                st.markdown(human_reply)
        else:
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
