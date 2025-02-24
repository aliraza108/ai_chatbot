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

# API Configuration
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
    """Convert product mentions to proper cards with images"""
    try:
        products = shopify.Product.find()
        
        # Find all product titles in response
        pattern = r'<h3>(.*?)<\/h3>'
        matches = list(re.finditer(pattern, response))
        
        for match in reversed(matches):
            title = match.group(1).strip()
            for product in products:
                if product.title.strip() == title:
                    # Build product card
                    card_html = f"""
                    <div class="product-card" style="
                        border: 1px solid #e0e0e0;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 15px 0;
                    ">
                        <h3>{product.title}</h3>
                        <img src="{product.images[0].src}" 
                             width="100" 
                             style="max-width:100%; height:auto; border-radius:5px;"
                             alt="{product.title}">
                        <p style="margin: 10px 0;">Price: {product.variants[0].price}</p>
                        <div style="color: #666; font-size: 0.9em;">
                            {product.body_html or "Product description not available"}
                        </div>
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
                                margin-top: 10px;
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
                if query.strip():
                    products = [p for p in products if query.lower() in p.title.lower()]
                if not products:
                    return "No products found matching your query."
                return "\n".join([f"<h3>{p.title}</h3>" for p in products[:3]])
            except Exception as e:
                return f"Error: {str(e)}"

        shopify_tool = FunctionTool.from_defaults(
            fn=get_products,
            name="get_products",
            description="Retrieve product listings with titles"
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
            You are Ali Raza, a chat support agent with 3 years of experience. Follow these rules:
            1. Never show internal thoughts or observations to the user
            2. If user greets, respond politely and list 3 random products
            3. Only use get_products when explicitly asked about products
            4. For non-product questions, answer directly without tool usage
            5. Always wrap product titles in <h3> tags when mentioned
            6. If asked about yourself, respond: "I'm Ali Raza, your shopping assistant with 3 years of experience."
            7. If no products found, suggest other help options
            8. Never mention tools or internal processes
            9. Format responses naturally without markdown
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

def clean_response(response):
    """Remove internal agent observations and actions"""
    lines = response.split('\n')
    cleaned = []
    for line in lines:
        if line.startswith(('Observation:', 'Thought:', 'Action:')):
            continue
        if 'Final Answer:' in line:
            cleaned.append(line.split('Final Answer:')[-1].strip())
            break
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def main():
    st.title("🛍️✨ Shop Assistant Pro")
    init_session()
    apply_styles()

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # Handle input
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                # Get and process response
                response = st.session_state.agent.query(prompt)
                
                # Clean the response
                processed = clean_response(response.response)
                
                # Enhance product display
                final_output = enhance_product_display(processed)
                
                # Handle empty responses
                if not final_output.strip():
                    final_output = "I found some great options for you! Please check our latest collection."
                
                st.markdown(final_output, unsafe_allow_html=True)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_output
                })
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
