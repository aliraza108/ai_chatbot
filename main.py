import os
import re
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# 1) LlamaIndex imports
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

# 2) Load environment variables
load_dotenv()

# 3) Use your OpenAI API key
OPENAI_API_KEY = "sk-proj-" + "p2dN0_oztdhFKtMjji9f5DGI7XQPFEORui43AF1arpd57VAdcEc2sHI77mSk5YX74uqgYIQYAwT3BlbkFJ_Bokz-n5mwr6coif3oieLYHu-6Xz5hxawV2mlKXtpTAOiyXiKWm6jtv5e7FOLlew8fSYFiU68A"

###############################################################################
#                               FAKE DATA                                     #
###############################################################################

FAKE_PERSONAL_DATA = {
    "john@example.com": {
        "name": "John Doe",
        "email": "john@example.com",
        "loyalty_points": 1200,
        "preferred_language": "English",
    },
    "jane@example.com": {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "loyalty_points": 300,
        "preferred_language": "French",
    },
}

FAKE_CONVERSATION_HISTORY = {
    "john@example.com": [
        "User asked about shipping times",
        "User asked about returns policy",
    ],
    "jane@example.com": [
        "User asked about discount codes",
    ],
}

###############################################################################
#                         PRODUCT DISPLAY FUNCTION                            #
###############################################################################

def enhance_product_display(response_text: str, products_df: pd.DataFrame) -> str:
    """Replace product names with cards containing images and buttons."""
    pattern = r'\[PRODUCT\](.*?)\[\/PRODUCT\]'
    matches = list(re.finditer(pattern, response_text, re.IGNORECASE))
    
    for match in reversed(matches):
        product_name = match.group(1).strip()
        product_match = products_df[products_df['title'] == product_name]
        
        if not product_match.empty:
            product = product_match.iloc[0]
            card_html = f"""
            <div class="product-card">
                <h4>{product['title']}</h4>
                <img src="{product['image_url']}" width="100" style="max-width:100%; height:auto;">
                <p>Price: ${product['price']}</p>
                <a href="{product['product_url']}" target="_blank">
                    <button class="view-button">View Product</button>
                </a>
            </div>
            """
            response_text = (response_text[:match.start()] + 
                            card_html + 
                            response_text[match.end():])
    
    return response_text

###############################################################################
#                                TOOLS                                        #
###############################################################################

def get_product_data(query: str) -> str:
    """Retrieve product data and format for agent."""
    products_df = st.session_state.products_df
    query = query.lower()
    
    # Simple search implementation
    results = products_df[
        products_df['title'].str.lower().str.contains(query) |
        products_df['description'].str.lower().str.contains(query)
    ].head(3)
    
    if results.empty:
        return "No products found."
    
    return "\n".join([f"[PRODUCT]{row['title']}[/PRODUCT]" for _, row in results.iterrows()])

def get_personal_info(email: str) -> str:
    """Retrieve personal info from fake data."""
    user_data = FAKE_PERSONAL_DATA.get(email.lower())
    return str(user_data) if user_data else "No user found."

def get_conversation_history(email: str) -> str:
    """Retrieve conversation history from fake data."""
    history = FAKE_CONVERSATION_HISTORY.get(email.lower())
    return "\n".join(history) if history else "No history found."

###############################################################################
#                              INITIALIZATION                                 #
###############################################################################

def apply_styles():
    """Add custom CSS styles."""
    st.markdown("""
    <style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background: #f8f9fa;
    }
    .view-button {
        background: #4CAF50;
        color: white;
        padding: 6px 12px;
        border: none;
        border-radius: 4px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

def init_session():
    """Initialize session state and agent."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "products_df" not in st.session_state:
        csv_path = "product.csv"  # Update with your path
        df = pd.read_csv(csv_path)
        # Ensure these columns exist in your CSV:
        # title, price, image_url, product_url
        st.session_state.products_df = df

    if "agent" not in st.session_state:
        # Create tools
        tools = [
            FunctionTool.from_defaults(fn=get_product_data, name="product_search"),
            FunctionTool.from_defaults(fn=get_personal_info, name="user_info"),
            FunctionTool.from_defaults(fn=get_conversation_history, name="chat_history")
        ]

        # Configure LLM
        Settings.llm = OpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.1
        )

        # Create agent
        st.session_state.agent = ReActAgent.from_tools(
            tools=tools,
            llm=Settings.llm,
            verbose=True,
            system_prompt="""
            You are an e-commerce support assistant. Follow these rules:
            1. Use product_search for product-related queries
            2. Use user_info for account questions (ask for email)
            3. Use chat_history for previous interactions
            4. Always wrap product names in [PRODUCT][/PRODUCT] tags
            5. Keep responses concise and helpful
            6. Mention product features from the data
            """
        )

###############################################################################
#                                   MAIN                                      #
###############################################################################

def main():
    st.title("🛍️ E-commerce Assistant")
    apply_styles()
    init_session()

    # Display chat history
    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "user"
        st.chat_message(role).markdown(msg["content"], unsafe_allow_html=True)

    # Handle user input
    if prompt := st.chat_input("Ask about products or your account..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)

        try:
            # Get agent response
            response = st.session_state.agent.chat(prompt)
            processed_response = enhance_product_display(
                response.response,
                st.session_state.products_df
            )

            # Add and display assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": processed_response
            })
            st.chat_message("assistant").markdown(processed_response, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error processing request: {str(e)}")

if __name__ == "__main__":
    main()
